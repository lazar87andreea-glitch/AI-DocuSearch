# AI DocuSearch — Intelligent Document Q&A Powered by Grok

**Developed by:** Andreea Nistor  
**Last Updated:** 2026-08-20

---

## 📌 Project Summary

AI DocuSearch is a lightweight, fast, and customizable AI tool that lets you upload a document (PDF, DOCX, TXT) and ask questions about its content. It extracts text, cleans it, chunks it, embeds it, retrieves relevant sections, and generates answers using Grok or any OpenAI-compatible LLM model.

This project is built with **Streamlit**, **LangSmith**, and a custom RAG pipeline — making it easy to run, easy to extend, and fun to experiment with.

---

## ⭐ Why This App Is Interesting

AI DocuSearch isn't just "chat with your PDF." It's a **full mini-RAG system** with a custom workflow:

- 📄 PDF/DOCX/TXT text extraction
- 🧹 Text cleaning & preprocessing
- ✂️ Smart chunking with overlap
- 🧬 Embedding & vector indexing (FAISS + fallback)
- 🔍 Semantic retrieval (cosine similarity, keyword backup)
- 🤖 LLM answer generation (Grok or custom OpenAI-compatible endpoint)
- 📊 Metadata & token tracking
- 🔍 LangSmith tracing & observability
- 📱 Mobile-friendly Streamlit UI
- 💾 Persistent question history (per-user, per-document)

This gives you more **control and transparency** than typical "upload a file and chat" tools.

---

## ⚡ Why Grok Makes This App Special

Most document-Q&A apps use OpenAI, Anthropic, or Gemini. AI DocuSearch was originally built with **Grok** (xAI), but now supports **any OpenAI-compatible LLM endpoint**. 

### Grok-Specific Advantages
- Very fast responses
- Direct, less filtered outputs
- Strong reasoning on long documents
- Great for agent-like workflows
- Lower friction for experimentation

### Grok Challenges (Solved)
- ✅ Not natively integrated with LangChain → Fixed with custom wrappers
- ✅ Requires custom tracing → Implemented manual LangSmith Client tracing
- ✅ API schema differs → Abstracted via `LLM_API_BASE` and `LLM_MODEL` config
- ✅ No LangChain integration → Full custom RAG pipeline implemented

### Generic OpenAI-Compatible Support (NEW)
The project now works with **any provider** that supports `/chat/completions`:
- ✅ OpenAI (GPT-4, GPT-4o, etc.)
- ✅ xAI Grok
- ✅ Groq
- ✅ Together AI
- ✅ Custom self-hosted endpoints

**Configuration:** Set `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` in `.env` or Streamlit Secrets.

---

## 🎯 Who This App Is For

Perfect for:
- 📚 **Students** — Extract information quickly from research papers
- 💻 **Developers** — Build custom document-analysis workflows
- 🔬 **Researchers** — Analyze PDFs with AI assistance
- 🧪 **AI Enthusiasts** — Experiment with Grok or other LLMs in a real RAG pipeline
- 📊 **Business Users** — Analyze contracts, reports, and documents
- 🎓 **Learners** — Understand how LangSmith tracing and RAG pipelines work
- 🚀 **DevOps/MLOps** — Deploy AI tools with Streamlit

---

## 🧠 Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Language** | Python 3.10+ | Type hints required |
| **Web UI** | Streamlit 1.57+ | Responsive, full-page reruns |
| **Observability** | LangSmith | Manual Client tracing (manual because of Streamlit) |
| **Embeddings** | all-MiniLM-L6-v2 | Lazy-loaded, ~80 MB model |
| **Vector DB** | FAISS (CPU) | With NumPy and keyword-overlap fallbacks |
| **LLM** | OpenAI-compatible endpoint | Grok (xAI), GPT-4, or any compatible provider |
| **Document Processing** | PyPDF2, python-docx, pdf2image, Tesseract | Handles PDF, DOCX, TXT + OCR |
| **Deployment** | Streamlit Cloud | Auto-deploys from GitHub |

---

## 🚀 Live Demo

**Try the App:**  
🌐 https://ai-docusearch.streamlit.app/

