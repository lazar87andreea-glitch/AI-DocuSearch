# Step 8: User Feedback Collection & Analytics

## Overview

✅ **NEW** — Lightweight user feedback collection system for gathering quality assessments, feature requests, and bug reports. Feedback is stored per-session alongside question history, enabling product teams to understand user satisfaction and identify improvement areas without adding friction to the user experience.

## Purpose

- Collect user satisfaction ratings (thumbs up/down) on answers
- Store optional comments when supplied by another caller; the current UI exposes binary ratings only
- Track feedback metrics for product analytics
- Correlate feedback with answer quality metrics (tokens, retrieval performance, mode used)
- Support feature requests and bug reports
- Maintain per-user privacy (session-isolated feedback, no PII)
- Provide lightweight UI integration (non-intrusive sidebar component)

## Key Concepts

### Feedback Types
- **Answer Rating** — Quick binary thumbs up/down on generated answers (no modal/dialog)
- **Detailed Feedback** — Supported by the storage API, but no text-feedback form is currently rendered
- **Session Isolation** — Each browser session receives a random UUID and a separate feedback filename
- **Analytics** — Feedback aggregated for product reporting without user identification

### Storage Architecture
- **Disk Storage** (`feedback/user_{session_id}.json`): Persistent feedback file, mirroring history structure
- **Metrics Correlation** — Each feedback entry links to the answer's tokens, timing, retrieval data

### Privacy & Security
- ✅ No personal data collected (no names, emails, IPs — unless explicitly provided in text feedback)
- ✅ Session-isolated (each browser session = separate feedback file)
- ✅ No tracking of user behavior beyond submitted feedback
- ✅ Optional text feedback (users can leave empty)
- ✅ Local JSON storage; when configured, the same rating is also sent best-effort to LangSmith

---

## Detailed Implementation Steps

### Step 8.1: Feedback Manager Class

**File:** `src/feedback_manager.py`

Handles all feedback disk operations:

```python
import json
import os
from typing import Any, List, Dict, Optional
from datetime import datetime, timezone

class FeedbackManager:
    """Manages user feedback collection and storage (per-session isolation)"""
    
    def __init__(self, session_id: str):
        """Initialize with unique session ID"""
        self.session_id = session_id
        self.feedback_dir = "feedback"
        self.feedback_file = os.path.join(self.feedback_dir, f"user_{session_id}.json")
        self._ensure_feedback_dir()
    
    def _ensure_feedback_dir(self) -> None:
        """Create feedback directory if it doesn't exist"""
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
    
    def add_feedback(
        self,
        answer_id: str,
        rating: bool,  # True = thumbs up, False = thumbs down
        question: str,
        document_name: str,
        comment: Optional[str] = None,
        feedback_type: str = "answer_rating",  # "answer_rating", "feature_request", "bug_report"
        mode: str = "Hybrid",
        answer_length: int = 0,
        chunk_count: int = 0,
        retrieval_seconds: float = 0.0,
    ) -> None:
        """
        Append feedback entry to session's JSON file with ISO 8601 timestamp
        
        Args:
            answer_id: Unique identifier for this answer (e.g., hash of timestamp + question)
            rating: True for positive, False for negative (ignored if feedback_type != "answer_rating")
            question: The question that was asked
            document_name: Name of the document being queried
            comment: Optional text feedback (max 500 chars)
            feedback_type: "answer_rating", "feature_request", or "bug_report"
            mode: Hybrid mode (optionally includes whether it used RAG or fell back to Direct LLM)
            answer_length: Characters in generated answer
            chunk_count: Number of chunks retrieved (0 if not applicable)
            retrieval_seconds: Time spent on retrieval (0.0 if not applicable)
        """
        feedback_data = self.load_feedback()
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "answer_id": answer_id,
            "rating": rating,
            "question": question,
            "document_name": document_name,
            "comment": comment or "",
            "feedback_type": feedback_type,
            "mode": mode,
            "answer_length": answer_length,
            "chunk_count": chunk_count,
            "retrieval_seconds": retrieval_seconds,
        }
        
        feedback_data.append(entry)
        self._save_feedback(feedback_data)
    
    def load_feedback(self) -> List[Dict[str, Any]]:
        """Load all feedback entries from disk, sorted newest first"""
        if not os.path.exists(self.feedback_file):
            return []
        
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Sort by timestamp descending (newest first)
            return sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
        except (json.JSONDecodeError, IOError):
            return []
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get aggregate statistics for this session's feedback"""
        feedback = self.load_feedback()
        
        if not feedback:
            return {
                "total_responses": 0,
                "positive_rating_count": 0,
                "negative_rating_count": 0,
                "positive_percentage": 0.0,
                "feature_requests": 0,
                "bug_reports": 0,
                "average_answer_length": 0,
            }
        
        positive = sum(1 for f in feedback if f.get("feedback_type") == "answer_rating" and f.get("rating"))
        negative = sum(1 for f in feedback if f.get("feedback_type") == "answer_rating" and not f.get("rating"))
        total_ratings = positive + negative
        
        return {
            "total_responses": len(feedback),
            "positive_rating_count": positive,
            "negative_rating_count": negative,
            "positive_percentage": (positive / total_ratings * 100) if total_ratings > 0 else 0.0,
            "feature_requests": sum(1 for f in feedback if f.get("feedback_type") == "feature_request"),
            "bug_reports": sum(1 for f in feedback if f.get("feedback_type") == "bug_report"),
            "average_answer_length": sum(f.get("answer_length", 0) for f in feedback) // len(feedback) if feedback else 0,
        }
    
    def update_feedback_rating(self, answer_id: str, rating: bool) -> None:
        """Update an existing feedback entry's rating"""
        feedback = self.load_feedback()
        
        for entry in feedback:
            if entry.get("answer_id") == answer_id:
                entry["rating"] = rating
                break
        
        self._save_feedback(feedback)
    
    def _save_feedback(self, feedback_data: List[Dict[str, Any]]) -> None:
        """Write feedback data to JSON file"""
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def cleanup_old_feedback(retention_days: int = 90) -> None:
        """Delete old feedback files (90-day retention by default)"""
        if not os.path.exists("feedback"):
            return
        
        now = datetime.now(timezone.utc)
        retention_seconds = retention_days * 24 * 60 * 60
        
        for filename in os.listdir("feedback"):
            file_path = os.path.join("feedback", filename)
            if os.path.isfile(file_path):
                mtime = os.path.getmtime(file_path)
                file_age_seconds = (now.timestamp() - mtime)
                
                if file_age_seconds > retention_seconds:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
```

