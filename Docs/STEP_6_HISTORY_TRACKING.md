# Step 6: Question History Tracking & Multi-User Isolation

## Overview
Implement persistent per-user question history with document filtering, session isolation, and multi-user support. Each browser session maintains its own private history file, with automatic cleanup and a CLI tool for analytics. Complete metrics (tokens, timing, retrieval performance) are stored internally for each question for future analytics capability.

## Purpose
- Track all user questions and answers for a session
- Store complete metrics (tokens, timing, retrieval performance)
- Enable quick re-running of past questions
- Maintain multi-user isolation (each browser session is private)
- Provide analytics/audit capability via CLI tool
- Filter history by document for clarity within a session

## Key Concepts

### Session Isolation
- Each browser session = isolated "user" (Streamlit enforces this natively)
- Separate history files: `history/user_{session_id}.json`
- One user cannot see another user's history or documents
- Browser close/refresh = new session (new history file)

### Document Filtering
- Within a single session, questions accumulate across all documents
- But sidebar shows only questions for the current document
- All data is preserved; filtering is UI-level only
- When switching documents in same session, sidebar automatically re-filters

### Multi-User Behavior
- Concurrent users: separate `st.session_state`, separate history files
- No cleanup contention: each session's cleanup doesn't affect others
- No cross-user data leakage: Streamlit's isolation is enforced
- Temp files scoped to each session; auto-cleaned on session end

---

## Detailed Implementation Steps

### Step 6.1: Create `src/history_manager.py`
**Purpose:** Core history management with session awareness

**Class: `HistoryManager`**

```python
class HistoryManager:
    def __init__(self, session_id: str):
        """Initialize with unique session ID"""
        self.session_id = session_id
        self.history_dir = "history"
        self.history_file = os.path.join(self.history_dir, f"user_{session_id}.json")
        
    def add_question(self, question: str, answer: str, mode: str, 
                     metrics_dict: dict, document_name: str) -> None:
        """Log a question+answer pair with full metrics"""
        # Append entry to session's JSON file
        
    def load_session_history(self) -> list:
        """Load all history entries for this session from JSON"""
        # Read and return entire history array
        
    def get_recent_questions(self, document_name: str | None = None, 
                            limit: int = 10) -> list:
        """Get last N questions, optionally filtered by document"""
        # Load history, filter by document_name if provided, return recent N
        
    @staticmethod
    def cleanup_old_sessions(retention_days: int = 30) -> None:
        """Delete session files older than retention_days"""
        # Scan history/ folder, remove files with mtime > retention_days
```

**File location:** `src/history_manager.py`

**Data format:** `history/user_{session_id}.json`
```json
[
  {
    "timestamp": "2025-08-18T10:30:45.123456",
    "question": "What are contract dates?",
    "answer": "The contract runs from January 1...",
    "mode": "RAG",
    "document_name": "contract.pdf",
    "metrics": {
      "total_seconds": 2.5,
      "retrieval_seconds": 1.2,
      "generation_seconds": 1.3,
      "chunk_count": 3,
      "prompt_tokens": 450,
      "completion_tokens": 120,
      "total_tokens": 570,
      "temperature": 0.2
    }
  }
]
```

**Key methods:**
- `add_question()` — Appends new entry to session's JSON file with ISO 8601 timestamp
- `load_session_history()` — Reads entire JSON file into memory
- `get_recent_questions(document_name)` — Filters by document, returns sorted by timestamp (newest first)
- `cleanup_old_sessions()` — Static method; scans `history/` folder for files with mtime > 30 days, deletes them

---

### Step 6.2: Integrate into `web_app.py`
**Purpose:** Wire history tracking into the app lifecycle

**Changes:**

1. **Initialize `HistoryManager` at app startup:**
   ```python
   if "history_manager" not in st.session_state:
       session_id = str(st.session_state.get("id", hash(time.time())))
       st.session_state.history_manager = HistoryManager(session_id)
   ```

2. **Call cleanup on app startup:**
   ```python
   # At the top of web_app.py, after imports
   if not os.path.exists("history"):
       os.makedirs("history")
   HistoryManager.cleanup_old_sessions(
       retention_days=int(os.getenv("HISTORY_RETENTION_DAYS", "30"))
   )
   ```

3. **After each mode completes, log the question:**
   ```python
   # After run_rag(), run_direct(), or run_hybrid() completes
   if "RAG" in st.session_state.results:
       result = st.session_state.results["RAG"]
       if os.getenv("HISTORY_ENABLED", "true").lower() in ("true", "1", "yes"):
           st.session_state.history_manager.add_question(
               question=result["query"],
               answer=result["raw_answer"],
               mode="RAG",
               metrics_dict={k: result[k] for k in 
                            ["total_seconds", "retrieval_seconds", "generation_seconds",
                             "chunk_count", "prompt_tokens", "completion_tokens", 
                             "total_tokens", "temperature"]},
               document_name=st.session_state.get("uploaded_name", "unknown")
           )
   ```
   (Repeat similarly for Direct LLM and Hybrid modes)

