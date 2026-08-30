# Step 10: Cost Tracking & Budget Management

## Overview

**Cost Tracking** is a session-local estimate based on token usage and the fixed rates configured
in `src/cost_tracker.py`. It enforces the app's internal usage limit; the provider dashboard is the
authoritative source for actual billing.

**Purpose:**
- Provide transparent cost visibility to users
- Prevent budget overruns on free tier ($0.50 USD per session)
- Estimate usage with the project's fixed Grok-based pricing constants
- Gracefully handle budget exhaustion without data loss

**Status:** ✅ FULLY IMPLEMENTED (2026-08-25)

---

## Architecture

### Module: `src/cost_tracker.py`

**Core Responsibilities:**
1. Calculate query costs based on token consumption
2. Accumulate costs per session
3. Provide budget enforcement (warnings & blocking)
4. Export cost data for GDPR compliance

**Key Functions:**

| Function | Purpose | Returns |
|----------|---------|---------|
| `initialize_cost_tracker()` | Initialize session state for cost tracking | None |
| `calculate_query_cost(prompt_tokens, completion_tokens)` | Calculate USD cost for a query | float (cost_usd) |
| `track_query_cost(prompt_tokens, completion_tokens)` | Add query cost to session total | float (new_total) |
| `get_session_cost()` | Get cumulative session cost | float (total_usd) |
| `get_remaining_budget()` | Get remaining budget | float (usd) |
| `get_budget_percentage()` | Get usage as percentage (0-100) | float |
| `should_warn()` | Check if 80% threshold reached | bool |
| `is_blocked()` | Check if budget exhausted (100%) | bool |
| `get_cost_badge()` | Get formatted display string | str (e.g., "💚 Cost: 24%") |
| `export_cost_data()` | Export for GDPR compliance | dict |

### Pricing Configuration

**Grok LLM Rates (per 1,000 tokens):**
```python
GROK_INPUT_COST_PER_1K = 0.03    # $0.03 per 1K input tokens
GROK_OUTPUT_COST_PER_1K = 0.10   # $0.10 per 1K output tokens
FREE_BUDGET_USD = 0.50            # $0.50 per session
```

**Calculation Formula:**
```
cost = (input_tokens / 1000 * 0.03) + (completion_tokens / 1000 * 0.10)
```

**Example (100-page document):**
- Input: 1,500 tokens (prompt + context)
- Output: 200 tokens (answer)
- Cost: (1500/1000 * 0.03) + (200/1000 * 0.10) = $0.065 per query
- Budget: $0.50 ÷ $0.065/query ≈ **25 questions**

---

## Integration Points

### 1. Home Page (`app_pages/home.py`)

**Initialization:**
```python
from src.cost_tracker import initialize_cost_tracker
initialize_cost_tracker()  # Called on app startup
```

**Cost Display (after page title):**
```python
st.info(translate("budget_info"))  # "Try for FREE: ~25 questions on ~100 page document..."
col1, col2 = st.columns([3, 1])
with col2:
    st.markdown(get_cost_badge())  # Shows: 💚 Cost: 24%
```

**Warning/Blocking Logic:**
```python
if should_warn() and not is_blocked():
    st.warning("Free testing trial nearly complete: You are approaching the trial limit...")

if is_blocked():
    st.error("Free testing trial complete: Your free testing trial has ended...")
    st.link_button("Share feedback", FEEDBACK_FORM_URL)
    st.stop()
```

The same Google Forms link is shown beside the usage indicator before the limit is reached. It
opens in a new tab, so users may provide feedback at any point without interrupting their session.
Google Forms responses are not written to the app's local `FeedbackManager` storage.

**Cost Tracking on Query:**
```python
result = run_hybrid(...)  # Get answer from LLM

# Only successful provider responses are tracked.
if result.get("response_status") == "success":
    track_query_cost(
        prompt_tokens=result.get("prompt_tokens", 0),
        completion_tokens=result.get("completion_tokens", 0),
    )
```

### 2. AI Query (`src/ai_query.py`)

**Token Extraction:**
The `generate_answer_with_meta()` function returns metadata including:
- `prompt_tokens`: Input token count
- `completion_tokens`: Output token count
- `total_tokens`: Sum of both

This data is passed through the result dict to `app_pages/home.py`.

### 3. GDPR Compliance (`src/gdpr_compliance.py`)

**Data Export:**
Cost data is included in user data exports:
```python
cost_data = export_cost_data()  # From cost_tracker.py
user_export["data"]["cost_tracking"] = {
    "total_cost_usd": cost_data.get("total_cost_usd"),
    "budget_percentage": cost_data.get("budget_percentage"),
    "queries_count": cost_data.get("queries_count"),
}
```

### 4. Internationalization (`src/i18n.py`)

**Budget Info Translation:**
All 5 supported languages have `budget_info` translation:
```
"en": "Try for FREE: you can ask ~25 questions on a ~100 page document..."
"ro": "Încearcă gratuit: poți pune ~25 de întrebări pe un document de ~100 de pagini..."
"fr": "Essayez gratuitement: vous pouvez poser ~25 questions sur un document de ~100 pages..."
"es": "Prueba gratis: puedes hacer ~25 preguntas en un documento de ~100 páginas..."
"de": "Kostenlos testen: Du kannst ~25 Fragen zu einem ~100-seitigen Dokument stellen..."
```

---

## Session State Storage

**Key:** `"llm_cost_tracker"`

