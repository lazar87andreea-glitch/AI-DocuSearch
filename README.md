# AI DocuSearch

AI DocuSearch is a document-aware AI search and Q&A agent built in Python. It extracts text from uploaded documents, preprocesses and chunks the content, retrieves relevant sections, and uses a live LLM to answer questions grounded in the source material.

This project is designed to be simple, explainable, and Git-friendly while remaining practical for local use and browser-based demos.

## Overview

AI DocuSearch supports:
- **PDF, DOCX, and TXT ingestion** — with automatic OCR fallback for scanned PDFs
- **Multi-language support** — OCR works with Romanian, English, and other languages (via Tesseract)
- **Multilingual UI** — Automatic language detection from browser/IP, with manual language selector (English, Romanian, French, Spanish, German)
- **Document metadata** — Automatic page count detection for PDFs (users can ask "How many pages?")
- **Cleaning and chunking for retrieval**
- **Lightweight retrieval fallback** for low-memory environments
- **Live LLM integration** with any OpenAI-compatible provider (OpenAI, xAI/Grok, Groq, etc.)
- **Language-aware LLM responses** — LLM automatically responds in the user's question language
- **Browser-based Streamlit app** — runs Hybrid mode with intelligent fallback and performance metrics
- **Mobile-optimized UI** — responsive design for Android, iOS, and desktop browsers
- **Streamlit Cloud ready** — deploy in minutes with Secrets configuration
- **LangSmith tracing** — optional observability for all LLM calls
- **Git-ready project structure** and comprehensive documentation

## Why this project exists

The core idea is retrieval-augmented generation (RAG):
- retrieve the most relevant document sections
- pass them to the LLM as context
- generate a grounded answer based on the document, not generic memory

When the full embedding pipeline is unavailable or too heavy for the current environment, the app can safely fall back to a lightweight mode without crashing the browser experience.

## Architecture

```text
User question
      |
      v
Document upload / file path
      |
      v
Text extraction
      |
      v
Preprocessing and chunking
      |
      v
Relevant chunk retrieval
      |
      v
LLM answer generation with document context
      |
      v
Final answer + source chunks
```

## Project structure

```text
AI DocuSearch/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── packages.txt                    # System dependencies for Streamlit Cloud
├── demo.py
├── web_app.py
├── test_ingest.py
├── test_langsmith.py               # LangSmith configuration verification
├── src/
│   ├── ai_query.py
│   ├── embed_index.py
│   ├── i18n.py                     # Internationalization (multilingual support)
│   ├── ingest.py
│   ├── pipeline.py
│   ├── preprocess.py
│   ├── prompt_loader.py
│   └── history_manager.py
├── prompts/
│   ├── rag_prompt.txt
│   └── direct_llm_prompt.txt
├── Docs/
│   ├── MASTER_GUIDE.md
│   ├── STEP_1_INGEST.md
│   ├── STEP_2_PREPROCESS.md
│   ├── STEP_3_EMBEDDING_INDEXING.md
│   ├── STEP_4_AI_QUERY.md
│   ├── STEP_5_PIPELINE.md
│   ├── STEP_6_HISTORY_TRACKING.md
│   └── STEP_7_STREAMLIT_CLOUD_DEPLOYMENT.md
├── examples/
└── ...
```

## Requirements

- Python 3.10+
- pip
- Virtual environment recommended
- An API key for any OpenAI-compatible LLM provider (OpenAI, xAI/Grok, Groq, etc.) via `.env`

## Quick start

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the sample file and fill in the values:

```bash
copy .env.example .env
```

Example values:

```env
LLM_API_KEY=your_key_here
LLM_API_BASE=https://api.x.ai/v1
LLM_MODEL=grok-4
DOCUSEARCH_LITE_MODE=true
```

The `LLM_API_BASE`/`LLM_MODEL` pair can point at any OpenAI-compatible chat completions API —
swap them for OpenAI, Groq, or another provider without changing any code.

## Run the app

```bash
python -m streamlit run web_app.py
```

After uploading a document and asking a question, the app uses **Hybrid Mode** — the most intelligent and resilient approach:

- **Hybrid Mode** — tries the full RAG pipeline first (chunks document, builds embedding index, retrieves relevant chunks)
- Falls back to direct text-to-LLM if embeddings/retrieval fails (low memory, model unavailable, etc.)
- Automatically adapts to available resources (works on mobile, desktop, low-memory environments)
- Provides best-quality answers with reliable fallback behavior