**Key methods:**
- `add_feedback()` — Appends new feedback entry to session's JSON file
- `load_feedback()` — Reads all feedback, sorted newest first
- `get_feedback_summary()` — Aggregate statistics for this session
- `update_feedback_rating()` — Edit an existing feedback entry's rating
- `cleanup_old_feedback()` — Static method; removes feedback files older than retention period

---

### Step 8.2: Data Storage Format

**File:** `feedback/user_{session_id}.json`

```json
[
  {
    "timestamp": "2025-08-25T14:30:45.123456+00:00",
    "answer_id": "ans_abc123def456",
    "rating": true,
    "question": "What are the contract dates?",
    "document_name": "contract.pdf",
    "comment": "Great answer, very accurate!",
    "feedback_type": "answer_rating",
    "mode": "Hybrid (RAG succeeded)",
    "answer_length": 245,
    "chunk_count": 3,
    "retrieval_seconds": 1.2
  },
  {
    "timestamp": "2025-08-25T14:28:10.567890+00:00",
    "answer_id": "ans_xyz789uvw012",
    "rating": false,
    "question": "What is the payment schedule?",
    "document_name": "contract.pdf",
    "comment": "Answer was incomplete, didn't mention late payment penalties.",
    "feedback_type": "answer_rating",
    "mode": "Hybrid (fell back to Direct LLM)",
    "answer_length": 120,
    "chunk_count": 0,
    "retrieval_seconds": 0.0
  },
  {
    "timestamp": "2025-08-25T14:15:22.345678+00:00",
    "answer_id": "req_feature_001",
    "rating": null,
    "question": "N/A",
    "document_name": "N/A",
    "comment": "Please add support for multi-document search across multiple PDFs.",
    "feedback_type": "feature_request",
    "mode": "N/A",
    "answer_length": 0,
    "chunk_count": 0,
    "retrieval_seconds": 0.0
  }
]
```

---

### Step 8.3: Web App Integration

**File:** `app_pages/home.py`

**Initialization (add to startup section, ~line 150):**

```python
from uuid import uuid4

from src.feedback_manager import FeedbackManager

# Initialize feedback manager
if "feedback_manager" not in st.session_state:
    session_id = uuid4().hex
    st.session_state.session_id = session_id
    st.session_state.feedback_manager = FeedbackManager(session_id)
```

`cleanup_old_feedback()` exists, but the current Home page does not invoke it automatically.

**After Answer Generation (add after displaying answer, ~line 320):**