**Structure:**
```python
{
    "total_cost_usd": 0.245,              # Cumulative spend
    "queries_count": 4,                   # Questions asked
    "queries": [                          # Detailed log
        {
            "timestamp": "2026-08-25T10:30:45.123456",
            "prompt_tokens": 1500,
            "completion_tokens": 200,
            "cost_usd": 0.065,
        },
        ...
    ],
    "blocked": False,                     # Budget exhausted?
}
```

**Persistence:**
- Lives in `st.session_state` (Streamlit browser session only)
- NOT persisted to disk (resets on new session)
- This is intentional: users get fresh $0.50 budget on each session

---

## User Experience Flow

### 1. First Visit
```
User opens app
    ↓
Session initializes with $0.50 budget
    ↓
App displays: "Try for FREE: ~25 questions on ~100 page doc"
    ↓
Cost badge shows: 💚 Cost: 0%
```

### 2. Asking Questions (Normal)
```
User asks a question
    ↓
LLM processes (e.g., 1500 prompt tokens, 200 output tokens)
    ↓
Cost calculated: $0.065
    ↓
Cost badge updates: 💚 Cost: 13% ($0.065 / $0.50)
    ↓
User sees answer + chat history
```

### 3. Approaching Limit (80% Warning)
```
User asks another question
    ↓
Total cost now: $0.42 (84% of $0.50)
    ↓
Cost badge turns yellow: ⚠️ Cost: 84%
    ↓
Warning banner appears: "⚠️ Budget Warning: 80% of budget used"
    ↓
User can still ask 1-2 more questions
```

### 4. Budget Exhausted (100% Blocking)
```
User asks another question, total would be $0.51
    ↓
Cost tracker detects: 100% budget exceeded
    ↓
Cost badge turns red: 🛑 Cost: 102%
    ↓
Trial-complete message and Google Forms link appear
    ↓
User can open the optional feedback form in a new tab
    ↓
app.stop() — the chat input is not rendered and no more questions are allowed
```

---

## Testing Methods

### Unit Tests: Token Cost Calculation
```python
from src.cost_tracker import calculate_query_cost

# Test: 1500 input + 200 output tokens
cost = calculate_query_cost(1500, 200)
assert cost == (1.5 * 0.03) + (0.2 * 0.10)  # $0.065
```

### Integration Test: Session Tracking
```python
import streamlit as st
from src.cost_tracker import track_query_cost, get_session_cost, should_warn

# Simulate 8 queries (typical budget for 100-page doc)
for i in range(8):
    track_query_cost(1500, 200)

cost = get_session_cost()
assert cost == 8 * 0.065  # $0.52
assert should_warn()  # 104% > 80%
```

### Manual Testing: Web App
1. Open app, confirm budget info displays
2. Upload 100-page PDF, ask 5-10 questions
3. Watch cost badge update in real-time
4. Reach ~80% and confirm warning appears
5. Reach 100% and confirm app blocks new questions

---

## Cost Model Assumptions

**For 100-page document:**

| Metric | Estimate | Rationale |
|--------|----------|-----------|
| Pages | ~100 | Medium-length document |
| Tokens/page | 300-500 | ~150 words/page avg |
| Total doc tokens | 30k-50k | Full text extraction |
| Avg prompt size | 1,500 tokens | Includes question + retrieved chunks |
| Avg output size | 200 tokens | ~150-word answer |
| Cost/query | $0.020-0.025 | Based on Grok pricing |
| **Questions in budget** | **~25** | $0.50 ÷ $0.020 |

**For smaller documents (10 pages):**
- Avg prompt: 500 tokens (less context needed)
- Avg output: 150 tokens
- Cost/query: ~$0.018
- Questions: ~28 (slightly more)

**For larger documents (500+ pages):**
- Avg prompt: 3,000+ tokens (more context)
- Avg output: 300 tokens
- Cost/query: ~$0.12
- Questions: ~4 (significantly fewer)

---

## Limitations & Edge Cases

### 1. Token Count Accuracy
- Uses provider token counts when available
- Falls back to a rough character-based estimate when a successful response omits usage data
- Configured provider failures return zero tokens and are not added to the app's usage tracker

### 2. Fallback Behavior
- Missing provider configuration produces a labeled simulation that is not tracked
- Configured provider failures are not tracked or saved as answers
- Successful responses without usage metadata are tracked using estimated token counts

### 3. No Persistent Storage
- Cost data resets on new browser session
- Intentional: each user gets independent $0.50 budget
- For multi-user analytics, export data via GDPR endpoint

### 4. No Upgrade Path
- Free tier is $0 (no paid tiers implemented yet)
- Users can only restart session for fresh budget
- Future: implement paid tier to lift budget limits

---

## Future Enhancements

- [ ] Support multiple LLM providers (OpenAI, Groq, Claude)
- [ ] Persistent usage analytics (opt-in)
- [ ] Paid tier with higher budgets ($10, $50, unlimited)
- [ ] Budget presets (conservative, balanced, aggressive)
- [ ] Cost alerts via email
- [ ] Usage reports & forecast graphs
- [ ] Family/team budget pooling

---

## References

- **Grok Pricing:** https://x.ai/pricing
- **Token Counting:** OpenAI GPT tokenizer documentation
- **GDPR Right to Erasure:** Data deleted on session end
- **Related Files:**
  - `src/cost_tracker.py` — Implementation
    - `app_pages/home.py` — Integration & display
  - `src/gdpr_compliance.py` — Data export integration
  - `src/i18n.py` — Budget info translations