The answer is displayed with a **📊 Show metrics** button underneath — click it to reveal total time, 
build/retrieval/generation time breakdown, chunks used, context size, and token counts. Metrics stay hidden 
until requested, keeping the default view focused on the answer.

## Example usage

```bash
python demo.py examples/sample.pdf "What are the contract dates?"
```

## Important design note

The project follows the intended RAG workflow whenever the embedding/index pipeline is available. However, for low-memory or low-resource environments, a safe fallback mode is enabled to prevent browser freezes and model-download failures.

This means:
- full retrieval mode is the desired path
- lightweight mode is the stability fallback
- the configured LLM provider remains the live answer engine

## Files of interest

- `src/pipeline.py` — main flow for document ingestion, chunking, retrieval, and answer generation
- `src/ai_query.py` — live LLM request wrapper (any OpenAI-compatible provider)
- `src/ingest.py` — document ingestion and text extraction
- `src/preprocess.py` — document cleaning and chunk splitting
- `src/prompt_loader.py` — loads prompt templates from `prompts/`
- `prompts/rag_prompt.txt` — prompt template for retrieval-augmented generation (used when embeddings succeed)
- `prompts/direct_llm_prompt.txt` — prompt template for direct LLM fallback (used when retrieval unavailable)
- `web_app.py` — Streamlit browser app with Hybrid mode and performance metrics

## Adjusting temperature

There is no temperature control in the UI. Instead, edit the `# temperature: <value>` line at the
top of the prompt files (`prompts/rag_prompt.txt` and `prompts/direct_llm_prompt.txt`) — e.g. change it to
`# temperature: 0.7` for more varied answers. This line is stripped before the prompt is sent to
the LLM. If a prompt file has no such line, `LLM_TEMPERATURE` from `.env` is used, then `0.2`.

## Optional: LangSmith tracing

Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env` (see `.env.example`) to send a run
for every `generate_answer` call, `build_pipeline` call, and `answer_question` call to your
[LangSmith](https://smith.langchain.com) dashboard — including latency and prompt/completion
tokens. Runs for the Hybrid mode also show whether RAG succeeded or fell back to Direct LLM,
nested as a trace tree. Tracing is entirely optional: if `langsmith` isn't installed or
tracing isn't enabled, the app behaves exactly the same with no extra network calls.

**Verify LangSmith is working:** Run `python test_langsmith.py` to confirm the connection to your LangSmith project.

## Streamlit Cloud Deployment

Deploy the app to [Streamlit Cloud](https://streamlit.io/cloud) in minutes:

### 1. Push to GitHub

Ensure your repository has:
- `requirements.txt` — all Python dependencies
- `packages.txt` — system dependencies (Tesseract OCR, Poppler, etc.) for scanned PDF support
- `.env.example` — example env file (do NOT push `.env` with real keys)

### 2. Create Streamlit Cloud app

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your GitHub repo, branch, and `web_app.py`
4. Click "Deploy"

### 3. Configure Secrets

After deployment, go to **Settings** → **Secrets** and add:

```toml
OPENAI_API_KEY = "sk-..."
LANGSMITH_API_KEY = "lsv2_pt_..."
LANGSMITH_TRACING = "true"
LANGSMITH_PROJECT = "ai-docusearch"
```

**Note:** Replace with your actual API keys. These are NOT read from `.env` on Streamlit Cloud — they must be set in the web UI.

### 4. Supported Formats

- **Searchable PDFs** — text extracted instantly ✓
- **Scanned PDFs (including Romanian)** — OCR fallback (30-60 seconds) ✓
- **DOCX files** — extracted with table support ✓
- **TXT files** — raw text ✓

## Mobile Browser Support

The app is optimized for mobile browsers (Android, iOS):
- ✅ Responsive layout (2-column metrics on mobile, 4-column on desktop)
- ✅ Hybrid mode adapts intelligently to mobile resources (tries RAG, falls back as needed)
- ✅ Touch-friendly buttons and text input
- ✅ Works offline after page loads

Test on mobile: Upload a document and ask a question — Hybrid mode handles it automatically.

## Documentation

The documentation set in the `Docs/` folder covers:
- ingestion and extraction
- preprocessing and chunking
- embedding and indexing
- AI answer generation
- full pipeline orchestration

## Git-ready status

This repository is prepared for clean Git publication:
- clear project naming
- English documentation
- environment variable config via `.env.example`
- `.gitignore` for Python and local secrets
- project-level docs suitable for a public repo

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Note

This README reflects the project name and current architecture as AI DocuSearch.