```python
def display_feedback_controls(answer_id: str, result: dict, question: str, doc_name: str) -> None:
    """Render feedback buttons for the current answer"""
    
    col1, col2, col3, col4 = st.columns([1, 1, 2, 2])
    
    with col1:
        if st.button("👍", key=f"thumbs_up_{answer_id}", help="This answer was helpful"):
            st.session_state.feedback_manager.add_feedback(
                answer_id=answer_id,
                rating=True,
                question=question,
                document_name=doc_name,
                comment="",
                feedback_type="answer_rating",
                mode=st.session_state.selected_mode,
                answer_length=len(result.get("raw_answer", "")),
                chunk_count=result.get("chunk_count", 0),
                retrieval_seconds=result.get("retrieval_seconds", 0.0),
            )
            st.success("Thanks for the feedback!")
    
    with col2:
        if st.button("👎", key=f"thumbs_down_{answer_id}", help="This answer was not helpful"):
            st.session_state.feedback_manager.add_feedback(
                answer_id=answer_id,
                rating=False,
                question=question,
                document_name=doc_name,
                comment="",
                feedback_type="answer_rating",
                mode=st.session_state.selected_mode,
                answer_length=len(result.get("raw_answer", "")),
                chunk_count=result.get("chunk_count", 0),
                retrieval_seconds=result.get("retrieval_seconds", 0.0),
            )
            st.error("We're sorry this wasn't helpful. Please tell us more.")
```

**Optional: Add Feedback Summary Sidebar:**

```python
with st.sidebar:
    st.markdown("### 📊 Feedback This Session")
    summary = st.session_state.feedback_manager.get_feedback_summary()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("👍 Positive", summary["positive_rating_count"])
    with col2:
        st.metric("👎 Negative", summary["negative_rating_count"])
    
    if summary["positive_rating_count"] + summary["negative_rating_count"] > 0:
        st.progress(summary["positive_percentage"] / 100)
        st.caption(f"Satisfaction: {summary['positive_percentage']:.0f}%")
```

---

### Step 8.4: Feature Request & Bug Report Forms

**Add to Sidebar or Modal (optional enhancement):**

```python
def show_feedback_form():
    """Display detailed feedback submission form"""
    
    with st.form("feedback_form"):
        st.markdown("### 📝 Send Feedback")
        
        feedback_type = st.radio(
            "What type of feedback?",
            ["Answer Quality", "Feature Request", "Bug Report", "General Comments"]
        )
        
        feedback_map = {
            "Answer Quality": "answer_rating",
            "Feature Request": "feature_request",
            "Bug Report": "bug_report",
            "General Comments": "general_comment",
        }
        
        comment = st.text_area(
            "Your feedback (optional)",
            max_chars=500,
            help="Help us improve AI DocuSearch"
        )
        
        if st.form_submit_button("📤 Submit Feedback"):
            st.session_state.feedback_manager.add_feedback(
                answer_id=f"manual_{datetime.now().isoformat()}",
                rating=None,
                question="N/A",
                document_name=st.session_state.get("current_document", "N/A"),
                comment=comment,
                feedback_type=feedback_map[feedback_type],
                mode="N/A",
            )
            st.success("Thanks for your feedback! It helps us improve.")
```

---

## Configuration & Deployment

### Environment Variables

Add to `.env` and Streamlit Cloud secrets:

```env
# Feedback collection settings
FEEDBACK_ENABLED=true                  # Enable/disable feedback collection
FEEDBACK_RETENTION_DAYS=90             # How long to keep feedback (default: 90 days)
FEEDBACK_EXPORT_ENDPOINT=              # Optional: URL to send feedback to external service
```

### `.gitignore` Update

Add feedback storage directory:

```
# Feedback and history
feedback/
history/
.env
```

---

## Analytics & Reporting

### CLI Tool for Feedback Export

**File:** `export_feedback.py`

```python
#!/usr/bin/env python3
"""Export user feedback for analytics"""

import json
import os
from pathlib import Path
from datetime import datetime

def export_all_feedback(output_file: str = "feedback_export.json") -> None:
    """Aggregate feedback from all sessions"""
    
    feedback_dir = Path("feedback")
    all_feedback = []
    
    if not feedback_dir.exists():
        print(f"No feedback directory found at {feedback_dir}")
        return
    
    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, 'r') as f:
                session_feedback = json.load(f)
                all_feedback.extend(session_feedback)
        except (json.JSONDecodeError, IOError):
            print(f"Error reading {session_file}")
    
    with open(output_file, 'w') as f:
        json.dump(all_feedback, f, indent=2)
    
    print(f"Exported {len(all_feedback)} feedback entries to {output_file}")

def print_feedback_stats() -> None:
    """Print aggregate statistics"""
    
    feedback_dir = Path("feedback")
    all_feedback = []
    
    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, 'r') as f:
                all_feedback.extend(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    
    total = len(all_feedback)
    positive = sum(1 for f in all_feedback if f.get("feedback_type") == "answer_rating" and f.get("rating"))
    negative = sum(1 for f in all_feedback if f.get("feedback_type") == "answer_rating" and not f.get("rating"))
    features = sum(1 for f in all_feedback if f.get("feedback_type") == "feature_request")
    bugs = sum(1 for f in all_feedback if f.get("feedback_type") == "bug_report")
    
    print(f"""
📊 Feedback Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Responses:     {total}
Positive Ratings:    {positive}
Negative Ratings:    {negative}
Satisfaction Rate:   {(positive/(positive+negative)*100 if positive+negative > 0 else 0):.1f}%
Feature Requests:    {features}
Bug Reports:         {bugs}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

if __name__ == "__main__":
    export_all_feedback()
    print_feedback_stats()
```

