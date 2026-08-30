# Step 11: GDPR Compliance & Legal Framework

## Overview

This module provides consent, local-data export, local-data deletion, and legal disclosures intended
to support privacy obligations. These technical controls do not by themselves certify compliance
with GDPR, CCPA, or any other law.

**Purpose:**
- Obtain explicit user consent before processing documents
- Provide users with data export (right to portability)
- Enable users to delete locally associated history, feedback, and selected in-memory document state
- Transparently disclose third-party data sharing
- Host Privacy Policy, Terms of Service, and Third-Party Services pages

**Status:** Implemented for experimental use; legal and security review is still required before production use.

---

## Architecture

### Module: `src/gdpr_compliance.py`

**Core Responsibilities:**
1. Display consent banner before document processing
2. Manage consent state (accept/reject)
3. Export user data in portable JSON format
4. Delete the current session's server-local history and feedback files and selected in-memory state
5. Display third-party service disclosures

**Key Functions:**

| Function | Purpose | Returns |
|----------|---------|---------|
| `show_consent_banner()` | Display GDPR notice, require checkbox + button | bool (consent_given) |
| `export_user_data(session_id, ...)` | Export all user data as JSON | dict |
| `delete_user_data(session_id, ...)` | Permanently delete user's data | bool (success) |
| `show_gdpr_footer(session_id, ...)` | Display footer with data management links | None |
| `get_consent_key()` | Get session state key for consent tracking | str |

### Legal Documents

The application renders `PRIVACY_POLICY.md`, `TERMS_OF_SERVICE.md`, and
`THIRD_PARTY_SERVICES.md` as linked in-app pages registered by `web_app.py`.

**PRIVACY_POLICY.md** (8,200+ lines)
- Comprehensive GDPR/CCPA compliance documentation
- Sections:
  1. Data collection methods
  2. Legal basis for processing
  3. Data retention periods
  4. International transfers
  5. Third-party sharing (LLM providers, LangSmith, ip-api.com)
  6. User rights (access, deletion, portability, restriction, objection)
  7. Security measures
  8. Cookie policy
  9. Children's privacy
  10. Data breach notification
  11. Contact information
  12. Policy updates
  13. Regulatory compliance (GDPR, CCPA, PIPEDA, POPIA, LGPD)
  14. Cookies & tracking
  15. Marketing & communications

**TERMS_OF_SERVICE.md** (5,500+ lines)
- User agreement & AI system disclaimers
- Sections:
  1. Service description
  2. User eligibility & accounts
  3. Acceptable use policy
  4. AI limitations & disclaimers
  5. Limitation of liability
  6. Indemnification
  7. IP rights & licensing
  8. Third-party services
  9. Termination & suspension
  10. Modification of terms
  11. Dispute resolution
  12. Governing law
  13. Severability
  14. GDPR/CCPA compliance
  15. Export controls
  16. Entire agreement
  17. Contact information
  18. Definitions

---

## Consent Flow

### 1. First Visit — Consent Banner

**When:** User opens app for first time (before any content shown)

**Display:**
```
🔒 Privacy & Data Processing Notice

By using AI DocuSearch, you consent to:
- Processing your documents with AI models
- Storing chat history for 30 days (auto-deleted)
- Analytics & debugging via LangSmith
- Language detection from IP/browser

Your rights:
- 📥 Download your data anytime
- 🗑️ Delete your data anytime
- ⏰ Auto-deletion after 30 days

[✅ I Agree & Continue] [ℹ️ More info]
```

**Implementation:**
```python
from src.gdpr_compliance import show_consent_banner

if not show_consent_banner():
    st.stop()  # Block app until consent given
```

