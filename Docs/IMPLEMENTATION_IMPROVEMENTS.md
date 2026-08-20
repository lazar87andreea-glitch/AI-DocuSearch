# AI DocuSearch — Implementation Improvements & Gap Analysis

**Last Updated:** 2026-08-20 (Updated after documentation sync)  
**Status:** Multi-phase implementation plan based on doc specs vs. current build

---

## Executive Summary

The current implementation has completed **~85%** of the planned features (↑ from 70%). The core RAG pipeline, document ingestion, Streamlit UI, and **persistent history tracking** are production-ready. LangSmith manual tracing is implemented but outputs not yet confirmed on Cloud. Optional features (history sidebar UI) deferred to Sprint 2. This document outlines priorities across **4 sprints**.

---

## Recent Updates (2026-08-20)

✅ **Documentation Sync Complete** — All MD files updated to reflect actual implementation:
- STEP_6_HISTORY_TRACKING.md: Marked ✅ FULLY IMPLEMENTED with actual code, hybrid storage architecture, performance notes
- STEP_4_AI_QUERY.md: Added Section 4.5 documenting LangSmith manual Client tracing implementation
- MASTER_GUIDE.md: Added feature status table (✅/⚠️ indicators), accomplishments, roadmap
- This file (IMPLEMENTATION_IMPROVEMENTS.md): Updated sprint statuses and known issues to match actual progress

📈 **Key Status Changes:**
- Step 4 (AI Query): ⚠️ 90% → ✅ 90% (manual tracing implemented, pending Cloud verification)
- Step 6 (History): ⚠️ 85% → ✅ 95% (hybrid storage fully working)
- Overall: 70% → 85% (20% progress from initial implementation)

---

## Current Status vs. Plan

### ✅ Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| **Step 1: Document Ingestion** | ✅ Complete | PDF, DOCX, TXT extraction with OCR fallback working |
| **Step 2: Preprocessing** | ✅ Complete | Text cleaning, chunking with overlap |
| **Step 3: Embedding & Indexing** | ✅ Complete | FAISS + NumPy fallback, lazy model loading, memory guards |
| **Step 4: AI Query** | ✅ 90% | Manual LangSmith Client tracing implemented; outputs capturing logic added (testing on Cloud pending) |
| **Step 5: Pipeline Orchestration** | ✅ Complete | End-to-end flow, lite mode fallback, memory handling |
| **Streamlit UI — Chat Interface** | ✅ Complete | Mode selector, chat bubbles, responsive mobile layout |
| **Streamlit UI — Metrics Display** | ✅ Removed | User preference; metrics hidden from default view |
| **Step 6: History Tracking** | ✅ 95% | Hybrid storage (in-memory + disk) fully working; sidebar UI **not implemented** (deferred) |
| **Step 7: Cloud Deployment** | ⚠️ 80% | App deploys; secrets loading partially hardened; full testing pending |

### 🔴 Known Issues

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| **LangSmith outputs verification** | 🔴 HIGH | Manual tracing implemented; needs Cloud verification that end_run(outputs=...) captures data | Ready for testing (diagnostics deployed in commit 65d66c1) |
| **Secrets loading on Streamlit Cloud** | 🟡 MEDIUM | Partially hardened; still needs edge case testing (missing secrets, partial configs) | Improved (dual fallback in commit 65d66c1) |
| **History sidebar UI not wired** | 🟡 MEDIUM | Users can't click history items to re-run; feature incomplete but foundation complete | Deferred to Sprint 2 |
| **Follow-up questions on Cloud** | 🟡 MEDIUM | Works locally; untested on Streamlit Cloud with persistent browser session | Ready for Sprint 2.2 testing |
| **inotify watch limit error** | 🟡 LOW | Streamlit Cloud infra issue; non-blocking but noisy in logs | Accepted (out of scope) |

---

## Sprint Breakdown

### Sprint 1: LangSmith Observability Fix (IMPLEMENTATION COMPLETE — Testing Phase)
**Duration:** 1-2 days  
**Goal:** Verify LangSmith traces with outputs appear in dashboard on Streamlit Cloud  
**Status:** Manual Client tracing fully implemented (commit 65d66c1+); code review complete; ready for Cloud verification