Upload a PDF/DOCX and ask anything about it.

---

## 📊 Pricing & Usage Model

AI DocuSearch includes a **simple usage model** designed for experimentation while protecting API costs.

### Pricing Table

| Tier | Price | What You Get | Limits |
|------|-------|-------------|--------|
| **Free** | $0 | Upload & ask questions | • $0.50 Grok usage/session<br>• ~10–15 questions<br>• ~10–15 pages<br>• ~10k–15k tokens |
| **Developer** | $5/month | Personal projects & testing | • 150 questions/month<br>• 50-page docs<br>• Faster embeddings<br>• Priority API access |
| **Pro** | $15/month | Heavy users & researchers | • 500 questions/month<br>• 150-page docs<br>• Multi-doc search<br>• Agent-mode analysis |
| **Team/Business** | Custom | Teams & enterprises | • Unlimited questions<br>• 200+ page docs<br>• Shared workspace<br>• Audit logs<br>• API access |

### How the Free Tier Works

The free tier is limited to **$0.50 USD** of LLM (Grok) usage per session.

**Token Breakdown:**
- Average cost per question: $0.03–$0.05
- Free tier allows: ~10–15 questions
- 1 page ≈ 300–500 tokens
- 10 pages ≈ 3,000–5,000 tokens
- Embedding cost: ~$0.02–$0.05
- Free tier supports: ~10–15 pages total

**Total Token Budget:** ~10,000–15,000 tokens (extraction + chunking + embedding + retrieval + generation)

### When the Limit Is Reached

1. App stops answering questions
2. "Usage limit reached" message appears
3. User can restart session or upgrade

### Why These Limits Exist

✅ Predictable costs  
✅ Fair usage policy  
✅ Safe experimentation  
✅ No accidental credit drain  

---

## 🔐 Security & Privacy

AI DocuSearch is designed for **safe experimentation** and responsible handling of user-uploaded documents.

### 📄 Document Handling

- ✅ Uploaded PDFs/DOCX/TXT processed in **memory or temporary storage only**
- ✅ Documents are **NOT saved** to any database, cloud storage, or persistent disk
- ✅ All extracted text, embeddings, and intermediate data are **discarded when session ends**
- ⚠️ Avoid uploading highly confidential or regulated documents in this demo

### 🗑️ Automatic Deletion

- Temporary files removed immediately after processing
- Session data (chunks, embeddings, answers) cleared on refresh/close
- No long-term retention of documents or answers

### 🛡️ Logging & Metadata

- App does **NOT log document content**
- Minimal metadata logged for debugging:
  - File size
  - Page count
  - Number of chunks
- User questions and answers **NOT stored outside active session**

### 🔑 API Key Protection

- Grok/LLM and LangSmith API keys stored securely in `.streamlit/secrets.toml` (Cloud) or `.env` (local)
- Keys **never exposed** in frontend or repository
- Users running locally must provide their own keys

### 🔒 No User Accounts

- No authentication or user accounts
- All sessions anonymous and isolated
- Multi-user isolation enforced by Streamlit

### ⚠️ Important Note

This is an **experimental project** for learning and exploration, **not** a production-grade secure service. For sensitive/enterprise data, additional measures required:
- Encryption at rest & in transit
- Access control & authentication
- Secure storage & compliance (HIPAA, GDPR, etc.)
- Audit logging

---

## 📜 Terms of Use (Summary)

By using AI DocuSearch, you agree to:

1. ✅ Not upload highly sensitive, confidential, or regulated documents
2. ✅ Use responsibly within free-tier limits
3. ✅ Avoid automated scraping, bulk uploads, or abusive patterns
4. ✅ Understand this is **not a production-grade service** and may change anytime

**Disclaimer:** Offered as-is, without guarantees of accuracy, availability, or support.

---

## 🗄️ Data Retention Policy (Summary)

- ✅ Uploaded documents processed in memory or temp storage only
- ✅ **No** documents, text, embeddings, or answers stored permanently
- ✅ All temp data deleted automatically on session end
- ✅ No user accounts or personal identifiers collected
- ✅ Logs contain only minimal metadata
- ✅ Local deployments: **you control all retention**

---

