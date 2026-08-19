# AI DocuSearch — Master Guide

## Project overview

AI DocuSearch is a document-focused AI search and Q&A project designed for local experimentation, browser demos, and practical retrieval-augmented generation workflows. It allows a user to upload a document, extract its text, find relevant sections, and ask a question grounded in the document content.

The project is built around a simple but effective architecture:
- ingest document text
- clean and chunk the content
- optionally build an embedding index
- retrieve relevant chunks
- ask the LLM to answer with the retrieved context
- provide a stable fallback when heavy indexing is not practical

## Core principles

### 1. Retrieval first
The intended design is to retrieve the most relevant sections of a document before answering. This reduces hallucination and keeps answers anchored to the actual content of the document.

### 2. LLM as answer generator
The LLM is used to synthesize a response from the retrieved content. It should not be the only source of information when the document context is available.

### 3. Stability over complexity
For low-memory or low-resource environments, the system includes a lightweight fallback mode so the app remains usable without crashing or downloading heavy models.

## Current architecture

```text
Upload document
     |
     v
Extract text
     |
     v
Clean + chunk text
     |
     v
Build or skip embedding index
     |
     v
Retrieve relevant chunks
     |
     v
LLM uses document context to answer
     |
     v
Return answer + source references
```

## File structure

```text
AI DocuSearch/
├── README.md                          # Project overview & quick start
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
├── packages.txt                       # System dependencies (Streamlit Cloud)
├── demo.py                            # CLI demo script
├── web_app.py                         # Streamlit web application
├── test_ingest.py                     # Document ingestion tests
├── test_langsmith.py                  # LangSmith configuration verification
├── src/
│   ├── ai_query.py
│   ├── embed_index.py
│   ├── ingest.py
│   ├── pipeline.py
│   ├── preprocess.py
│   └── prompt_loader.py
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
│   └── sample.txt
└── ...
```

## Environment configuration

Create a `.env` file based on `.env.example` before testing the app.

Required variables:

```env
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.x.ai/v1
LLM_MODEL=grok-4
DOCUSEARCH_LITE_MODE=true
```

`LLM_API_BASE`/`LLM_MODEL` work with any OpenAI-compatible chat completions provider — point them
at OpenAI, xAI/Grok, Groq, or another compatible provider.

Optional variables:

```env
HOST=0.0.0.0
PORT=8501
LOG_LEVEL=info

# Optional LangSmith tracing (https://smith.langchain.com)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=ai-docusearch
```

When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set, `generate_answer`, `build_pipeline`,
and `answer_question` are automatically traced to LangSmith via the `@traceable` decorator (see
`src/ai_query.py` and `src/pipeline.py`), including latency and token counts. This requires the
optional `langsmith` package (already in `requirements.txt`); if it isn't installed, tracing calls
are safely skipped with no behavior change.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run the app

```bash
python -m streamlit run web_app.py
```

After uploading a document and entering a question, use the **RAG Mode**, **Direct LLM Mode**, and
**Hybrid Mode** tabs to run and compare each approach. Each answer has a **📊 Show metrics** button
underneath (hidden by default) that reveals total time, a build/retrieval/generation time
breakdown, chunk count, context size, and prompt/completion/total token counts (real `usage` data
from the provider when available, otherwise an estimate). A **📊 Show mode comparison** button
appears once two or more modes have been run, revealing a side-by-side table.

## Example usage

```bash
python demo.py examples/sample.pdf "What are the contract dates?"
```

## Important runtime behavior

The full pipeline can be heavy, especially when embedding models are downloaded and indexed locally. The project therefore includes logic to fall back to lightweight retrieval or direct LLM answering when:
- memory is low
- the index build fails
- the environment is too constrained for a full embedding flow

This is a practical design decision for local demo use and not a deviation from the RAG concept. The default design remains retrieval-based; the fallback exists to maintain stability.

## Module responsibilities

### `src/ingest.py`
Responsible for extracting plain text from uploaded files.

### `src/preprocess.py`
Responsible for normalizing and splitting text into manageable chunks.

### `src/embed_index.py`
Responsible for generating embeddings and searching the document space for relevant chunks.

