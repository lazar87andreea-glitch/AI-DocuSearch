# AI DocuSearch repository instructions

## Commands

Use the repository virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the Streamlit app:

```powershell
python -m streamlit run web_app.py
```

Run the CLI flow:

```powershell
python demo.py examples/sample.pdf "What are the contract dates?"
# Equivalent module entry point:
python -m src.pipeline examples/sample.pdf "What are the contract dates?"
```

The ingestion tests use a custom script rather than a test runner:

```powershell
python test_ingest.py
```

Run one ingestion test by importing its function:

```powershell
python -c "from test_ingest import test_extract_text_docx_support; test_extract_text_docx_support()"
```

Check optional LangSmith credentials and trace delivery with:

```powershell
python test_langsmith.py
```

## Architecture

- `web_app.py` is the Streamlit entry point. It loads `.env`, copies Streamlit Cloud secrets into
  `os.environ`, initializes LangSmith, and only then imports the `src` modules. Preserve this order:
  tracing decorators and provider configuration are resolved during module import.
- The web app exposes three execution paths:
  - **RAG** calls `build_pipeline(..., use_embeddings=True)` and then `answer_question()`.
  - **Direct LLM** skips chunking/retrieval and sends the full extracted text through
    `prompts/direct_llm_prompt.txt`.
  - **Hybrid** tries RAG and falls back to Direct LLM only when the RAG path raises. Separately,
    `build_pipeline()` can degrade to keyword retrieval without raising when embeddings are
    unavailable or memory is low.
- The core RAG flow is `src/ingest.py` -> `src/preprocess.py` -> `src/embed_index.py` ->
  `src/pipeline.py` -> `src/ai_query.py`. `src/prompt_loader.py` keeps prompt text and sampling
  configuration outside Python code.
- `src/ingest.py` handles searchable PDFs with `pypdf`, then attempts OCR with
  `pdf2image`/Tesseract when no text layer exists. DOCX extraction includes paragraphs and tables;
  other extensions are treated as UTF-8 text except unsupported legacy `.doc`.
- `src/embed_index.py` lazily loads `all-MiniLM-L6-v2`, prefers FAISS cosine search, falls back to
  NumPy similarity, and finally to token-overlap search when embeddings cannot be used.
- `src/ai_query.py` calls any OpenAI-compatible `/chat/completions` endpoint and returns answer,
  timing, token usage, temperature, and live/simulated status. `web_app.py` and `src/pipeline.py`
  depend on this metadata shape for metrics and mode comparison.
- Streamlit Cloud uses Python dependencies from `requirements.txt`, OS-level OCR dependencies from
  `packages.txt`, and secrets configured in the Streamlit UI rather than a committed `.env`.

## Repository conventions

- Lightweight retrieval is the default: when `use_embeddings` is omitted,
  `DOCUSEARCH_LITE_MODE=true` produces `index=None` and keyword retrieval. Keep low-memory and
  missing-model fallbacks usable instead of assuming embeddings always exist.
- Preserve the result dictionary contract shared by RAG, Direct LLM, Hybrid, and the UI:
  `raw_answer`, `source_chunks`, `lite_mode`, build/retrieval/generation/total timings,
  `chunk_count`, `context_chars`, token counts, `estimated_tokens`, `used_live_api`,
  `temperature`, and (in web modes) `fallback_reason`.
- Prompt templates live in `prompts/` and use Python `str.format` placeholders. RAG requires
  `{context}` and `{question}`; Direct LLM requires `{document_text}` and `{question}`.
- Tune each prompt with an optional first line such as `# temperature: 0.2`. Temperature precedence
  is: explicit function argument, prompt-file directive, `LLM_TEMPERATURE`, then `0.2`.
- Prefer provider-neutral `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL`. The provider-specific
  OpenAI/xAI/Grok variables are compatibility fallbacks. Missing or failed API configuration
  intentionally returns a `[SIMULATED ANSWER]` plus estimated token metrics.
- Keep the BLAS thread-limit environment variables at the top of `web_app.py`, before importing
  Streamlit or modules that can load NumPy/model code; they protect low-memory deployments.
- Streamlit reruns are coordinated through `st.session_state`: a new upload or changed question
  clears prior mode results, while metric visibility and comparison state persist across reruns.
- Mobile mode intentionally exposes Direct LLM only; desktop exposes RAG, Direct LLM, and Hybrid.
- OCR can require `TESSERACT_CMD` and `POPPLER_PATH` locally. Streamlit Cloud obtains Tesseract and
  Poppler from `packages.txt`.
- Keep credentials out of source control. `.env` and `.streamlit/` are ignored; update
  `.env.example` when introducing configuration.