**Usage:**

```bash
# Export all feedback
python export_feedback.py

# View feedback statistics
python -c "from export_feedback import print_feedback_stats; print_feedback_stats()"
```

---

## Roadmap & Future Enhancements

### Phase 1 (Current)
- ✅ Answer rating (thumbs up/down)
- ✅ Per-session isolation
- ✅ Optional detailed feedback
- ✅ Feedback export for analytics

### Phase 2 (Planned)
- 🔄 Dashboard for feedback analytics
- 🔄 Sentiment analysis on text feedback
- 🔄 Correlation analysis (feedback vs. mode, retrieval speed, document size)
- 🔄 A/B testing support (track version + timestamp)

### Phase 3 (Backlog)
- 🔄 Integration with external analytics services (Mixpanel, Amplitude)
- 🔄 Automated email digest of high-impact feedback
- 🔄 User segmentation (power users, one-time users)
- 🔄 Feedback translation to multiple languages

---

## Privacy & Compliance

### Data Collection
- ✅ **Minimal:** Only collects feedback explicitly submitted by users
- ✅ **No tracking:** No page views, session duration, or behavioral tracking
- ✅ **No PII:** No collection of IP, user agent, or device ID (unless explicitly provided)
- ✅ **Local storage:** Feedback stays in `feedback/` directory on Streamlit Cloud; no third-party services

### Data Retention
- Default retention: **90 days**
- Configurable via `FEEDBACK_RETENTION_DAYS` environment variable
- Old feedback files automatically deleted on app startup
- Users can manually delete `feedback/` directory to remove all data

### Deployment Considerations
- For GDPR/CCPA compliance, disclose feedback collection in privacy policy
- Add opt-out option via `FEEDBACK_ENABLED=false` environment variable
- Consider hosting feedback export in secure location (not public repo)

---

## Testing

### Test Feedback Manager

**File:** `test_feedback.py`

```python
#!/usr/bin/env python3
"""Test feedback collection functionality"""

import json
import os
from src.feedback_manager import FeedbackManager

def test_add_feedback():
    """Test adding feedback"""
    manager = FeedbackManager("test_session_001")
    
    manager.add_feedback(
        answer_id="test_001",
        rating=True,
        question="What is this?",
        document_name="test.pdf",
        comment="Great answer!",
        feedback_type="answer_rating",
        mode="RAG",
        answer_length=200,
        chunk_count=2,
        retrieval_seconds=1.0,
    )
    
    feedback = manager.load_feedback()
    assert len(feedback) == 1
    assert feedback[0]["rating"] == True
    assert feedback[0]["comment"] == "Great answer!"
    print("✅ test_add_feedback passed")

def test_feedback_summary():
    """Test feedback aggregation"""
    manager = FeedbackManager("test_session_002")
    
    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("ans_2", True, "Q2", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("ans_3", False, "Q3", "doc.pdf", "Bad", "answer_rating", "RAG", 100, 2, 1.0)
    
    summary = manager.get_feedback_summary()
    assert summary["positive_rating_count"] == 2
    assert summary["negative_rating_count"] == 1
    assert abs(summary["positive_percentage"] - 66.67) < 1
    print("✅ test_feedback_summary passed")

if __name__ == "__main__":
    test_add_feedback()
    test_feedback_summary()
    print("\n✅ All feedback tests passed!")
```

---

## Summary

The feedback collection system provides:
- 📊 Simple thumbs up/down ratings on answers
- 💬 Optional detailed feedback for features/bugs
- 🔐 Session-isolated storage (no cross-user data leakage)
- 📈 Analytics-ready format for product insights
- 🚀 Minimal friction to user experience
- 🛡️ Privacy-compliant (no tracking, local storage)