---

### Step 6.3: Add Sidebar History Panel
**Purpose:** Display recent questions filtered by current document

**Implementation in `web_app.py`:**

```python
def render_history_sidebar():
    """Display recent questions for current document in sidebar"""
    if os.getenv("HISTORY_ENABLED", "true").lower() not in ("true", "1", "yes"):
        return
    
    current_doc = st.session_state.get("uploaded_name", None)
    if not current_doc:
        st.sidebar.info("📋 Upload a document to see history")
        return
    
    history = st.session_state.history_manager.get_recent_questions(
        document_name=current_doc,
        limit=int(os.getenv("HISTORY_LIMIT", "10"))
    )
    
    if not history:
        st.sidebar.info("📋 No history yet for this document")
        return
    
    st.sidebar.markdown("### 📋 Session History")
    for i, entry in enumerate(history):
        timestamp = entry["timestamp"][:19]  # YYYY-MM-DD HH:MM:SS
        mode = entry["mode"]
        question = entry["question"][:50] + "..." if len(entry["question"]) > 50 else entry["question"]
        
        if st.sidebar.button(f"[{mode}] {timestamp}\n{question}", key=f"history_{i}"):
            st.session_state.last_question = entry["question"]
            st.rerun()
    
    st.sidebar.divider()
```

**Call this function in `web_app.py` before the main question input:**
```python
render_history_sidebar()
question = st.text_input("Ask a question about the document")
```

---

### Step 6.4: Create `history_cli.py`
**Purpose:** Non-interactive CLI tool for history inspection and analytics

**Commands:**
```bash
# List all questions from all sessions
python history_cli.py list

# List questions for specific session
python history_cli.py list --session user_abc123

# List questions for specific document
python history_cli.py list --document contract.pdf

# Show full details of one question
python history_cli.py show --session user_abc123 --index 0

# Export to CSV
python history_cli.py export --output history.csv
python history_cli.py export --session user_abc123 --output session_history.csv
python history_cli.py export --document contract.pdf --output contract_history.csv

# Manually trigger cleanup
python history_cli.py cleanup --days 30
```

**Implementation outline:**
- Use `argparse` for CLI arguments
- JSON file parsing and filtering
- CSV export via `csv` module with columns: timestamp, question, answer, mode, document_name, metrics.*
- Timestamp/file age comparison for cleanup
- Clear summary output (count of entries, session info, etc.)

---

### Step 6.5: Add Configuration via Environment Variables
**Add to `.env`:**
```env
# Question history tracking (Step 6)
HISTORY_ENABLED=true
HISTORY_RETENTION_DAYS=30
HISTORY_LIMIT=10
```

**Precedence:**
- Env var if set
- Hardcoded default in code
- Feature completely disabled if `HISTORY_ENABLED=false`

---

## Verification

### Web App Functional Tests

**Test 6.1: Single document, multiple questions**
- Upload `contract.pdf`
- Ask 3 questions (different modes: RAG, Direct LLM, Hybrid)
- Verify sidebar shows all 3 with correct timestamps and modes
- Click a sidebar question → question field updates
- Can re-run with any mode

**Test 6.2: Multiple documents in one session**
- Upload `contract.pdf`, ask 2 questions (RAG mode)
- Upload `report.docx`, ask 1 question (Direct LLM mode)
- Sidebar shows only `report.docx`'s 1 question
- Switch back to `contract.pdf` → sidebar shows 2 questions again
- Verify JSON file contains all 3 entries

**Test 6.3: Session isolation (multi-user)**
- Open two browser tabs/windows (or incognito windows)
- Tab 1: Upload `contract.pdf`, ask 2 questions
- Tab 2: Upload `report.docx`, ask 1 question
- Each tab's history is separate; no cross-contamination
- Verify separate `user_*.json` files created

**Test 6.4: Browser close/refresh**
- Ask questions in session, close browser
- Reopen app → no history (new session ID)
- But old history files remain on disk (until cleanup)

**Test 6.5: Cleanup**
- Create a session file manually
- Set its modification time to 31 days ago
- Run app startup cleanup
- Verify old file is deleted, recent files remain

### CLI Functional Tests

**Test 6.6: CLI list and export**
- `python history_cli.py list` → shows all sessions and questions
- `python history_cli.py list --document contract.pdf` → filters correctly
- `python history_cli.py export --output out.csv` → CSV file with correct columns
- `python history_cli.py show --session user_abc123 --index 0` → shows full entry

**Test 6.7: CLI cleanup**
- Age a session file to 31 days old
- `python history_cli.py cleanup --days 30` → removes it
- Recent files remain

