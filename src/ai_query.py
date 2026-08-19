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


@traceable(run_type="llm", name="generate_answer")
def generate_answer_with_meta(
    prompt: str, model_name: Optional[str] = None, temperature: Optional[float] = None
) -> Dict[str, Any]:
    """Same resolution/request logic as generate_answer, plus timing and token metrics."""
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

    if api_key and base_url and resolved_model:
        # Initialize LangSmith client once
        _ls_client = None
        run = None
        try:
            from langsmith import Client
            _ls_client = Client()
            print(f"[LANGSMITH] Client initialized", file=sys.stderr)
        except Exception as e:
            print(f"[LANGSMITH] Failed to initialize client: {e}", file=sys.stderr)
        
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
                print(f"[LANGSMITH] Run created: {run.id}", file=sys.stderr)
            except Exception as e:
                print(f"[LANGSMITH] Failed to create run: {e}", file=sys.stderr)
        
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
            print(f"[AI_QUERY] SUCCESS: Got answer from LLM API", file=sys.stderr)
            
            # Extract token usage from response
            usage = data.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
            estimated = prompt_tokens is None or completion_tokens is None
            if prompt_tokens is None:
                prompt_tokens = _estimate_tokens(prompt)
            if completion_tokens is None:
                completion_tokens = _estimate_tokens(answer)
            if total_tokens is None:
                total_tokens = prompt_tokens + completion_tokens
            
            # End the LangSmith run successfully with token metrics
            if run and _ls_client:
                try:
                    _ls_client.end_run(
                        run.id, 
                        outputs={
                            "answer": answer[:500],
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                        }
                    )
                    print(f"[LANGSMITH] Run ended successfully: {run.id}", file=sys.stderr)
                except Exception as e:
                    print(f"[LANGSMITH] Failed to end run: {e}", file=sys.stderr)

            return {
                "answer": answer,
                "elapsed_seconds": time.perf_counter() - start,
                "used_live_api": True,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_tokens": estimated,
                "temperature": resolved_temperature,
            }
        except Exception as e:
            print(f"[AI_QUERY] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            
            # End the LangSmith run with error
            if run and _ls_client:
                try:
                    _ls_client.end_run(run.id, error=str(e))
                    print(f"[LANGSMITH] Run ended with error: {run.id}", file=sys.stderr)
                except Exception as ls_err:
                    print(f"[LANGSMITH] Failed to end run with error: {ls_err}", file=sys.stderr)
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


def generate_answer(
    prompt: str, model_name: Optional[str] = None, temperature: Optional[float] = None
) -> str:
    return generate_answer_with_meta(prompt, model_name=model_name, temperature=temperature)["answer"]


if __name__ == "__main__":
    print(generate_answer("Hello world"))


