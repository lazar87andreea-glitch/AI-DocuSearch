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

- `web_app.py` is the lightweight Streamlit navigation entry point. `app_pages/home.py` loads
  `.env`, copies Streamlit Cloud secrets into `os.environ`, initializes LangSmith, and only then
  imports most `src` modules. Preserve the initialization order in `app_pages/home.py`: tracing
  decorators and provider configuration are resolved during module import.
- The web app exposes a single, intelligent **Hybrid** execution path:
  - **Hybrid Mode** tries the full RAG pipeline first (chunking, embeddings, retrieval)
  - Falls back to Direct LLM (full text) if RAG fails (low memory, model unavailable, etc.)
  - Internally uses `build_pipeline_from_text(..., use_embeddings=True)` and then `answer_question()`
  - Gracefully degrades without raising errors when embeddings are unavailable or memory is low
- The core RAG flow is `src/ingest.py` -> `src/preprocess.py` -> `src/embed_index.py` ->
  `src/pipeline.py` -> `src/ai_query.py`. `src/prompt_loader.py` keeps prompt text and sampling
  configuration outside Python code.
- `src/ingest.py` handles searchable PDFs with `pypdf`, then attempts OCR with
  `pdf2image`/Tesseract when no text layer exists. Both paths preserve every physical page with a
  `[PDF_PAGE:n]` marker, including empty pages. Includes `get_pdf_page_count()` to extract page metadata.
  DOCX extraction includes paragraphs and tables; other extensions are treated as UTF-8 text except unsupported legacy `.doc`.
- `src/preprocess.py` keeps marked PDF pages separate and copies the page marker into every chunk.
  `src/pipeline.py` detects explicit multilingual page requests and selects matching page chunks
  before embedding or keyword retrieval. Page ranges are limited to five physical PDF pages and
  page context to 30,000 characters.
- `src/i18n.py` provides automatic language detection (from browser Accept-Language header or IP geolocation),
  translation of all UI strings, and language-aware LLM prompts. Supports English, Romanian, French, Spanish, German.
  Language preference is cached in `st.session_state` and can be manually overridden via sidebar selector.
- `src/embed_index.py` lazily loads `all-MiniLM-L6-v2`, prefers FAISS cosine search, falls back to
  NumPy similarity, and finally to token-overlap search when embeddings cannot be used.
- `src/ai_query.py` calls any OpenAI-compatible `/chat/completions` endpoint and returns answer,
  timing, token usage, temperature, and explicit success/simulated/error status.
  `app_pages/home.py` and `src/pipeline.py` depend on this metadata shape.
- Streamlit Cloud uses Python dependencies from `requirements.txt`, OS-level OCR dependencies from
  `packages.txt`, and secrets configured in the Streamlit UI rather than a committed `.env`.

## Repository conventions

- The Streamlit app explicitly passes `use_embeddings=True`; `DOCUSEARCH_LITE_MODE` does not select
  its initial retrieval mode. When another caller omits `use_embeddings`, the environment variable
  controls that caller's default (`true` means keyword retrieval). Keep runtime missing-model and
  low-memory fallbacks usable because an explicit embedding attempt can still return `index=None`.
- Preserve the result dictionary contract shared by RAG, Direct LLM, Hybrid, and the UI:
  `raw_answer`, `source_chunks`, `lite_mode`, build/retrieval/generation/total timings,
  `chunk_count`, `context_chars`, token counts, `estimated_tokens`, `used_live_api`,
  `response_status`, `error_type`, `error_message`,
  `temperature`, `requested_pdf_pages`, and (in web modes) `fallback_reason`.
- Prompt templates live in `prompts/` and use Python `str.format` placeholders. Both RAG and Direct LLM require:
  - `{context}` or `{document_text}` — document content
  - `{question}` — user question
  - `{document_info}` — document metadata (filename, page count, etc.)
  - Prompts should instruct LLM to "Respond in the same language as the question"
- Tune each prompt with an optional first line such as `# temperature: 0.2`. Temperature precedence
  is: explicit function argument, prompt-file directive, `LLM_TEMPERATURE`, then `0.2`.
- Prefer provider-neutral `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL`. The provider-specific
  OpenAI/xAI/Grok variables are compatibility fallbacks. Missing configuration intentionally
  returns a `[SIMULATED ANSWER]`; configured provider failures return no answer and zero tokens.
  Only `response_status="success"` results may be charged, stored in history, or rated.
- Keep the BLAS thread-limit environment variables at the top of `app_pages/home.py`, before importing
  Streamlit or modules that can load NumPy/model code; they protect low-memory deployments.
- Streamlit reruns are coordinated through `st.session_state`: a new upload or changed question
  clears prior mode results, while metric visibility, language preference, and comparison state persist across reruns.
- Language detection is cached in `st.session_state.user_language` and persists across reruns. The
  current Home page does not render the optional language-selector helper.
- Each new Streamlit session receives a random UUID hex identifier. History and feedback managers
  must use that identifier rather than process identity or a hash of the session-state proxy.
- OCR can require `TESSERACT_CMD` and `POPPLER_PATH` locally. Streamlit Cloud obtains Tesseract and
  Poppler from `packages.txt`.
- Keep credentials out of source control. `.env` and `.streamlit/` are ignored; update
  `.env.example` when introducing configuration.
