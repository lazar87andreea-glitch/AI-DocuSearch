# AI DocuSearch

AI DocuSearch is a document-aware AI search and Q&A agent built in Python. It extracts text from uploaded documents, preprocesses and chunks the content, retrieves relevant sections, and uses a live LLM to answer questions grounded in the source material.

This project is designed to be simple, explainable, and Git-friendly while remaining practical for local use and browser-based demos.

## Overview

AI DocuSearch supports:
- PDF, DOCX, and TXT ingestion
- Cleaning and chunking for retrieval
- Lightweight retrieval fallback for low-memory environments
- Live LLM integration with any OpenAI-compatible provider (OpenAI, xAI/Grok, Groq, etc.)
- A single browser app that runs RAG, Direct LLM, and Hybrid modes side by side with optional speed/token metrics
- Git-ready project structure and documentation

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
├── demo.py
├── web_app.py
├── test_ingest.py
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
│   └── STEP_5_PIPELINE.md
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

After uploading a document and asking a question, use the **RAG Mode**, **Direct LLM Mode**, and
**Hybrid Mode** tabs to run each approach and compare their results:

- **RAG Mode** — chunks the document, builds an embedding index, retrieves the most relevant
  chunks, then answers using only that context.
- **Direct LLM Mode** — sends the entire extracted document text straight to the LLM, skipping
  chunking/embeddings entirely.
- **Hybrid Mode** — tries the full RAG pipeline first and automatically falls back to Direct LLM
  behavior if the embedding pipeline fails (e.g. low memory).

Each tab shows the answer with a **📊 Show metrics** button underneath — click it to reveal that
run's total time, build/retrieval/generation time breakdown, chunks used, context size, and
prompt/completion/total token counts (from the provider's `usage` field when available, otherwise
estimated). Metrics stay hidden until requested, keeping the default view focused on the answer.
Once two or more modes have been run, a **📊 Show mode comparison** button appears to reveal a
side-by-side table of all of them.

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
- `prompts/rag_prompt.txt` — prompt template used by RAG mode (and Hybrid mode when it succeeds)
- `prompts/direct_llm_prompt.txt` — prompt template used by Direct LLM mode (and Hybrid mode when it falls back)
- `web_app.py` — unified browser app with RAG / Direct LLM / Hybrid mode tabs and metrics

## Adjusting temperature

There is no temperature control in the UI. Instead, edit the `# temperature: <value>` line at the
top of `prompts/rag_prompt.txt` or `prompts/direct_llm_prompt.txt` directly — e.g. change it to
`# temperature: 0.7` for more varied answers. This line is stripped before the prompt is sent to
the LLM. If a prompt file has no such line, `LLM_TEMPERATURE` from `.env` is used, then `0.2`.

## Optional: LangSmith tracing

Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env` (see `.env.example`) to send a run
for every `generate_answer` call, `build_pipeline` call, and `answer_question` call to your
[LangSmith](https://smith.langchain.com) dashboard — including latency and prompt/completion
tokens. Runs for the unified web app also show which mode (RAG / Direct LLM / Hybrid) produced
them, nested as a trace tree. Tracing is entirely optional: if `langsmith` isn't installed or
tracing isn't enabled, the app behaves exactly the same with no extra network calls.

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
