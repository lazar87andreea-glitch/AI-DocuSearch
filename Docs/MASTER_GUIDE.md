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

### 1. Intelligent Retrieval with Automatic Fallback (Hybrid Mode)
The app intelligently attempts retrieval-augmented generation (RAG) with full embeddings first.
If that fails (low memory, model unavailable), it seamlessly falls back to direct LLM processing.
This ensures best-quality answers with reliable fallback behavior.

### 2. Multilingual and Localized Responses
The UI automatically detects user language from browser headers or IP geolocation.
The LLM is instructed to respond in the user's question language.
Translated strings are available for English, Romanian, French, Spanish, and German. The current
Home page does not expose the optional manual language selector, so failed detection defaults to English.

### 3. Document-aware and metadata-rich
The system extracts and tracks document metadata (page count for PDFs).
This information is passed to the LLM so users can ask "How many pages?" and get accurate answers.
All document properties are accessible in prompts.

### 4. Retrieval first, fallback second
When resources permit, retrieve the most relevant sections of a document before answering. 
This reduces hallucination and keeps answers anchored to the actual content.
If retrieval isn't available, fall back to the full document text.

### 5. Stability over complexity
For low-memory or low-resource environments, the system gracefully adapts to ensure usability.
No crashes, no frozen UI, no failed downloads — just reliable answers.

## Current Status & Feature Completion

**Overall:** Experimental and suitable for local evaluation and controlled user testing. It is not
presented as production-ready; see the known limitations and legal documents before using sensitive data.

| Step | Module | Status | Notes |
|------|--------|--------|-------|
| **Step 1** | Ingestion | ✅ Complete | PDF, DOCX, TXT + OCR fallback |
| **Step 2** | Preprocessing | ✅ Complete | Chunking with overlap, cleaning |
| **Step 3** | Embeddings & Index | ✅ Complete | FAISS + NumPy fallback, memory guards, lazy loading |
| **Step 4** | AI Query + LangSmith | ✅ Complete | Full implementation with manual Client tracing working |
| **Step 5** | Pipeline | ✅ Complete | Web embedding attempt with keyword and Direct LLM fallbacks |
| **Step 6** | History Tracking | ✅ 95% | Hybrid storage (in-memory + disk) working; sidebar UI deferred |
| **Step 7** | Cloud Deployment | ⚠️ 80% | Deploys; secrets loading partially hardened; needs testing |
| **Step 8** | Feedback Collection | ✅ Complete | Thumbs up/down ratings, detailed feedback, per-session isolation |
| **Step 9** | Internationalization | ✅ Complete | Multilingual UI, auto language detection, document metadata |
| **Cost Tracking** | Budget Management | ✅ Complete | Grok pricing ($0.03/1K in, $0.10/1K out), real-time badge, warnings, blocking |
| **GDPR Compliance** | Privacy & Legal | ✅ Complete | Consent banner, data export/deletion, footer links, legal docs |
| **UI Chat** | Streamlit App | ✅ Complete | Hybrid mode only, chat bubbles, responsive mobile, page count |
| **UI Metrics** | Display | ✅ Available | Hidden by default behind the Show metrics control |

---

## Key Accomplishments

- 📄 **Multi-format ingestion:** PDF (with OCR), DOCX (with tables), TXT
- 🔍 **Semantic search:** FAISS indexing with fallbacks (NumPy, keyword overlap)
- 💬 **Conversational UI:** Chat interface with left/right bubbles, timestamps, mode badges
- 💾 **Persistent history:** Dual-layer storage (session cache + disk JSON per user)
- 📊 **LangSmith tracing:** Manual Client-based tracing for debugging
- 📋 **User feedback collection:** Thumbs up/down ratings + detailed feedback + analytics export
- 🌍 **Multilingual support:** Auto-detected language, translated UI (English, Romanian, French, Spanish, German)
- 📄 **Document metadata:** Automatic page count detection for PDFs, metadata accessible to LLM
- 🗣️ **Language-aware responses:** LLM responds in the user's question language
- 💰 **Cost tracking & budgeting:** Real-time LLM usage monitoring with Grok pricing, visual badge, budget warnings and blocking
- � **Semantic fallback:** Automatic Direct LLM invocation when RAG can't answer document-based questions
- �🔐 **GDPR compliance:** Consent banner, user data export/deletion, privacy policy, terms of service, third-party service disclosure, footer links
- 🌐 **Responsive design:** Desktop + mobile optimized
- 🛡️ **Stability:** Graceful fallbacks for memory/model/API failures

---

## Known Issues & Roadmap

**Blocking (Sprint 1):**
- ✅ LangSmith tracing fully implemented and working

