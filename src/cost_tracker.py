"""
Cost tracking module for LLM usage with Grok pricing.

Tracks cumulative LLM costs per session and enforces $0.50 USD budget limit.

Pricing (Grok):
- Input: $0.03 per 1K tokens
- Output: $0.10 per 1K tokens
- Budget: $0.50 per session (free tier)
"""

import streamlit as st
from typing import Dict, Tuple
from datetime import datetime

# Grok pricing constants (in USD)
GROK_INPUT_COST_PER_1K = 0.03  # $0.03 per 1K input tokens
GROK_OUTPUT_COST_PER_1K = 0.10  # $0.10 per 1K output tokens
FREE_BUDGET_USD = 0.50  # $0.50 free budget per session
WARNING_THRESHOLD = 0.80  # Warn at 80% of budget
BLOCK_THRESHOLD = 1.00  # Block at 100% of budget


def get_cost_key() -> str:
    """Get the session state key for cost tracking."""
    return "llm_cost_tracker"


def initialize_cost_tracker() -> None:
    """Initialize cost tracker in session state if not present."""
    if get_cost_key() not in st.session_state:
        st.session_state[get_cost_key()] = {
            "total_cost_usd": 0.0,
            "queries_count": 0,
            "queries": [],  # List of {"timestamp", "prompt_tokens", "completion_tokens", "cost_usd"}
            "blocked": False,
        }


def calculate_query_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate cost for a single query using Grok pricing.
    
    Args:
        prompt_tokens: Number of tokens in the prompt/input
        completion_tokens: Number of tokens in the completion/output
    
    Returns:
        Cost in USD
    """
    input_cost = (prompt_tokens / 1000) * GROK_INPUT_COST_PER_1K
    output_cost = (completion_tokens / 1000) * GROK_OUTPUT_COST_PER_1K
    return input_cost + output_cost


def track_query_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Track a query cost and add to session total.
    
    Args:
        prompt_tokens: Number of tokens in the prompt/input
        completion_tokens: Number of tokens in the completion/output
    
    Returns:
        New total cost in USD
    """
    initialize_cost_tracker()
    
    query_cost = calculate_query_cost(prompt_tokens, completion_tokens)
    tracker = st.session_state[get_cost_key()]
    
    tracker["total_cost_usd"] += query_cost
    tracker["queries_count"] += 1
    tracker["queries"].append({
        "timestamp": datetime.now().isoformat(),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": query_cost,
    })
    
    # Check if budget exceeded
    if tracker["total_cost_usd"] >= FREE_BUDGET_USD:
        tracker["blocked"] = True
    
    return tracker["total_cost_usd"]


def get_session_cost() -> float:
    """Get total cost spent in current session."""
    initialize_cost_tracker()
    return st.session_state[get_cost_key()]["total_cost_usd"]


def get_remaining_budget() -> float:
    """Get remaining budget in USD."""
    return max(0, FREE_BUDGET_USD - get_session_cost())


def get_budget_percentage() -> float:
    """Get percentage of budget used (0-100)."""
    cost = get_session_cost()
    return min(100, (cost / FREE_BUDGET_USD) * 100)


def should_warn() -> bool:
    """Check if warning should be shown (80% of budget used)."""
    return get_budget_percentage() >= (WARNING_THRESHOLD * 100)


def is_blocked() -> bool:
    """Check if user has exceeded budget and should be blocked."""
    initialize_cost_tracker()
    return st.session_state[get_cost_key()]["blocked"]


def get_query_count() -> int:
    """Get number of queries made in this session."""
    initialize_cost_tracker()
    return st.session_state[get_cost_key()]["queries_count"]


def get_cost_details() -> Dict:
    """Get detailed cost breakdown for this session."""
    initialize_cost_tracker()
    tracker = st.session_state[get_cost_key()]
    
    return {
        "total_cost_usd": tracker["total_cost_usd"],
        "remaining_budget_usd": get_remaining_budget(),
        "budget_percentage": get_budget_percentage(),
        "queries_count": tracker["queries_count"],
        "queries": tracker["queries"],
        "is_blocked": tracker["blocked"],
    }


def get_cost_badge() -> str:
    """Get formatted cost badge for display (percentage only)."""
    percentage = get_budget_percentage()
    
    if percentage < 80:
        # Green - all good
        emoji = "💚"
    elif percentage < 100:
        # Yellow - warning
        emoji = "⚠️"
    else:
        # Red - blocked
        emoji = "🛑"
    
    return f"{emoji} **Cost: {percentage:.0f}%**"


def reset_cost_tracker() -> None:
    """Reset cost tracker (new session or manual reset)."""
    st.session_state[get_cost_key()] = {
        "total_cost_usd": 0.0,
        "queries_count": 0,
        "queries": [],
        "blocked": False,
    }


def export_cost_data() -> Dict:
    """Export cost tracking data for GDPR compliance."""
    return get_cost_details()
