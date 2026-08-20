import os
import sys
import time
from typing import Any, Dict, Optional

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


def generate_answer_with_meta(
    prompt: str, model_name: Optional[str] = None, temperature: Optional[float] = None
) -> Dict[str, Any]:
    """Same resolution/request logic as generate_answer, plus timing and token metrics.
    
    Uses manual LangSmith Client tracing (create_run/end_run) instead of @traceable decorator
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
    run = None
    run_ended = False  # Track if we've already ended the run
    
    if api_key and base_url and resolved_model:
        # Debug: Log LangSmith environment BEFORE creating client
        langsmith_key = os.getenv("LANGSMITH_API_KEY")
        langsmith_tracing = os.getenv("LANGSMITH_TRACING")
        langsmith_project = os.getenv("LANGSMITH_PROJECT")
        print(f"[LANGSMITH_ENV] API_KEY present: {bool(langsmith_key)}", file=sys.stderr)
        print(f"[LANGSMITH_ENV] TRACING: '{langsmith_tracing}'", file=sys.stderr)
        print(f"[LANGSMITH_ENV] PROJECT: '{langsmith_project}'", file=sys.stderr)
        
        # Initialize LangSmith client once
        try:
            from langsmith import Client
            print(f"[LANGSMITH] Attempting to create Client...", file=sys.stderr)
            _ls_client = Client()
            print(f"[LANGSMITH] Client initialized successfully", file=sys.stderr)
        except Exception as e:
            print(f"[LANGSMITH] Failed to initialize client: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
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
                
                run = _ls_client.create_run(
                    name="generate_answer",
                    run_type="llm",
                    inputs={
                        "question": question_text[:300],
                        "prompt_length": len(prompt),
                        "model": resolved_model,
                    },
                )
                print(f"[LANGSMITH] Run created with ID: {run.id if hasattr(run, 'id') else run}", file=sys.stderr)
            except Exception as e:
                print(f"[LANGSMITH] Failed to create run: {e}", file=sys.stderr)
                run = None
        
        # Try to get the answer from the API
        answer = ""
        api_error = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
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
            if completion_tokens == 0:
                completion_tokens = _estimate_tokens(answer)
            if total_tokens == 0:
                total_tokens = prompt_tokens + completion_tokens
                
        except Exception as e:
            print(f"[AI_QUERY] ERROR during API call: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            api_error = str(e)
            answer = f"[ERROR] {type(e).__name__}: {e}"
            prompt_tokens = _estimate_tokens(prompt)
            completion_tokens = _estimate_tokens(answer)
            total_tokens = prompt_tokens + completion_tokens
            success = False
        
        # ALWAYS end the run (only once, AFTER we have all data)
        print(f"[LANGSMITH] About to end run: run={run is not None}, _ls_client={_ls_client is not None}, run_ended={run_ended}, success={success}", file=sys.stderr)
        
        if run and _ls_client and not run_ended:
            try:
                run_id = run.id if hasattr(run, 'id') else run
                print(f"[LANGSMITH] Ending run with ID: {run_id}", file=sys.stderr)
                print(f"[LANGSMITH] run object type: {type(run)}, run_id type: {type(run_id)}", file=sys.stderr)
                
                if success:
                    # API call succeeded - end run with outputs
                    outputs = {
                        "answer": str(answer[:500]) if answer else "",
                        "prompt_tokens": int(prompt_tokens),
                        "completion_tokens": int(completion_tokens),
                        "total_tokens": int(total_tokens),
                    }
                    print(f"[LANGSMITH] Outputs dict: {outputs}", file=sys.stderr)
                    print(f"[LANGSMITH] Output types: answer={type(outputs['answer'])}, tokens={type(outputs['prompt_tokens'])}", file=sys.stderr)
                    print(f"[LANGSMITH] Calling end_run with outputs...", file=sys.stderr)
                    _ls_client.end_run(run_id, outputs=outputs)
                    print(f"[LANGSMITH] end_run(outputs=...) completed without exception", file=sys.stderr)
                else:
                    # API call failed - end run with error
                    print(f"[LANGSMITH] Calling end_run with error: {api_error}", file=sys.stderr)
                    _ls_client.end_run(run_id, error=api_error)
                    print(f"[LANGSMITH] end_run(error=...) completed without exception", file=sys.stderr)
                
                run_ended = True
                    
            except Exception as ls_error:
                print(f"[LANGSMITH] CRITICAL ERROR: Failed to end_run: {type(ls_error).__name__}: {ls_error}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
        
        # Return result
        estimated_tokens = prompt_tokens is None or completion_tokens is None
        return {
            "answer": answer,
            "elapsed_seconds": time.perf_counter() - start,
            "used_live_api": api_error is None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_tokens": estimated_tokens,
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
        "used_live_api": False,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_tokens": True,
        "temperature": resolved_temperature,
    }