## 🤖 Responsible AI Notice (Summary)

AI DocuSearch uses LLMs (Grok/GPT-4/etc.) to generate answers. Responses may:
- ⚠️ Contain mistakes or hallucinations
- ⚠️ Misinterpret ambiguous text
- ⚠️ Generate incomplete or approximate summaries
- ⚠️ Reflect model limitations

**Best Practices:**
- 🔍 Verify important information manually
- ❌ Do **NOT** use for legal, medical, or financial decisions
- ✅ Use for exploration, research, and learning

---

## 🔒 Security Roadmap (Future Enhancements)

Future improvements for stronger security and privacy:

1. 🔐 **Session-based encryption** for temporary document storage
2. 👤 **Optional user accounts** for document isolation
3. 📈 **Per-user usage dashboards** with real-time quota tracking
4. ⏰ **Configurable data-retention windows** (immediate delete, 24h, 7d, etc.)
5. 🔑 **Encrypted local storage** for self-hosted deployments
6. 📋 **Document-level access controls** for shared workspaces
7. 🗑️ **"Delete my data" button** for immediate cleanup
8. 📊 **Audit logs** for team or enterprise use
9. 🛡️ **Two-factor authentication** for Pro/Team accounts
10. 🔄 **Compliance certifications** (SOC 2, ISO 27001)

---

## 📈 Current Implementation Status

### ✅ Complete Features
- Document ingestion (PDF, DOCX, TXT + OCR)
- Preprocessing & chunking
- Embedding & indexing (FAISS + fallbacks)
- Semantic retrieval
- LLM query with OpenAI-compatible endpoints
- Streamlit UI with chat interface
- Persistent question history (hybrid storage)
- LangSmith manual tracing (implementation complete)
- Multi-mode execution (RAG, Direct LLM, Hybrid)
- Responsive mobile design

### ⚠️ In-Progress
- LangSmith outputs verification on Streamlit Cloud
- History sidebar UI (foundation complete, wiring pending)

### 🔄 Planned/Deferred
- History sidebar with clickable re-run
- Multi-document search
- Analytics dashboard
- Optional user accounts
- Enhanced security features (see roadmap)

See **IMPLEMENTATION_IMPROVEMENTS.md** for detailed sprint breakdown.

---

## 🎯 Suggested New Features & Improvements

Based on the current architecture, here are features that could enhance the app:

### **High-Impact Features** (Would Significantly Improve User Experience)

1. **📚 Multi-Document Analysis**
   - Upload multiple documents at once
   - Ask cross-document questions ("Compare Section 3.1 in Doc1 vs Section 2.4 in Doc2")
   - Support document relationships and references
   - **Effort:** Medium | **Impact:** High | **Priority:** 1

2. **💬 Real-Time Chat Suggestions**
   - Suggest follow-up questions based on document content
   - Auto-generate common questions for the document
   - "Smart questions" sidebar with one-click execution
   - **Effort:** Low | **Impact:** Medium | **Priority:** 2

3. **📊 Advanced Analytics Dashboard**
   - Track questions-per-session metrics
   - Word cloud of most-asked topics
   - Answer quality feedback (thumbs up/down)
   - Usage patterns and trends
   - **Effort:** Medium | **Impact:** Medium | **Priority:** 3

4. **🏷️ Document Tagging & Organization**
   - Tag documents by category, date, source
   - Save document sets for later
   - Organize by project/folder
   - **Effort:** Medium | **Impact:** Medium | **Priority:** 3

5. **📤 Export & Report Generation**
   - Export Q&A as PDF with source citations
   - Generate summaries as markdown/docx
   - Create audit trails for compliance
   - **Effort:** Medium | **Impact:** High | **Priority:** 2

### **Nice-to-Have Enhancements** (Polish & Convenience)

6. **🎨 Theme & Customization**
   - Dark mode toggle (partially done, could be enhanced)
   - Custom branding for team/business tier
   - Font size/readability adjustments
   - **Effort:** Low | **Impact:** Low

7. **⌨️ Keyboard Shortcuts**
   - Cmd/Ctrl+K to focus search
   - Cmd/Ctrl+Enter to submit
   - ↑/↓ to navigate history
   - **Effort:** Low | **Impact:** Low

