# DocuSearch - Step 4: AI Query and Answer Generation

## Overview

`src/ai_query.py` sends prompts to an OpenAI-compatible `/chat/completions` endpoint and returns
answer, timing, token, tracing, and response-state metadata. The Streamlit UI uses that state to
decide whether a result may be displayed, counted, stored, or rated.

## Configuration

`generate_answer_with_meta()` resolves provider settings in this order:

| Purpose | Preferred variable | Compatibility fallbacks |
|---|---|---|
| API key | `LLM_API_KEY` | `OPENAI_API_KEY`, `XAI_API_KEY`, `GROK_API_KEY` |
| Base URL | `LLM_API_BASE` | `OPENAI_API_BASE`, `XAI_API_BASE`, `GROK_API_BASE` |
| Model | Function argument, then `LLM_MODEL` | `OPENAI_MODEL`, `XAI_MODEL`, `GROK_MODEL` |

If `OPENAI_API_KEY` is configured without a base URL, the base defaults to
`https://api.openai.com/v1`.

Example:

```env
LLM_API_KEY=your_key_here
LLM_API_BASE=https://api.x.ai/v1
LLM_MODEL=grok-4
LLM_TEMPERATURE=0.2
```

## Temperature

The core function accepts an optional explicit `temperature`. Its direct precedence is:

1. Explicit function argument
2. `LLM_TEMPERATURE`
3. `0.2`

The pipeline and Home page load prompt templates through
`src.prompt_loader.load_prompt_with_temperature()`. For those callers, a
`# temperature: <value>` directive on the first line of the prompt file is passed as the explicit
argument and therefore takes precedence over the environment variable.

## Provider Request

For complete configuration, the function posts this shape to
`{base_url}/chat/completions` with a 60-second timeout:

```python
payload = {
    "model": resolved_model,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": resolved_temperature,
}
```

The response is read from `choices[0].message.content`. Network errors, timeouts, non-success HTTP
responses, malformed JSON, and incompatible response shapes are caught and represented as an
explicit error result.

## Response Contract

`generate_answer_with_meta()` returns:

```python
{
    "answer": str,
    "elapsed_seconds": float,
    "response_status": "success" | "simulated" | "error",
    "error_type": str | None,
    "error_message": str | None,
    "used_live_api": bool,
    "langsmith_run_id": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "estimated_tokens": bool,
    "temperature": float,
}
```

### Success

- `response_status="success"`
- `answer` contains the provider response
- `used_live_api=True`
- Provider token usage is used when available
- Missing or zero usage fields are estimated with the approximate `len(text) // 4` heuristic
- The Streamlit app may display, count, save, and accept feedback for the answer

### Missing Configuration

- `response_status="simulated"`
- `answer` contains a labeled `[SIMULATED ANSWER]` preview
- `error_type="configuration_missing"`
- Token values are estimates
- The Streamlit app displays the preview but does not count or save it

### Configured Provider Failure

- `response_status="error"`
- `answer` is empty
- `error_type` and `error_message` describe the exception
- Token counts are zero and `used_live_api=False`
- The Streamlit app displays an error and does not count, save, or rate the request

The zero-token result describes the app's accounting. A provider may still bill work performed
before an error, so the provider dashboard remains authoritative for actual charges.

## Prompt Templates

- `prompts/rag_prompt.txt` receives `{context}`, `{question}`, and `{document_info}`.
- `prompts/direct_llm_prompt.txt` receives `{document_text}`, `{question}`, and `{document_info}`.
- Both templates instruct the model to respond in the same language as the question.
- An optional first line such as `# temperature: 0.2` configures that prompt and is removed before
  the request is sent.

`src/pipeline.py` constructs the RAG prompt. `app_pages/home.py` constructs the Direct LLM prompt
used by the internal Hybrid fallback.

## LangSmith Tracing

When `LANGSMITH_API_KEY` is present and `LANGSMITH_TRACING=true`, the function performs a
best-effort manual run lifecycle:

1. Generate a UUID for the LLM run.
2. Call `Client.create_run(..., id=run_id, run_type="llm")` before the provider request.
3. Call `Client.update_run()` with outputs on success or an error on failure.
4. Return the run ID so Helpful/Not helpful feedback can reference the answer trace.

LangSmith setup or delivery failures are logged but do not replace the provider result.

Optional variables:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=ai-docusearch
LANGSMITH_FEEDBACK_ENABLED=true
```

## Integration

`src.pipeline.answer_question()` propagates the complete response state. The Home page preserves
the same contract through RAG, Direct LLM, and Hybrid paths. Only `response_status="success"`
results are sent to the app cost tracker and local history.

## Validation

Run the focused offline regression suite:

```powershell
python test_ai_query.py
```

It covers provider success, configured-provider failure, missing-configuration simulation,
pipeline propagation, and the Streamlit rule that failed requests are not written to history.
