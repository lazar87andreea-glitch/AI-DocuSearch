import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

# Import traceable from web_app (already initialized with LangSmith credentials)
# This ensures all modules use the same traceable instance
try:
    # At runtime, web_app will export traceable to sys.modules
    # For now, define a fallback in case of circular imports
    from langsmith import traceable
except Exception:
    # LangSmith is optional; no-op decorator keeps tracing calls safe when it's not installed.
    from typing import Callable, TypeVar

    _F = TypeVar("_F", bound=Callable[..., Any])

    def traceable(*_args: Any, **_kwargs: Any) -> Callable[[_F], _F]:
        def _decorator(fn: _F) -> _F:
            return fn
        return _decorator


def _estimate_tokens(text: str) -> int:
    # Rough heuristic (~4 chars/token) used only when a provider doesn't return real usage.
    return max(0, len(text) // 4) if text else 0


def _get_langsmith_client() -> Optional[Any]:
    """Get or create a cached LangSmith Client, with proper environment setup.
    
    Returns None if LangSmith is not properly configured.
    """
    try:
        # Only attempt to create if we have the required environment
        if not os.getenv("LANGSMITH_API_KEY"):
            print(f"[LANGSMITH] Cannot create client: LANGSMITH_API_KEY not set", file=sys.stderr)
            return None
        
        if os.getenv("LANGSMITH_TRACING", "").lower() != "true":
            print(f"[LANGSMITH] Cannot create client: LANGSMITH_TRACING not set to 'true'", file=sys.stderr)
            return None
        
        from langsmith import Client
        print(f"[LANGSMITH] Creating Client with project: {os.getenv('LANGSMITH_PROJECT', 'default')}", file=sys.stderr)
        client = Client()
        print(f"[LANGSMITH] Client created successfully", file=sys.stderr)
        return client
    except Exception as e:
        print(f"[LANGSMITH] Failed to create Client: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def generate_answer_with_meta(
    prompt: str, model_name: Optional[str] = None, temperature: Optional[float] = None
) -> Dict[str, Any]:
    """Same resolution/request logic as generate_answer, plus timing and token metrics.
    
    Uses manual LangSmith Client tracing (create_run/update_run) instead of @traceable decorator
    to ensure outputs are properly captured. The decorator approach conflicts with manual
    tracing and causes "No outputs" in LangSmith dashboard.
    """
    start = time.perf_counter()

    resolved_temperature = temperature
    if resolved_temperature is None:
        env_temp = os.getenv("LLM_TEMPERATURE")
        resolved_temperature = float(env_temp) if env_temp else 0.2

    # Generic LLM_* variables are the recommended way to configure any OpenAI-compatible
    # chat completions provider (OpenAI, xAI/Grok, Groq, Together, etc.). OPENAI_* and the
    # legacy XAI_*/GROK_* names are supported as fallbacks for convenience/backward compatibility.
    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("XAI_API_KEY")
        or os.getenv("GROK_API_KEY")
    )
    base_url = (
        os.getenv("LLM_API_BASE")
        or os.getenv("OPENAI_API_BASE")
        or os.getenv("XAI_API_BASE")
        or os.getenv("GROK_API_BASE")
    )
    if not base_url and os.getenv("OPENAI_API_KEY"):
        base_url = "https://api.openai.com/v1"
    resolved_model = (
        model_name
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("XAI_MODEL")
        or os.getenv("GROK_MODEL")
    )

    # Debug: Log what we found in environment
    print(f"[AI_QUERY] API Key present: {bool(api_key)}", file=sys.stderr)
    print(f"[AI_QUERY] Base URL: {base_url}", file=sys.stderr)
    print(f"[AI_QUERY] Model: {resolved_model}", file=sys.stderr)
    print(f"[AI_QUERY] Temperature: {resolved_temperature}", file=sys.stderr)

    # Initialize LangSmith variables
    _ls_client = None
    langsmith_run_id = None
    
    if api_key and base_url and resolved_model:
        # Debug: Log LangSmith environment BEFORE creating client
        langsmith_key = os.getenv("LANGSMITH_API_KEY")
        langsmith_tracing = os.getenv("LANGSMITH_TRACING")
        langsmith_project = os.getenv("LANGSMITH_PROJECT")
        print(f"[LANGSMITH_ENV] API_KEY present: {bool(langsmith_key)}", file=sys.stderr)
        print(f"[LANGSMITH_ENV] TRACING: '{langsmith_tracing}'", file=sys.stderr)
        print(f"[LANGSMITH_ENV] PROJECT: '{langsmith_project}'", file=sys.stderr)
        
        # Get LangSmith client (only if properly configured)
        _ls_client = _get_langsmith_client()
        
        # Create run with question extraction
        if _ls_client:
            try:
                # Extract question from prompt (usually appears after "Question:" or at the end)
                question_text = prompt
                if "Question:" in prompt:
                    question_text = prompt.split("Question:")[-1].strip()[:200]
                elif "question" in prompt.lower():
                    # Find context around the word "question"
                    parts = prompt.lower().split("question")
                    if len(parts) > 1:
                        question_text = prompt.split(parts[0] + "question")[-1].strip()[:200]
                
                print(f"[LANGSMITH] About to call create_run...", file=sys.stderr)
                # Use explicit project_name from env to avoid Client state issues in Streamlit
                project_name = os.getenv("LANGSMITH_PROJECT", "default")
                print(f"[LANGSMITH] Using project_name: {project_name}", file=sys.stderr)
                langsmith_run_id = uuid4()
                _ls_client.create_run(
                    name="generate_answer",
                    run_type="llm",
                    project_name=project_name,
                    id=langsmith_run_id,
                    inputs={
                        "question": question_text[:300],
                        "prompt_length": len(prompt),
                        "model": resolved_model,
                    },
                )
                print(f"[LANGSMITH] Run created with ID: {langsmith_run_id}", file=sys.stderr)
            except Exception as e:
                print(f"[LANGSMITH] Failed to create run: {type(e).__name__}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                langsmith_run_id = None
        
        # Try to get the answer from the API
        answer = ""
        api_error = ""
        error_type = None
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        usage_estimated = False
        success = False
        
        try:
            import requests
            
            payload = {
                "model": resolved_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": resolved_temperature,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            print(f"[AI_QUERY] Sending request to {base_url.rstrip('/')}/chat/completions", file=sys.stderr)
            
            resp = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            print(f"[AI_QUERY] Response status: {resp.status_code}", file=sys.stderr)
            resp.raise_for_status()
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            success = True
            print(f"[AI_QUERY] SUCCESS: Got answer from LLM API (length={len(answer)})", file=sys.stderr)
            
            # Extract token usage from response
            usage = data.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or 0)
            if prompt_tokens == 0:
                prompt_tokens = _estimate_tokens(prompt)
                usage_estimated = True
            if completion_tokens == 0:
                completion_tokens = _estimate_tokens(answer)
                usage_estimated = True
            if total_tokens == 0:
                total_tokens = prompt_tokens + completion_tokens
                
        except Exception as e:
            print(f"[AI_QUERY] ERROR during API call: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            api_error = str(e)
            error_type = type(e).__name__
            answer = ""
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            success = False
        
        # Complete the run after all response metadata is available.
        print(f"[LANGSMITH] About to update run: run={langsmith_run_id is not None}, client={_ls_client is not None}, success={success}", file=sys.stderr)
        
        if langsmith_run_id and _ls_client:
            try:
                if success:
                    outputs = {
                        "answer": str(answer[:500]) if answer else "",
                        "prompt_tokens": int(prompt_tokens),
                        "completion_tokens": int(completion_tokens),
                        "total_tokens": int(total_tokens),
                    }
                    _ls_client.update_run(
                        langsmith_run_id,
                        outputs=outputs,
                        end_time=datetime.now(timezone.utc),
                    )
                else:
                    _ls_client.update_run(
                        langsmith_run_id,
                        error=api_error,
                        end_time=datetime.now(timezone.utc),
                    )
                print(f"[LANGSMITH] Run updated successfully", file=sys.stderr)
            except Exception as ls_error:
                print(f"[LANGSMITH] Failed to update run: {type(ls_error).__name__}: {ls_error}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
        
        # Return result
        return {
            "answer": answer,
            "elapsed_seconds": time.perf_counter() - start,
            "response_status": "success" if success else "error",
            "error_type": error_type,
            "error_message": api_error or None,
            "used_live_api": success,
            "langsmith_run_id": str(langsmith_run_id) if langsmith_run_id else None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_tokens": usage_estimated,
            "temperature": resolved_temperature,
        }
    else:
        print(f"[AI_QUERY] MISSING CONFIG: api_key={bool(api_key)}, base_url={bool(base_url)}, model={bool(resolved_model)}", file=sys.stderr)

    snippet = prompt[:100].replace("\n", " ")
    answer = f"[SIMULATED ANSWER] {snippet}..."
    prompt_tokens = _estimate_tokens(prompt)
    completion_tokens = _estimate_tokens(answer)
    return {
        "answer": answer,
        "elapsed_seconds": time.perf_counter() - start,
        "response_status": "simulated",
        "error_type": "configuration_missing",
        "error_message": "LLM provider configuration is incomplete.",
        "used_live_api": False,
        "langsmith_run_id": None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_tokens": True,
        "temperature": resolved_temperature,
    }