### `src/ai_query.py`
Responsible for calling the configured LLM provider's chat completions API (any OpenAI-compatible
endpoint, e.g. OpenAI, xAI/Grok, Groq) and returning the model response. Also exposes
`generate_answer_with_meta()`, which additionally reports elapsed time and prompt/completion/total
token counts (used by the web app's per-mode metrics).

### `src/pipeline.py`
Responsible for coordinating the whole flow and deciding whether to use the full RAG path or the
fallback path. `answer_question()` returns timing (retrieval/generation/total seconds), chunk
count, context size, and token metrics alongside the answer.

### `src/prompt_loader.py`
Responsible for loading prompt templates from the `prompts/` folder and filling in their
`{placeholder}` fields via `load_prompt(name, **kwargs)`. Keeping prompts as separate `.txt` files
(`prompts/rag_prompt.txt`, `prompts/direct_llm_prompt.txt`) instead of inline strings makes them
easy to find and edit without touching Python code. Each file may start with an optional
`# temperature: <value>` directive line — `load_prompt_with_temperature()` reads and strips it,
falling back to `LLM_TEMPERATURE`, then `0.2`, if absent. This is the intended way to tune
temperature per prompt; there is no runtime/UI control for it.

## Streamlit Cloud Deployment

AI DocuSearch is optimized for [Streamlit Cloud](https://streamlit.io/cloud) deployment with:

- **System dependencies** — `packages.txt` includes Tesseract OCR and Poppler for scanned PDF support
- **Secret management** — App reads `OPENAI_API_KEY`, `LANGSMITH_API_KEY` from Streamlit secrets (not `.env`)
- **Mobile optimization** — Responsive UI detects device type and adjusts layout automatically
- **Language support** — OCR works with Romanian, English, and other Tesseract-supported languages
- **Fast deployment** — Push to GitHub; app redeploys automatically

For detailed deployment instructions, see **Docs/STEP_7_STREAMLIT_CLOUD_DEPLOYMENT.md**.

## Recent Features & Improvements

### OCR Support for Scanned PDFs
- Automatic fallback to OCR when PDF has no text layer
- Supports multi-language documents (Romanian, English, etc.)
- Tesseract OCR + Poppler automatically installed on Streamlit Cloud via `packages.txt`

### Mobile Browser Optimization
- Responsive 2-column layout on mobile (4-column on desktop)
- Direct LLM mode optimized for mobile (RAG/Hybrid modes disabled due to resource limits)
- Touch-friendly buttons and text input

### LangSmith Integration Fix
- App now correctly reads LangSmith credentials from Streamlit Cloud **Secrets** (not just `.env`)
- `test_langsmith.py` included for local verification

### Improved Error Handling
- Better error messages for file extraction failures
- Visible feedback for button clicks and processing status
- Detailed logs for troubleshooting

## Documentation Set

The `Docs/` folder contains step-by-step guides for each component:
- **STEP_1_INGEST.md** — Document text extraction (including OCR)
- **STEP_2_PREPROCESS.md** — Text cleaning and chunking
- **STEP_3_EMBEDDING_INDEXING.md** — Embedding generation and retrieval
- **STEP_4_AI_QUERY.md** — LLM integration and answer generation
- **STEP_5_PIPELINE.md** — Full flow orchestration
- **STEP_6_HISTORY_TRACKING.md** — (Optional) Session history and analytics
- **STEP_7_STREAMLIT_CLOUD_DEPLOYMENT.md** — Deployment and configuration

## Design notes for GitHub publication

For public repo readiness, the following are essential:
- clean project naming
- clear instructions in English
- environment variable examples
- no secrets committed to the repo
- concise architecture and troubleshooting docs
- versioned project structure and notes

## Documentation set

The documents in the `Docs/` folder cover the project in a modular way:

- `STEP_1_INGEST.md` — file ingestion and text extraction
- `STEP_2_PREPROCESS.md` — cleaning and chunking
- `STEP_3_EMBEDDING_INDEXING.md` — embeddings and search
- `STEP_4_AI_QUERY.md` — model response generation
- `STEP_5_PIPELINE.md` — orchestration and full workflow

## Troubleshooting

### Heavy embedding model issues
Use the lightweight mode or reduce the workload. The project includes environment-based fallback logic.

### Browser freezes
This is usually caused by embedding/model startup on low-memory hardware. Prefer the lighter browser app or set `DOCUSEARCH_LITE_MODE=true`.

### API errors
Check `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` in `.env`.

## Recommended final production stance

For this repository, the recommended default is:
- lightweight mode for real-world stability
- retrieval-based flow when resources allow
- any OpenAI-compatible LLM provider as the live reasoning layer

This balances reliability, practicality, and the original RAG intent.

## Next steps for Git upload

Before pushing to a remote repository, ensure:
1. `.env` is excluded via `.gitignore`
2. README reflects the final project name
3. docs are in English and polished
4. examples and source files are included in the repo
5. a license is added if required

## Summary

AI DocuSearch is a practical document-centric AI assistant that shows the intended RAG workflow while remaining usable in constrained environments. It is structured for demos, local testing, and eventual GitHub publication.