**What's Done:**
- ✅ Manual Client.create_run() / end_run() pattern implemented
- ✅ Variables initialized at function start (scope fixed)
- ✅ Outputs dict structured with answer, tokens, timing
- ✅ Error handling: error parameter when API fails
- ✅ Comprehensive debug logging for troubleshooting
- ✅ Documentation complete (STEP_4_AI_QUERY.md Section 4.5)
- ✅ Deployed to GitHub and Streamlit Cloud (commit e573b04)

**What Remains:** Verify this works on Cloud (the issue was "create_run returns None" — now diagnostics will show if that's fixed)

#### 1.1 Deploy & Monitor Streamlit Cloud Logs
- **Action:** Latest code deployed (commit e573b04)
- **Check Logs For (exact strings):**
  - `[LANGSMITH_ENV] API_KEY present: True` ✅
  - `[LANGSMITH_ENV] TRACING: 'true'` ✅ (must be lowercase string, not 'True')
  - `[LANGSMITH] Client initialized successfully` ✅
  - `[LANGSMITH] Run created with ID: <uuid>` ✅ (NOT "created with ID: None")
  - `[LANGSMITH] Ending run with outputs: {...}` ✅
  
- **Expected Result:** All logs appear + LangSmith dashboard shows runs with inputs & outputs ✅

#### 1.2 If Logs Show "create_run returned: None"
This means `LANGSMITH_TRACING` environment variable not set correctly to string `'true'`. Check:
- [ ] Streamlit Cloud Secrets > Set `LANGSMITH_TRACING=true` (lowercase, NOT "True")
- [ ] Set `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`
- [ ] Redeploy and check logs again

#### 1.3 If Outputs Still Don't Appear in Dashboard
If logs show successful end_run() but dashboard shows no outputs:
- [ ] Check LangSmith SDK version in requirements.txt (should be langsmith>=0.1.0)
- [ ] Test locally with minimal script (see requirements below)
- [ ] Check if end_run() parameter name is still `outputs=` (verify against langsmith docs)

**Minimal Test Script:**
```bash
pip install langsmith
python -c "
from langsmith import Client
import os
os.environ['LANGSMITH_API_KEY'] = 'your_key'
os.environ['LANGSMITH_TRACING'] = 'true'
client = Client()
run = client.create_run(name='test', run_type='llm', inputs={'q': 'test?'})
if run: print(f'Run ID: {run.id}')
else: print('ERROR: create_run returned None')
# Check dashboard for run
"
```

**If Resolved:** ✅ Proceed to Sprint 2.2 to test follow-up questions on Cloud

#### 1.4 Contingency: Disable LangSmith if Unresolvable (30+ min debugging)
**Only if** debugging takes >1.5 hours and blocking progress:
- Add default `LANGSMITH_TRACING=false` to web_app.py
- Document limitation
- Keep error handling intact for future fix
- Proceed to Sprint 2

---

### Sprint 2: History Sidebar UI & Follow-Up Testing
**Duration:** 2-3 days  
**Goal:** Complete history tracking feature and test follow-up questions  
**Dependency:** Sprint 1 can be in-progress (not blocking)

#### 2.1 Implement History Sidebar Display
**File:** `web_app.py`  
**Status:** Foundation fully complete; only UI wiring remains

**Current State:**
- ✅ HistoryManager class complete (in `src/history_manager.py`)
- ✅ Questions logged to disk (in `log_to_history()`)
- ✅ Session state cache working (in `st.session_state.chat_history`)
- ✅ Chat history displayed in main area (in `render_chat_history()`)
- ⚠️ Sidebar display NOT wired yet (this is the missing piece)

**What to Add:** Copy the `render_history_sidebar()` function (documented in STEP_6_HISTORY_TRACKING.md lines ~463-480) into web_app.py and call it before the main chat input (around line ~560)
```python
def render_history_sidebar(history_manager, current_doc):
    """Show clickable list of recent questions for current document"""
    if not current_doc:
        st.sidebar.info("📋 No document loaded yet")
        return
    
    st.sidebar.markdown("### 📋 Session History")
    recent = history_manager.get_recent_questions(
        document_name=current_doc,
        limit=10
    )
    
    if not recent:
        st.sidebar.info("No history for this document")
        return
    
    for entry in recent:
        timestamp = entry["timestamp"][:19]
        mode = entry["mode"]
        question = entry["question"][:40] + "..." if len(entry["question"]) > 40 else entry["question"]
        
        if st.sidebar.button(f"[{mode}] {timestamp}\n{question}", key=f"hist_{entry['timestamp']}"):
            # Re-run this question
            st.session_state.chat_input = entry["question"]
            st.session_state.rerun_mode = mode
            st.rerun()
```

**Integration Points:**
- Call before main chat input (line ~560 in web_app.py)
- Use same `st.session_state.history_manager` initialized earlier
- Pass current document name from `st.session_state.get("uploaded_name")`

**Acceptance Criteria:**
- [ ] Sidebar shows last 5-10 questions for current document
- [ ] Clicking a question populates the chat input
- [ ] Clicking re-runs that mode automatically
- [ ] History updates in real-time as new questions are asked
- [ ] Sidebar empty when no document uploaded

#### 2.2 Test Follow-Up Questions on Streamlit Cloud
**Scenario:** User asks Q1, then Q2 (follow-up), then switches documents, then re-opens doc → should see both Q1 & Q2

**Test Script:**
1. Deploy latest main branch to Streamlit Cloud
2. Upload `sample.pdf` (or any document)
3. Ask Q1: "What is this document about?"
4. Wait for answer
5. Ask Q2: "Can you summarize that?"
6. Check chat history shows both Q1 and answer, then Q2 and answer in order
7. Check sidebar shows both questions for this document
8. Upload different document
9. Ask Q3 for new document
10. Switch back to sample.pdf → should show Q1 & Q2, NOT Q3
11. Verify `history/user_{session_id}.json` file contains entries with correct document_name

**Expected Result:** Chat shows persistent history with document filtering working

**If Fails:**
- Check logs for `[INIT]` messages about history loading
- Verify `load_existing_history` call succeeds in document upload handler
- Check JSON file format in `history/` folder

#### 2.3 CLI History Tool Testing
**Current State:** `history_cli.py` exists with list/show/export/cleanup commands

**Test Each Command:**
```bash
# List all sessions' history
python history_cli.py list

# Show questions for specific session
python history_cli.py show <session_id>

# Export to CSV
python history_cli.py export <session_id> --format csv --output out.csv

# Cleanup old sessions
python history_cli.py cleanup --older-than 30
```

**Acceptance Criteria:**
- [ ] `list` shows all session files
- [ ] `show <session_id>` displays formatted table
- [ ] `export` creates CSV with proper headers
- [ ] `cleanup` removes files with mtime > threshold

**If Any Fails:** Fix bugs in history_cli.py

---

### Sprint 3: Deployment Hardening & Edge Case Fixes
**Duration:** 2-3 days  
**Goal:** Make app robust for production use  
**Dependency:** Sprints 1-2 should be mostly done

#### 3.1 Secrets Loading Robustness
**Current State:** web_app.py has retry logic for st.secrets.items() and .get()

**What to Verify:**
- [ ] Test on Streamlit Cloud with LANGSMITH secrets set
- [ ] Test with LANGSMITH secrets NOT set (should gracefully degrade)
- [ ] Test with partial secrets (only API_KEY, missing PROJECT, etc.)
- [ ] Verify logs show exactly which secrets were loaded

**Edge Cases to Handle:**
```python
# Case 1: st.secrets is None
if hasattr(st, 'secrets') and st.secrets:
    # Current code handles this ✅

# Case 2: st.secrets.items() not available (different Streamlit version)
# Current code has try/except with fallback ✅

# Case 3: st.secrets get() returns None
# Current code handles with "or" chain ✅

# Case 4: st.secrets exists but is empty dict
# Verify: should not crash, should log "st.secrets available but empty"
```

**Test On Streamlit Cloud:**
- Delete all secrets → should log warnings but app still runs with simulated LLM
- Add only LLM_API_KEY → should work for queries, skip LangSmith
- Add all LangSmith secrets → should trace to dashboard

#### 3.2 Error Handling for Large Documents
**Scenario:** User uploads 100+ MB PDF

**What Could Break:**
- OCR on very large PDF (memory spike)
- Embedding model running out of memory
- Streamlit timeout during processing

**What Should Happen:**
- PDF extraction: Warn if > 50 MB but continue
- Chunking: Auto-reduce chunk size if too many chunks
- Embedding: Lite mode fallback if memory < 2 GB
- UI: Show progress messages during long operations

**Verification:**
- [ ] Code has check for extracted text > 50 MB (stderr warning)
- [ ] EmbedIndex has `self.disabled` flag on MemoryError
- [ ] build_pipeline() checks available memory before embedding
- [ ] web_app.py shows st.info/warning during upload/processing

**If Missing:** Add memory guards and progress feedback

#### 3.3 Document Format Edge Cases
**Test Each Format:**
- [ ] Encrypted PDF → should gracefully fail with clear message
- [ ] PDF with no extractable text → should auto-fallback to OCR
- [ ] DOCX with embedded images (no text) → should extract any text present
- [ ] Very long TXT file (1000+ pages) → should chunk properly
- [ ] Binary file with wrong extension → should fail gracefully
- [ ] Zero-byte file → should fail gracefully

**Test Commands:**
```bash
# Local testing
python -c "
from src.ingest import extract_text
try:
    text = extract_text('test.pdf')
    print(f'Extracted {len(text)} chars')
except Exception as e:
    print(f'Error: {e}')
"
```

#### 3.4 Chat Input Edge Cases
**Test in Web UI:**
- [ ] Submit empty question → should show error
- [ ] Submit very long question (2000+ chars) → should handle gracefully
- [ ] Special characters in question (emoji, Unicode) → should work
- [ ] Rapid repeated submissions → should queue/handle concurrency
- [ ] Switch modes mid-question → should not break state
- [ ] Refresh browser mid-answer → should gracefully interrupt

**Acceptance Criteria:** App doesn't crash or show confusing errors

---

### Sprint 4: Feature Enhancements & Documentation
**Duration:** 3-4 days  
**Goal:** Polish and expand capabilities  
**Dependency:** Sprints 1-3 complete

#### 4.1 Enhanced Analytics Dashboard (Optional)
**Idea:** In-app dashboard showing aggregated stats from history

**What to Show:**
- Total questions asked (this session)
- Modes used (pie chart: RAG vs Direct LLM vs Hybrid)
- Average tokens per question
- Fastest / slowest queries
- Documents processed

**Implementation:**
- Add new page in Streamlit multi-page app: `pages/analytics.py`
- Read all history entries from current session
- Aggregate and display via st.metric / st.bar_chart

**Acceptance:** Analytics page shows reasonable stats

#### 4.2 Export Conversation as PDF
**Idea:** Let users download chat history as formatted PDF

**Implementation:**
- Use `reportlab` or `pypdf` to generate PDF
- Include question, answer, mode, timestamp for each entry
- Add `st.download_button()` to trigger download

**Acceptance:** Click button → PDF downloads with formatted conversation

#### 4.3 Multi-Document Search
**Idea:** Search across multiple uploaded documents in one session

**Current Behavior:** Upload doc A, ask Q1, then upload doc B, ask Q2 (isolated per doc)

**Enhanced Behavior:**
- After uploading doc B, have option to "Search all uploaded documents"
- Retrieval searches across all loaded chunks
- Answer includes document source for each chunk

**Implementation:**
- Track all uploaded documents in `st.session_state.all_documents`
- Merge chunks with document labels: `{text: "...", source: "doc_name"}`
- Display source doc in results

**Acceptance:** Can search across 2+ documents; results show which doc each chunk came from

#### 4.4 Question Templates / Examples
**Idea:** Suggest common questions to new users

**Implementation:**
- In sidebar, show example questions below history
- Template questions: "Summarize this document", "What are the key points?", "List dates mentioned"
- Click to populate chat input

**Acceptance:** Example questions appear and are clickable

#### 4.5 Update Documentation
**Files to Update:**
- [ ] README.md: Add quick-start video link (if available)
- [ ] MASTER_GUIDE.md: Update status of all features (what's done, what's not)
- [ ] New file: TROUBLESHOOTING.md with common issues & solutions
- [ ] New file: ARCHITECTURE.md with system design diagrams (Mermaid)
- [ ] Add comments in code for complex logic

**Acceptance:** All guides are current and helpful for new developers

#### 4.6 Unit Tests & Integration Tests
**Current State:** test_ingest.py and test_langsmith.py exist

**Add:**
- [ ] Unit tests for preprocess.py (chunking, cleaning)
- [ ] Unit tests for embed_index.py (search, fallback)
- [ ] Unit tests for pipeline.py (lite mode trigger)
- [ ] Integration test: full end-to-end flow
- [ ] E2E test: Streamlit UI with uploaded document

**Tool:** pytest with fixtures

**Acceptance:** `pytest` runs all tests; 90%+ pass rate

#### 4.7 Performance Optimization
**Profile & Optimize:**
- [ ] Which step is slowest? (use Python profiler)
- [ ] Can embedding model be quantized for faster inference?
- [ ] Can FAISS index use GPU if available?
- [ ] Can chunks be pre-computed and cached?

**Benchmarks to Track:**
- Time to upload document
- Time to first answer (by mode)
- Memory usage during embedding

**Acceptance:** Document baseline metrics; identify 1-2 quick wins

---

## Implementation Order (Recommended)

### Week 1 (Immediate)
1. **Sprint 1.1-1.3:** Resolve LangSmith outputs (1-2 days)
   - Tests on Streamlit Cloud
   - Determine root cause
   - Apply fix or document workaround

2. **Sprint 2.1:** Implement history sidebar (0.5-1 day)
   - Add render_history_sidebar() function
   - Wire into web_app.py
   - Local testing

### Week 2
3. **Sprint 2.2:** Test follow-up questions end-to-end (1 day)
   - Deploy to Streamlit Cloud
   - Manual testing on live app
   - Verify document filtering

4. **Sprint 3.1-3.2:** Hardening (1.5 days)
   - Secrets loading verification
   - Large document handling
   - Progress UI improvements

### Week 3
5. **Sprint 3.3-3.4:** Edge case testing (1 day)
   - Format edge cases
   - Chat input edge cases
   - Bug fixes as needed

6. **Sprint 4.5:** Documentation updates (0.5 day)
   - Update guides
   - Add troubleshooting
   - Code comments

### Week 4+ (Optional Enhancements)
7. **Sprint 4.1-4.4:** Feature additions
   - Analytics dashboard
   - PDF export
   - Multi-doc search
   - Question templates
   - Performance optimization

---

## Success Criteria (MVP)

By end of Sprint 3, the app should be:

- ✅ **Stable:** No crashes on edge cases
- ✅ **Traceable:** LangSmith showing outputs in dashboard
- ✅ **Persistent:** History working end-to-end
- ✅ **Usable:** Sidebar history clickable
- ✅ **Documented:** README and guides up-to-date
- ✅ **Tested:** Core flows verified on Streamlit Cloud

---

## Open Questions

1. **LangSmith Output Capture:** What's the root cause? (to be determined in Sprint 1)
2. **Feature Priority:** Are analytics/PDF export valuable enough to spend time on? (user feedback needed)
3. **Performance:** Any bottlenecks identified in profiling? (to be determined in Sprint 4.7)
4. **Scale:** How many concurrent users? Max document size? (determines optimization priority)

---

## Risk Log

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| LangSmith fix takes >2 days | Medium | Delays public launch | Start parallel work on Sprint 2 |
| Streamlit Cloud has breaking changes | Low | Major rework needed | Pin Streamlit version in requirements.txt |
| Memory issues with large PDFs | Medium | Crashes on OCR | Pre-test with 100+ MB files; add guardrails |
| History sidebar conflicts with state | Medium | Chat breaks on rerun | Careful testing with st.session_state |

---

## Appendix: File Checklist

### Core Implementation Files
- [x] `src/ingest.py` — Document extraction
- [x] `src/preprocess.py` — Text cleaning & chunking
- [x] `src/embed_index.py` — Embeddings & search
- [x] `src/ai_query.py` — LLM query + **LangSmith tracing (NEEDS FIX)**
- [x] `src/pipeline.py` — Orchestration
- [x] `src/history_manager.py` — History tracking
- [ ] `src/history_cli.py` — CLI tool (exists, needs testing)
- [x] `web_app.py` — Streamlit app + **sidebar UI (NEEDS COMPLETION)**

### Config & Prompts
- [x] `requirements.txt`
- [x] `packages.txt` (for Streamlit Cloud)
- [x] `.env.example`
- [x] `prompts/rag_prompt.txt`
- [x] `prompts/direct_llm_prompt.txt`
- [x] `.gitignore`

### Documentation
- [x] `README.md` (outdated, needs refresh)
- [x] `Docs/MASTER_GUIDE.md`
- [x] `Docs/STEP_*.md` (all steps documented)
- [ ] `Docs/TROUBLESHOOTING.md` (missing)
- [ ] `Docs/ARCHITECTURE.md` (missing)

### Testing
- [x] `test_ingest.py`
- [ ] `test_preprocess.py` (missing)
- [ ] `test_embed_index.py` (missing)
- [ ] `test_pipeline.py` (missing)
- [x] `test_langsmith.py`

---

**Next Action:** Start Sprint 1.1 — Deploy and monitor Streamlit Cloud logs after latest commit.