**Backlog (Sprint 2-4):**
- 🟡 History sidebar UI (clickable re-run) — deferred to Sprint 2
- 🟡 CLI history tool — needs testing
- 🟡 Multi-document search — enhancement
- 🟡 Analytics dashboard — enhancement

See `IMPLEMENTATION_IMPROVEMENTS.md` for full roadmap.

## File structure

```text
AI DocuSearch/
├── README.md                          # Project overview & quick start
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
├── packages.txt                       # System dependencies (Streamlit Cloud)
├── demo.py                            # CLI demo script
├── web_app.py                         # Streamlit navigation entry point
├── THIRD_PARTY_SERVICES.md            # External-provider disclosure
├── app_pages/
│   ├── home.py                        # Main document Q&A application
│   ├── privacy_policy.py              # In-app Privacy Policy
│   ├── terms_of_service.py            # In-app Terms of Service
│   └── third_party_services.py        # In-app provider disclosure
├── test_ingest.py                     # Document ingestion tests
├── test_langsmith.py                  # LangSmith configuration verification
├── test_feedback.py                   # Feedback collection tests
├── export_feedback.py                 # Feedback analytics & export tool
├── src/
│   ├── ai_query.py
│   ├── cost_tracker.py                 # Cost tracking & budget management (NEW)
│   ├── embed_index.py
│   ├── feedback_manager.py            # User feedback collection (NEW)
│   ├── gdpr_compliance.py             # GDPR features: consent, data export/deletion (NEW)
│   ├── history_manager.py
│   ├── i18n.py                        # Internationalization & multilingual support (NEW)
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
│   ├── STEP_7_STREAMLIT_CLOUD_DEPLOYMENT.md
│   ├── STEP_8_FEEDBACK_COLLECTION.md
│   ├── STEP_9_INTERNATIONALIZATION.md
│   ├── STEP_10_COST_TRACKING.md              # LLM budget management (NEW)
│   └── STEP_11_GDPR_COMPLIANCE.md            # Privacy & legal framework (NEW)
├── examples/
│   └── sample.txt
├── PRIVACY_POLICY.md                   # GDPR/CCPA compliance documentation (NEW)
├── TERMS_OF_SERVICE.md                 # User agreement & AI disclaimers (NEW)
└── ...
```

## Environment configuration

Create a `.env` file based on `.env.example` before testing the app.

Required variables:

```env
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.x.ai/v1
LLM_MODEL=grok-4
```

`LLM_API_BASE`/`LLM_MODEL` work with any OpenAI-compatible chat completions provider — point them
at OpenAI, xAI/Grok, Groq, or another compatible provider.

`DOCUSEARCH_LITE_MODE` is optional. It controls the default only when a pipeline caller omits
`use_embeddings` (the CLI currently does). The Streamlit Home page passes `use_embeddings=True`,
so this variable does not select the web app's initial retrieval mode.

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

After uploading a document and entering a question, the app runs its single **Hybrid** workflow.

## Example usage

```bash
python demo.py examples/sample.pdf "What are the contract dates?"
```

## Important runtime behavior

The web app explicitly attempts embeddings. The project can fall back to keyword retrieval or
Direct LLM answering when:
- memory is low
- the index build fails
- the environment is too constrained for a full embedding flow

`DOCUSEARCH_LITE_MODE` is not part of this web decision because Home supplies an explicit
`use_embeddings=True` argument. It remains available to CLI and library callers that omit the argument.

## Module responsibilities

### `src/ingest.py`
Responsible for extracting plain text from uploaded files.

### `src/preprocess.py`
Responsible for normalizing and splitting text into manageable chunks.

### `src/embed_index.py`
Responsible for generating embeddings and searching the document space for relevant chunks.

### `src/ai_query.py`
Responsible for calling the configured LLM provider's chat completions API (any OpenAI-compatible
endpoint, e.g. OpenAI, xAI/Grok, Groq) and returning the model response.

### `src/pipeline.py`
Responsible for coordinating the whole flow and deciding whether to use the full RAG path or the
fallback path. `answer_question()` returns the answer and supporting metadata.

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
- Same Hybrid workflow as desktop, with a denser metrics layout
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
This is usually caused by embedding/model startup on low-memory hardware. Reducing the document
size can help. `DOCUSEARCH_LITE_MODE` does not change the current Streamlit path because Home
explicitly requests embeddings.

### API errors
Check `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` in `.env`.

## Recommended deployment stance

For this experimental repository, the current behavior is:
- attempt semantic retrieval in the Streamlit app
- use keyword retrieval when an embedding index cannot be built
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
