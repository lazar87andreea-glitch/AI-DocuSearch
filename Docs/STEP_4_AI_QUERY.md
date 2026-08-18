# DocuSearch — Step 4: AI Query & Answer Generation

## Overview
The AI query step generates answers to user questions based on the context retrieved from previous steps. It calls a live, OpenAI-compatible chat completions API over HTTPS and falls back to a simulated answer when no provider is configured or the request fails.

## Purpose
- Generate natural language answers to user questions
- Use retrieved document context for grounding answers in real data
- Call any OpenAI-compatible LLM provider when configured (OpenAI, xAI/Grok, Groq, Together, etc.)
- Provide a safe, deterministic fallback when the API key/URL/model are missing or the request fails

## Key Concepts

### Prompt Engineering
- **Definition:** Crafting input prompts to guide LLM behavior
- **Context Injection:** Including relevant document sections in prompt
- **Prompt Structure:** Question + context + instruction for answer format

### LLM Backend
- **Primary:** Any OpenAI-compatible REST API (`/chat/completions`), called via `requests`
- **Fallback:** Simulated answer — used when configuration is missing or the request fails
- **Provider-agnostic:** the project doesn't hardcode a specific vendor; it just needs an API key,
  base URL, and model name that speak the OpenAI chat completions format

### Generation Parameters
- **Temperature:** Fixed at `0.2` for the request (low randomness, more deterministic answers)
- **Timeout:** 60 seconds per request

---

## Detailed Implementation Steps

### Step 4.1: Resolve Configuration
```python
def generate_answer(prompt: str, model_name: Optional[str] = None) -> str:
```

**Process:**

1. **Read environment variables** (via `os.getenv`), in priority order:
   - `api_key` — `LLM_API_KEY`, else `OPENAI_API_KEY`, else `XAI_API_KEY`, else `GROK_API_KEY`
   - `base_url` — `LLM_API_BASE`, else `OPENAI_API_BASE`, else `XAI_API_BASE`, else `GROK_API_BASE`;
     if still unset and `OPENAI_API_KEY` is present, defaults to `https://api.openai.com/v1`
   - `resolved_model` — `model_name` argument, else `LLM_MODEL`, else `OPENAI_MODEL`, else `XAI_MODEL`, else `GROK_MODEL`
2. **Debug logging:** prints whether an API key is present, the base URL, and the resolved model to `stderr`.
3. If `api_key`, `base_url`, and `resolved_model` are all present, proceed to Step 4.2. Otherwise, skip directly to the simulated fallback (Step 4.3).

**`LLM_*` variables are the recommended, provider-agnostic way to configure this project.** The
`OPENAI_*` and legacy `XAI_*`/`GROK_*` names are supported as fallbacks for convenience and
backward compatibility, but new setups should prefer `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL`.

**Example `.env` configuration (any OpenAI-compatible provider):**
```env
LLM_API_KEY=your_key_here
LLM_API_BASE=https://api.x.ai/v1
LLM_MODEL=grok-4
```

