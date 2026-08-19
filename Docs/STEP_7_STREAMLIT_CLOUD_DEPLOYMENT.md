# AI DocuSearch — Step 7: Streamlit Cloud Deployment

## Overview

This guide covers deploying AI DocuSearch to [Streamlit Cloud](https://streamlit.io/cloud) for browser-based access. The app works on desktop, tablet, and mobile browsers, with automatic optimization for each device type.

## Prerequisites

- GitHub repository with AI DocuSearch code pushed
- Streamlit Cloud account (free tier available)
- API keys for:
  - LLM provider (OpenAI, Grok, Groq, etc.) — via `OPENAI_API_KEY` or `LLM_API_KEY`
  - LangSmith (optional) — via `LANGSMITH_API_KEY`

## Step 1: Prepare Repository for Deployment

Ensure your GitHub repository contains:

### Required Files

1. **requirements.txt** — Python dependencies
   ```
   pypdf
   python-docx
   sentence-transformers
   faiss-cpu
   numpy
   requests
   streamlit
   python-dotenv
   langsmith
   pdf2image
   pytesseract
   pillow
   ```

2. **packages.txt** — System dependencies for OCR support
   ```
   tesseract-ocr
   poppler-utils
   libtesseract-dev
   ```

3. **.env.example** — Template for environment variables (NO actual keys!)
   ```env
   OPENAI_API_KEY=sk-...
   LLM_API_BASE=https://api.openai.com/v1
   LLM_MODEL=gpt-4
   LANGSMITH_API_KEY=lsv2_pt_...
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=ai-docusearch
   ```

4. **web_app.py** — Main Streamlit application

5. **.gitignore** — Should exclude `.env` and `__pycache__/`

### Important

- ✅ Commit all code to GitHub
- ✅ DO NOT commit `.env` with real API keys
- ❌ Never hardcode secrets in code

## Step 2: Deploy to Streamlit Cloud

### 2.1: Go to Streamlit Cloud

1. Visit [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"

### 2.2: Configure App

1. **Repository:** Select your GitHub repo containing AI DocuSearch
2. **Branch:** Select `main` (or your working branch)
3. **Main file path:** Enter `web_app.py`
4. Click **"Deploy"**

**Status:** The app will build and deploy (this may take 2-5 minutes for first deployment)

## Step 3: Configure Secrets

### 3.1: Access Settings

1. Once the app loads, click **≡** (hamburger menu) in top right
2. Click **Settings**
3. Click **"Secrets"** tab

### 3.2: Add API Keys

Paste your secrets in the text box (one per line, format: `KEY = "value"`):

```toml
# Required: LLM API key (choose one)
OPENAI_API_KEY = "sk-proj-..."
# OR for xAI/Grok:
# LLM_API_KEY = "grok-api-key-here"
# LLM_API_BASE = "https://api.x.ai/v1"
# LLM_MODEL = "grok-4"

# Optional: LangSmith tracing (for observability)
LANGSMITH_API_KEY = "lsv2_pt_..."
LANGSMITH_TRACING = "true"
LANGSMITH_PROJECT = "ai-docusearch"

# Optional: Question history tracking (Step 6)
HISTORY_ENABLED = "true"
HISTORY_RETENTION_DAYS = "30"
HISTORY_LIMIT = "10"
```

### 3.3: Save & Rerun

1. Click **"Save"**
2. App will automatically rerun with new secrets
3. You should see the app reload in the browser

## Step 4: Verify Deployment

### 4.1: Test Upload & Query

1. **Upload a document**
   - Click "Upload a PDF, DOCX or TXT file"
   - Select a test document
   - Wait for extraction (green ✅ message)

2. **Chat with the document**
   - Select a mode: **Direct LLM** (fastest, all devices), **RAG** (most accurate, desktop only), or **Hybrid** (tries RAG, falls back to Direct LLM)
   - Type your question in the chat input box
   - Press Enter or click the input box to submit
   - Answer appears in the conversation thread below

3. **View conversation history**
   - Previous questions and answers appear above the chat input
   - Click "📊 Metrics" on any response to see performance details (response time, tokens, etc.)
   - History persists for the current browser session

### 4.2: Test LangSmith Integration (Optional)

Run `test_langsmith.py` locally to verify credentials:

```bash
python test_langsmith.py
```

Then in the deployed app, ask a question. Check your [LangSmith dashboard](https://smith.langchain.com) for traces.

## Step 5: Features & Capabilities

### Document Formats

| Format | Speed | Quality | Notes |
|--------|-------|---------|-------|
| Searchable PDF | Fast ✓ | High | Standard digital PDFs |
| Scanned PDF | Slow (30-60s) | Medium | Uses OCR; works with Romanian text |
| DOCX | Fast ✓ | High | Includes tables |
| TXT | Very fast ✓ | High | Plain text files |

### Device Support

- **Desktop browsers** (Chrome, Firefox, Safari, Edge)
  - ✅ Chat interface with all three modes (RAG, Direct LLM, Hybrid)
  - ✅ Conversation history with timestamps
  - ✅ Expandable metrics for each response
  - ✅ Wide layout for readability

- **Mobile browsers** (Android, iOS)
  - ✅ Same chat interface as desktop
  - ✅ Direct LLM mode (recommended for mobile performance)
  - ℹ️ RAG/Hybrid modes available but not recommended (uses more resources)
  - ✅ Touch-friendly chat input
  - ✅ Responsive vertical layout

### Performance Notes

- **First app load:** 10-30 seconds (Streamlit Cloud cold start)
- **Document extraction:**
  - Searchable PDF: 1-5 seconds
  - Scanned PDF: 30-120 seconds
  - DOCX: 1-3 seconds
- **Query generation:**
  - Direct LLM: 10-30 seconds
  - RAG mode: 30-60 seconds (includes embedding)
  - Hybrid: depends on which mode succeeds

## Step 6: Troubleshooting

### App Won't Start

**Symptom:** "App is loading..." but never finishes

**Solutions:**
1. Check Streamlit Cloud logs (click **≡** → **Manage app** → view **Logs**)
2. Look for Python errors or missing packages
3. Verify `requirements.txt` has all dependencies
4. Try deploying a fresh branch

### Document Upload Fails

**Symptom:** "Failed to extract text" error

**Solutions:**
1. Verify file format (PDF, DOCX, TXT only)
2. Check file isn't corrupted (try local test: `python demo.py document.pdf "test question"`)
3. For scanned PDFs, verify `packages.txt` has Tesseract/Poppler
4. Check Streamlit Cloud logs for specific error

### Button Click Does Nothing

**Symptom:** Click "Run Direct LLM" but no response

**Solutions:**
1. Verify `OPENAI_API_KEY` is set in Secrets
2. Check API key is valid (test locally first)
3. Check Streamlit Cloud logs for errors
4. Try smaller test document first
5. Verify internet connectivity

### LangSmith Traces Not Appearing

**Symptom:** App works but no traces in LangSmith dashboard

**Solutions:**
1. Verify `LANGSMITH_API_KEY` set in Secrets (not `.env`)
2. Verify `LANGSMITH_TRACING = "true"` in Secrets
3. Run `test_langsmith.py` locally to verify credentials
4. Check LangSmith dashboard at https://smith.langchain.com
5. Ensure project name matches `LANGSMITH_PROJECT`

## Step 7: Customization

### Change App Description

Edit `web_app.py` line ~62:

```python
st.markdown(
    "Your custom description here"
)
```

Push to GitHub; app will redeploy automatically.

### Adjust LLM Temperature

Edit `prompts/direct_llm_prompt.txt` or `prompts/rag_prompt.txt`:

```
# temperature: 0.5
```

Change value to 0.1-1.0; push to GitHub.

### Hide Metrics by Default

Edit `web_app.py` in `render_result()` function:

```python
show_flag = f"show_metrics_{mode_key}"
if show_flag not in st.session_state:
    st.session_state[show_flag] = True  # Change to True to show by default
```

## Step 8: Monitor & Maintain

### Regular Checks

- Monitor API usage in provider dashboard (OpenAI, Grok, etc.)
- Check Streamlit Cloud logs monthly for errors
- Verify LangSmith traces if enabled

### Updates

1. Make changes locally
2. Commit and push to GitHub
3. Streamlit Cloud auto-redeploys (usually within 1 minute)

### Rerun App Manually

Go to **≡** → **Manage app** → click **Rerun** if needed

## Next Steps

- Share your app URL with users
- Collect feedback on document formats and languages
- Monitor costs with your LLM provider
- Consider Streamlit Cloud Pro tier if high usage

---

## Additional Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-cloud)
- [LangSmith Dashboard](https://smith.langchain.com)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Tesseract OCR Documentation](https://github.com/UB-Mannheim/tesseract/wiki)