**Session State:**
- Key: `"gdpr_consent_given"`
- Value: `True` after button click
- Persists: Across reruns (user doesn't re-consent on page refresh)

### 2. Accepted — Processing Enabled

Once consent given:
- Document upload enabled
- Questions can be asked
- Chat history recorded
- Cost tracking starts

### 3. Footer — Data Management Links

**Always visible** at bottom of page:

```
### 🔒 Privacy & Data Management

[📥 Download Data] [🗑️ Delete Data] [📜 Privacy] [📋 Terms] [🔗 3rd Parties]

Your GDPR Rights:
- ✅ Access your data (📥 Download)
- ✅ Delete your data (🗑️ Delete)
- ✅ Data portability (JSON format)
- ✅ Restrict processing
- ✅ Object to tracking
```

---

## Data Export (Right to Portability)

### Trigger: "Download Data" Button

**What's Exported:**
```json
{
  "export_date": "2026-08-25T10:45:30.123456",
  "session_id": "user_12345",
  "version": "1.0",
  "data": {
    "questions_and_answers": [
      {
        "timestamp": "2026-08-25T10:30:00",
        "question": "What are contract dates?",
        "answer": "The contract runs from June 1 to August 31, 2026...",
        "document": "contract.pdf",
        "mode": "Hybrid",
        "metrics": {
          "total_seconds": 2.34,
          "chunk_count": 3,
          "total_tokens": 450
        }
      }
    ],
    "feedback": [
      {
        "timestamp": "2026-08-25T10:31:00",
        "rating": "positive",
        "question": "What are contract dates?",
        "comment": "Accurate and concise"
      }
    ],
    "cost_tracking": {
      "total_cost_usd": 0.12,
      "remaining_budget_usd": 0.38,
      "budget_percentage": 24,
      "queries_count": 6
    },
    "metadata": {
      "total_questions": 8,
      "total_feedback_entries": 2,
      "export_format": "JSON",
      "portability": "This data can be imported into any compatible service"
    }
  }
}
```

### Format
- **File name:** `docusearch_data_{session_id}_{timestamp}.json`
- **MIME type:** `application/json`
- **Encoding:** UTF-8
- **Portability:** Standard JSON, no proprietary format

### Use Cases
- User compliance: Comply with GDPR Article 15 (right to access)
- Data portability: GDPR Article 20 (transfer to another service)
- Personal backup: User downloads their conversation history
- Audit trail: Evidence of data processing for legal review

---

## Data Deletion (Right to Erasure)

### Trigger: "Delete Data" Button

**Safeguard:** Confirmation checkbox required
```
⚠️ This will permanently delete ALL your data!
[☐ I understand - delete everything]
```

**What's currently deleted:**
1. Chat history file (`history/user_{session_id}.json`)
2. Feedback file (`feedback/user_{session_id}.json`) — if exists
3. In-memory chat history, extracted document text, retrieval pipeline, and page count

The current implementation does not clear every Streamlit state key or the session cost tracker,
and it cannot delete copies already processed or retained by configured third-party services.

**Implementation:**
```python
def delete_user_data(session_id, history_manager, feedback_manager=None):
    # Delete history
    history_file = Path("history") / f"user_{session_id}.json"
    if history_file.exists():
        history_file.unlink()
    
    # Delete feedback
    feedback_file = Path("feedback") / f"user_{session_id}.json"
    if feedback_file.exists():
        feedback_file.unlink()
    
    # Clear selected in-memory document and chat state
    st.session_state.chat_history = []
    st.session_state.document_text = None
    st.session_state.rag_pipeline = None
    st.session_state.page_count = None
    
    return True
```

**User Confirmation:**
```
✅ Locally associated history, feedback, and selected document state were deleted.
```

Deletion of the local files is irreversible. Third-party retention is governed by each configured
provider and is outside this control.

---

## Third-Party Data Sharing

### Services with Data Access

| Service | Data Shared | Purpose | Privacy |
|---------|-------------|---------|---------|
| **Grok (xAI)** | Document text + questions | LLM processing | xAI Privacy Policy |
| **LangSmith** | Token counts, latency, logs | Debugging & monitoring | LangSmith Privacy |
| **ip-api.com** | IP address only | Language detection | No data storage |
| **Streamlit Cloud** | App data | Hosting | Streamlit Privacy |

### Disclosure
Displayed in footer + Privacy Policy:
```
🔗 Third-Party Services:
- Grok LLM: Document processing
- LangSmith: Analytics & debugging
- ip-api.com: Geolocation-based language detection
- Streamlit Cloud: App hosting
```

### User Control
- Users can disable LangSmith: Set `LANGSMITH_TRACING=false`
- Language detection can't be disabled (required for UX)
- Relevant document chunks are sent to the configured LLM for RAG answers; the full extracted text
  may be sent during Direct LLM fallback

---

## Integration Points

### 1. Home Page (`app_pages/home.py`)

**Consent Check (early):**
```python
from src.gdpr_compliance import show_consent_banner

if not show_consent_banner():
    st.stop()
```

**Footer Display (late):**
```python
from src.gdpr_compliance import show_gdpr_footer

show_gdpr_footer(
    session_id=str(st.session_state.get("session_id", "unknown")),
    history_manager=st.session_state.get("history_manager"),
    feedback_manager=None
)
```

### 2. Cost Tracker (`src/cost_tracker.py`)

**Data Included in Export:**
```python
cost_data = export_cost_data()  # From cost_tracker

# In GDPR export
user_export["data"]["cost_tracking"] = {
    "total_cost_usd": cost_data["total_cost_usd"],
    "remaining_budget_usd": cost_data["remaining_budget_usd"],
    "budget_percentage": cost_data["budget_percentage"],
    "queries_count": cost_data["queries_count"],
}
```

### 3. History Manager (`src/history_manager.py`)

**Data Exported:**
- All questions & answers for session
- Document name & timestamp
- Performance metrics

**Data Deleted:**
- History JSON file removed from disk

---

## Regulatory Compliance

### GDPR (European Union)

**Applicable Articles:**
- Art. 5: Lawful basis (consent + transparency)
- Art. 12-15: Right to access data
- Art. 16: Right to rectification
- Art. 17: Right to erasure ("right to be forgotten")
- Art. 20: Right to data portability
- Art. 21: Right to object
- Art. 22: Automated decision-making
- Art. 32-36: Data security, breach notification

**Compliance:**
✅ Explicit consent before processing  
✅ Transparent privacy policy  
✅ Data export in portable format  
✅ Permanent deletion capability  
✅ No automated decision-making  
✅ Secure data handling (HTTPS, memory isolation)  
✅ Breach notification process documented  

### CCPA (California, USA)

**Applicable Sections:**
- § 1798.100: Right to know
- § 1798.105: Right to delete
- § 1798.110: Right to know (categories of data)
- § 1798.115: Right to know (data sources)
- § 1798.130: Right to opt-out of sale

**Compliance:**
✅ Data export (right to know)  
✅ Data deletion (right to delete)  
✅ Privacy policy disclosures  
✅ No data "sale" (no third-party sharing for money)  

### PIPEDA (Canada)
✅ Consent + transparency  
✅ Data access/portability  
✅ Deletion capability  

### POPIA (South Africa)
✅ Lawful processing basis  
✅ Purpose limitation  
✅ Data minimization  

### LGPD (Brazil)
✅ Legal basis for processing  
✅ Data export & deletion  
✅ Privacy policy  

---

## User Experience

### Before Processing
```
1. User opens app
2. Consent banner appears (cannot dismiss)
3. User reads: "Processing documents with AI..."
4. User clicks checkbox: "I understand..."
5. User clicks "I Agree & Continue"
6. Banner disappears, app unlocks
7. User can now upload documents
```

### After Accepting
```
1. User uploads PDF, asks questions
2. At any time, user can click "Download Data" (footer)
3. Browser downloads JSON file with all history
4. Or user can click "Delete Data" to wipe everything
5. Links to Privacy Policy and Terms open dedicated pages inside the Streamlit application
```

### On Deletion
```
1. User clicks "Delete Data"
2. Warning appears: "This is permanent"
3. Checkbox required: "I understand"
4. User clicks "Delete"
5. All data removed instantly
6. Success message: "Data deleted"
7. Session clears, app resets
```

---

## Testing Methods

### Unit Tests: Consent Tracking
```python
import streamlit as st
from src.gdpr_compliance import show_consent_banner, get_consent_key

# Test: Initially no consent
assert get_consent_key() not in st.session_state

# Simulate user clicking "I Agree"
st.session_state[get_consent_key()] = True
assert show_consent_banner() == True  # Returns True after consent
```

### Integration Test: Data Export
```python
from src.gdpr_compliance import export_user_data

user_data = export_user_data(
    session_id="test_123",
    history_manager=history_mgr,
    feedback_manager=None
)

assert user_data["session_id"] == "test_123"
assert "questions_and_answers" in user_data["data"]
assert "cost_tracking" in user_data["data"]
```

### Manual Testing: Full Flow
1. Open app incognito/private window
2. Consent banner appears ✓
3. Cannot upload file until consent ✓
4. Click checkbox + button ✓
5. Upload document ✓
6. Ask question ✓
7. Scroll to footer ✓
8. Click "Download Data" — JSON downloads ✓
9. Click "Delete Data" — confirmation required ✓
10. Verify data deleted (attempt to view history) ✓

---

## Limitations & Future Work

### Current
- Consent banner blocks entire app (strict but user-friendly)
- Email verification not implemented
- No multi-device synchronization

### Planned
- [ ] Cookie-based consent (remember across devices)
- [ ] Email-based data deletion requests
- [ ] Account linking (multi-session tracking)
- [ ] Audit logs for compliance reports
- [ ] DPIA (Data Protection Impact Assessment) tool

---

## References

- **GDPR:** https://gdpr-info.eu/
- **CCPA:** https://oag.ca.gov/privacy/ccpa
- **Privacy Policy:** [PRIVACY_POLICY.md](../PRIVACY_POLICY.md)
- **Terms of Service:** [TERMS_OF_SERVICE.md](../TERMS_OF_SERVICE.md)
- **Legal Counsel:** Consult a lawyer for your jurisdiction

---

## Contact & Support

For privacy inquiries, data requests, or concerns:
- Email: [privacy@example.com] — **Add your email**
- GitHub Issues: [Report compliance bugs]
- Privacy Dashboard: [Future feature]

---

**Last Updated:** 2026-08-30
**Version:** 1.1
**Status:** Experimental privacy controls; not a legal compliance certification