### Data Accuracy Checks
- Verify JSON structure matches format above
- Verify timestamps are ISO 8601 format (YYYY-MM-DDTHH:MM:SS.NNNNNN)
- Verify all metrics fields present: total_seconds, retrieval_seconds, generation_seconds, chunk_count, prompt_tokens, completion_tokens, total_tokens, temperature
- Verify metrics values match result dicts from pipeline
- Verify document names captured correctly
- Verify question and answer text preserved accurately

---

## Relevant Files

| File | Type | Purpose |
|---|---|---|
| `src/history_manager.py` | New | Core history logic: JSON I/O, session management, filtering, cleanup |
| `history_cli.py` | New | CLI tool for inspection and batch operations |
| `web_app.py` | Modified | Initialize manager, log questions after each mode, render sidebar, call cleanup |
| `.env` | Modified | Add config variables: HISTORY_ENABLED, HISTORY_RETENTION_DAYS, HISTORY_LIMIT |
| `Docs/STEP_6_HISTORY_TRACKING.md` | New | This documentation |

---

## Architectural Decisions

| Decision | Rationale |
|---|---|
| **Per-session history files** (`user_{session_id}.json`) | Keeps each user's data isolated; leverages Streamlit's native session isolation |
| **Document filtering (UI-level)** | Store all questions; filter in sidebar for clarity without data loss |
| **Multi-user isolation** | Relies on Streamlit's built-in session isolation; no custom auth needed for basic separation |
| **Auto-cleanup on startup** | Silent, non-intrusive; doesn't affect active sessions |
| **File-based storage** | No database dependency; simple to inspect, debug, and audit |
| **CLI tool separate from web app** | Allows admin/analytics access without running the Streamlit app |
| **Complete metrics storage** | Enables future analytics (token trends, mode performance, etc.) |

---

## Multi-User Isolation Guarantees

1. **Concurrent users in different browser sessions:**
   - Separate `st.session_state` objects (Streamlit enforces)
   - Separate uploaded file temp locations (session-scoped)
   - Separate history JSON files (`user_session1.json`, `user_session2.json`)
   - No data leakage between users

2. **Document isolation within and across sessions:**
   - Each upload creates a new session-local temp file
   - Document names are stored with questions for filtering
   - Another user's upload of "contract.pdf" doesn't interfere

3. **Cleanup safety:**
   - Cleanup only touches files with old mtime (>30 days)
   - Doesn't affect active sessions (newer mtime)
   - No race conditions between concurrent users

4. **Admin/CLI access:**
   - Server admin can inspect all history via CLI
   - Filesystem permissions control access
   - Good for auditing and performance analytics

---

## Future Enhancements

1. **History export/download button** in sidebar (CSV for individual session)
2. **History search** — filter by keyword in question or answer
3. **User authentication** (optional) — ties real usernames to sessions
4. **Analytics dashboard** — token usage trends, most-asked questions, mode performance
5. **History compression** — gzip old session files to save disk space
6. **Sync to cloud** (optional) — backup history to S3/Google Drive

---

## Performance Considerations

- **JSON file I/O:** Append-only writes; no file locks needed
- **Sidebar rendering:** Filters history on each rerun (O(n) where n = total questions in session)
- **Cleanup task:** Runs once at startup; linear scan of history/ folder
- **Multi-user overhead:** Each session has its own HistoryManager; no global state contention

For high-volume usage, consider:
- Pagination in sidebar (show last 10, load older on demand)
- Index file (session_id → file path) for faster cleanup
- Eventual migration to SQLite for large history volumes

---

## Integration with Existing Modules

- **`web_app.py`** — Only integration point; calls HistoryManager after each query
- **`pipeline.py`** — No changes needed; metrics already available in result dict
- **`ai_query.py`** — No changes needed; metrics already in return dict
- **`ingest.py`**, **`preprocess.py`**, **`embed_index.py`**, **`prompt_loader.py`** — No changes needed

---

## Testing Checklist

- [ ] `src/history_manager.py` created with all methods
- [ ] `web_app.py` initializes HistoryManager on startup
- [ ] Cleanup called on app startup
- [ ] Questions logged after each mode (RAG/Direct/Hybrid)
- [ ] Sidebar renders and filters by current document
- [ ] Click sidebar question loads it into input field
- [ ] Multiple documents in one session filter correctly
- [ ] Multiple browser sessions don't interfere
- [ ] Browser close/refresh starts new session
- [ ] Old sessions cleaned up after 30 days
- [ ] `history_cli.py` lists, filters, exports correctly
- [ ] `HISTORY_ENABLED=false` disables feature completely
- [ ] JSON file structure matches specification
- [ ] Timestamps in ISO 8601 format
- [ ] All metrics fields present and accurate

---

## Next Steps (After Implementation)

1. Test thoroughly with multiple concurrent users
2. Monitor disk usage; plan cleanup strategy for long-running deployments
3. Consider metrics collection/analytics dashboard
4. Optionally add user authentication for more granular access control
5. Plan for history export/sharing features