```env
# OpenAI example
LLM_API_KEY=your_key_here
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

---

### Step 4.2: Call the LLM API
**Process:**

1. **Build the request payload:**
   ```python
   payload = {
       "model": resolved_model,
       "messages": [{"role": "user", "content": prompt}],
       "temperature": 0.2,
   }
   headers = {
       "Authorization": f"Bearer {api_key}",
       "Content-Type": "application/json",
   }
   ```
2. **POST** to `f"{base_url.rstrip('/')}/chat/completions"` with a 60-second timeout.
3. **Raise on HTTP errors** via `resp.raise_for_status()`.
4. **Extract the answer** from `data["choices"][0]["message"]["content"]`.
5. On success, return the answer string directly.

**Error handling:** Any exception (network error, timeout, non-2xx response, malformed JSON) is caught, logged to `stderr` with a traceback, and execution falls through to the simulated fallback — `generate_answer` never raises to the caller.

---

### Step 4.3: Simulated Fallback
**Triggered when:**
- Any of `api_key`, `base_url`, or `resolved_model` is missing, **or**
- The API request raised an exception

**Behavior:**
```python
snippet = prompt[:100].replace("\n", " ")
return f"[SIMULATED ANSWER] {snippet}..."
```

This guarantees `generate_answer` always returns a string and never crashes the calling pipeline, even with no network access or missing credentials.

---

### Step 4.4: Metrics-Aware Variant — `generate_answer_with_meta`
```python
def generate_answer_with_meta(prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
```

Runs the exact same resolution/request/fallback logic as `generate_answer` (Steps 4.1–4.3), but
returns a dict instead of a bare string so callers can display timing and token metrics:

```python
{
    "answer": str,
    "elapsed_seconds": float,       # wall-clock time for this call
    "used_live_api": bool,          # False if the simulated fallback was used
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "estimated_tokens": bool,       # True if tokens are a heuristic, not real provider usage
}
```

**Token accounting:**
- If the provider's JSON response includes a top-level `"usage"` object (the OpenAI chat
  completions convention: `prompt_tokens` / `completion_tokens` / `total_tokens`), those exact
  values are used and `estimated_tokens` is `False`.
- Otherwise (provider omits `usage`, or the simulated fallback was used), tokens are estimated with
  a `len(text) // 4` heuristic (`_estimate_tokens`) for both the prompt and the answer, and
  `estimated_tokens` is `True`.

`generate_answer(prompt, model_name)` is now implemented as a thin wrapper:
```python
def generate_answer(prompt: str, model_name: Optional[str] = None) -> str:
    return generate_answer_with_meta(prompt, model_name=model_name)["answer"]
```
so existing callers that only need the answer text are unaffected.

---

### Step 4.5: Prompt Construction (In Pipeline)
The prompt itself is built in `src/pipeline.py`, not in this module:

```python
context = "\n\n".join(chunks[i] for i in indices)
prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer concisely and list source chunk indices."
ans = generate_answer(prompt)
```

**Prompt Structure:**
```
Context:
[Retrieved chunk 1]

[Retrieved chunk 2]

[Retrieved chunk 3]

Question: [User question]
Answer concisely and list source chunk indices.
```

---

## Module Location & File Structure
**File:** `src/ai_query.py`

**Functions:**
- `generate_answer(prompt: str, model_name: Optional[str] = None) -> str`
- `generate_answer_with_meta(prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]`
- `_estimate_tokens(text: str) -> int` (internal, `len(text) // 4` heuristic)

**Dependencies:**
- `requests` — HTTP client for the LLM API
- `os`, `sys`, `time`, `typing` — standard library
- `langsmith` (optional) — if installed and `LANGSMITH_TRACING=true`, `generate_answer_with_meta`
  is wrapped in `@traceable(run_type="llm", name="generate_answer")`, sending a run (prompt, answer,
  latency, token counts) to the LangSmith dashboard. If `langsmith` isn't installed, a no-op
  decorator shim is used instead and behavior is unchanged.

**Environment variables (checked in priority order):**
| Purpose | Recommended | Fallbacks (legacy/convenience) |
|---|---|---|
| API key | `LLM_API_KEY` | `OPENAI_API_KEY`, `XAI_API_KEY`, `GROK_API_KEY` |
| Base URL | `LLM_API_BASE` | `OPENAI_API_BASE`, `XAI_API_BASE`, `GROK_API_BASE` (defaults to `https://api.openai.com/v1` if only `OPENAI_API_KEY` is set) |
| Model name | `LLM_MODEL` | `OPENAI_MODEL`, `XAI_MODEL`, `GROK_MODEL` |

**LangSmith tracing variables (optional):**
| Variable | Purpose |
|---|---|
| `LANGSMITH_TRACING` | Set to `true` to enable tracing |
| `LANGSMITH_API_KEY` | API key from https://smith.langchain.com/settings |
| `LANGSMITH_PROJECT` | Project name shown in the dashboard (defaults to `default` if unset) |

---

## Testing Methods

### Test 4.1: Fallback Mode Test (no credentials configured)
```python
from src.ai_query import generate_answer

def test_fallback_mode(monkeypatch):
    for var in ("LLM_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    answer = generate_answer("What are the contract dates?")

    assert isinstance(answer, str)
    assert answer.startswith("[SIMULATED ANSWER]")
    print("✓ Fallback mode test passed")
```

### Test 4.2: Simulated Snippet Test
**Objective:** Verify the fallback truncates the prompt to 100 characters and strips newlines.

```python
def test_simulated_snippet(monkeypatch):
    for var in ("LLM_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    long_prompt = "line one\n" * 30
    answer = generate_answer(long_prompt)

    assert "\n" not in answer
    assert answer == f"[SIMULATED ANSWER] {long_prompt[:100].replace(chr(10), ' ')}..."
    print("✓ Simulated snippet test passed")
```

### Test 4.3: Model Resolution Precedence Test
**Objective:** Verify `model_name` argument takes precedence over `LLM_MODEL` and other fallbacks.

```python
def test_model_resolution(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "grok-4")
    # `model_name` argument should win when both are set; verified indirectly via the
    # payload sent in a mocked `requests.post` call.
```

### Test 4.4: API Success Path Test (mocked, generic provider)
**Objective:** Verify a successful API response is returned unmodified, regardless of provider.

```python
def test_api_success(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE", "https://api.x.ai/v1")
    monkeypatch.setenv("LLM_MODEL", "grok-4")

    class FakeResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "Grounded answer"}}]}

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse())

    answer = generate_answer("Question?")
    assert answer == "Grounded answer"
    print("✓ API success path test passed")
```

### Test 4.5: API Failure Falls Back Test (mocked)
**Objective:** Verify request exceptions are swallowed and the simulated fallback is returned.

```python
def test_api_failure_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE", "https://api.x.ai/v1")
    monkeypatch.setenv("LLM_MODEL", "grok-4")

    import requests
    def boom(*a, **k):
        raise requests.exceptions.Timeout("timed out")
    monkeypatch.setattr(requests, "post", boom)

    answer = generate_answer("Question?")
    assert answer.startswith("[SIMULATED ANSWER]")
    print("✓ API failure fallback test passed")
```

### Test 4.6: OpenAI Default Base URL Test
**Objective:** Verify that setting only `OPENAI_API_KEY` (no base URL) defaults to OpenAI's endpoint.

```python
def test_openai_default_base_url(monkeypatch):
    for var in ("LLM_API_KEY", "LLM_API_BASE", "XAI_API_KEY", "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    captured = {}
    import requests
    def fake_post(url, **kwargs):
        captured["url"] = url
        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}
        return R()
    monkeypatch.setattr(requests, "post", fake_post)

    generate_answer("Question?")
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    print("✓ OpenAI default base URL test passed")
```

---

## Running Tests from Command Line

### Quick Manual Test (no credentials, uses fallback)
```bash
python -c "from src.ai_query import generate_answer; print(generate_answer('What is AI?'))"
```

### Using the Module Directly
```bash
python src/ai_query.py
```
This runs `generate_answer("Hello world")` and prints the result — either a live answer from the configured provider (if `.env` is configured) or the simulated fallback.

---

## Prompt Engineering Best Practices

### For Document Q&A (Default, used by `src/pipeline.py`)
```python
prompt = f"""Context:
{context}

Question: {question}

Answer concisely and list source chunk indices."""
```

### For Summarization
```python
prompt = f"""Document Content:
{context}

Provide a concise summary of the key points in 2-3 sentences."""
```

### For Translation
```python
prompt = f"""Text to translate:
{context}

Translate to {target_language}. Keep formatting."""
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Always getting `[SIMULATED ANSWER]` | Missing `LLM_API_KEY`, `LLM_API_BASE`, or `LLM_MODEL` (and no supported fallback var set) | Set all three in `.env` (or `OPENAI_API_KEY` + `OPENAI_MODEL` for OpenAI) |
| `401`/`403` from API | Invalid or expired API key | Verify `LLM_API_KEY` (or provider-specific key) in `.env` |
| `404` or connection errors | Wrong `LLM_API_BASE` | Confirm base URL matches your provider, e.g. `https://api.openai.com/v1` or `https://api.x.ai/v1` |
| Request times out | Network issue or slow API response | Retry; requests time out after 60s |
| Irrelevant answers | Poor retrieval or prompt | Improve retrieval or adjust prompt in `src/pipeline.py` |
| No visible errors but wrong output | Silent fallback due to caught exception | Check `stderr` logs — every failure path logs `[AI_QUERY] ERROR: ...` |
| Switching providers doesn't work | Old `.env` values still cached in a running process | Restart the app after editing `.env` |

---

## Integration with Pipeline

This module is called by the **Pipeline** step:

```python
# From src/pipeline.py
def answer_question(pipeline: Dict[str, Any], question: str, top_k: int = 3):
    # ... retrieval happens here (semantic search or lite-mode keyword search) ...

    # AI Query module used here:
    ans = generate_answer(prompt)

    return {
        "query": question,
        "raw_answer": ans,
        "source_chunks": indices,
        "lite_mode": pipeline.get("index") is None,
    }
```

The answer generation is the final step before returning results to the user.

---

## Performance Considerations

- **Live API call:** typically 1-10 seconds depending on prompt length, provider, and network latency
- **Fallback mode:** effectively instant (<1ms), no network call
- **Timeout ceiling:** requests are aborted after 60 seconds and fall back to the simulated answer

---

## Switching Providers

Because `generate_answer` only assumes an OpenAI-compatible `/chat/completions` endpoint, switching
providers is a configuration change, not a code change:

| Provider | `LLM_API_BASE` | Example `LLM_MODEL` |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| xAI / Grok | `https://api.x.ai/v1` | `grok-4` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` |

---

## Future Enhancements

### Additional Backends
```python
# Could support:
# - Providers with non-OpenAI-compatible APIs (would need a small adapter layer)
# - Local model backends for fully offline use
```

### Advanced Generation Control
```python
# Could add:
# - Configurable temperature and max token length
# - Streaming responses
# - Prompt templates per document type
```
