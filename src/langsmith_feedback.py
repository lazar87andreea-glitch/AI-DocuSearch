import os
import sys
from typing import Optional


def submit_langsmith_feedback(
    run_id: Optional[str], rating: bool, comment: Optional[str] = None
) -> bool:
    """Attach a user rating to a LangSmith run without breaking local feedback."""
    if not run_id:
        return False
    if not os.getenv("LANGSMITH_API_KEY"):
        return False
    if os.getenv("LANGSMITH_TRACING", "").lower() != "true":
        return False
    if os.getenv("LANGSMITH_FEEDBACK_ENABLED", "true").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False

    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=run_id,
            key="user_rating",
            score=1 if rating else 0,
            comment=comment or None,
            source_info={"source": "streamlit_feedback"},
        )
        return True
    except Exception as exc:
        print(
            f"[LANGSMITH] Feedback delivery failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return False