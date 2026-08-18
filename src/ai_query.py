import os
import sys
import time
from typing import Any, Dict, Optional

try:
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
def generate_answer_with_meta(prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Same resolution/request logic as generate_answer, plus timing and token metrics."""
    start = time.perf_counter()

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

    if api_key and base_url and resolved_model:
        try:
            import requests

            payload = {
                "model": resolved_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
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

            return {
                "answer": answer,
                "elapsed_seconds": time.perf_counter() - start,
                "used_live_api": True,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_tokens": estimated,
            }
        except Exception as e:
            print(f"[AI_QUERY] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
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
    }


def generate_answer(prompt: str, model_name: Optional[str] = None) -> str:
    return generate_answer_with_meta(prompt, model_name=model_name)["answer"]


if __name__ == "__main__":
    print(generate_answer("Hello world"))