8. **🔔 Smart Notifications**
   - Alert when hitting usage limits
   - Email summaries of insights
   - Scheduled document analysis
   - **Effort:** Medium | **Impact:** Low

9. **🌐 Internationalization (i18n)**
   - Support multiple languages
   - RTL language support
   - Regional compliance (GDPR, CCPA)
   - **Effort:** Medium | **Impact:** Medium (for global audience)

### **Advanced Features** (Requires Significant Engineering)

10. **🤖 Agent-Mode Analysis**
    - Multi-step reasoning across documents
    - Autonomous document summarization
    - Fact extraction and verification
    - **Effort:** High | **Impact:** High | **Priority:** 4

11. **🔄 Document Comparison Tools**
    - Side-by-side diff viewer
    - Highlight changes between versions
    - Track document evolution
    - **Effort:** High | **Impact:** Medium

12. **🎯 OCR Enhancements**
    - Image extraction from PDFs
    - Table detection and formatting
    - Layout preservation
    - **Effort:** High | **Impact:** Medium

13. **👥 Collaborative Workspace**
    - Share documents with team
    - Collaborate on annotations
    - Real-time simultaneous analysis
    - **Effort:** Very High | **Impact:** High

14. **🔍 Advanced Retrieval**
    - Hybrid search (semantic + keyword)
    - Reranking with cross-encoders
    - Query expansion
    - **Effort:** Medium | **Impact:** High

15. **📱 Mobile Native App**
    - iOS/Android apps
    - Offline document access
    - Camera-based document upload
    - **Effort:** Very High | **Impact:** Medium

---

## 🛠️ How to Get Started

### **Local Development**

```bash
# Clone repo
git clone https://github.com/lazar87andreea-glitch/AI-DocuSearch
cd AI-DocuSearch

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys:
# - LLM_API_KEY (Grok or OpenAI)
# - LLM_API_BASE
# - LLM_MODEL
# - LANGSMITH_TRACING=true
# - LANGSMITH_API_KEY
# - LANGSMITH_PROJECT (optional)

# Run app
streamlit run web_app.py
```

### **Streamlit Cloud Deployment**

```bash
# 1. Push code to GitHub
git add .
git commit -m "Deploy to Streamlit Cloud"
git push origin main

# 2. Go to https://share.streamlit.io/
# 3. Click "New app"
# 4. Select repo, branch, and web_app.py
# 5. Add secrets (Settings > Secrets):
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LLM_API_KEY=...
LLM_API_BASE=...
LLM_MODEL=...

# App auto-redeploys on push
```

---

## 📚 Documentation

- **MASTER_GUIDE.md** — Project overview & architecture
- **STEP_1_INGEST.md** — Document ingestion details
- **STEP_2_PREPROCESS.md** — Text cleaning & chunking
- **STEP_3_EMBEDDING_INDEXING.md** — Embeddings & FAISS
- **STEP_4_AI_QUERY.md** — LLM integration & LangSmith tracing
- **STEP_5_PIPELINE.md** — End-to-end orchestration
- **STEP_6_HISTORY_TRACKING.md** — Persistent history implementation
- **IMPLEMENTATION_IMPROVEMENTS.md** — Sprint roadmap & known issues
- **PROJECT_OVERVIEW.md** — This file (high-level overview + feature ideas)

---

## 📞 Support & Feedback

- 🐛 **Issues:** https://github.com/lazar87andreea-glitch/AI-DocuSearch/issues
- 💬 **Discussions:** https://github.com/lazar87andreea-glitch/AI-DocuSearch/discussions
- 📧 **Contact:** Andreea Nistor

---

## 📄 License

[Specify your license here — MIT, Apache 2.0, GPL, etc.]

---

## 🙏 Acknowledgments

- Streamlit team for the fantastic UI framework
- LangSmith for observability platform
- xAI Grok for fast LLM inference
- Open-source community (PyPDF2, python-docx, FAISS, etc.)

---

**Last Updated:** 2026-08-20  
**Status:** 85% Complete — Production-ready core, observability & UI enhancements in progress
