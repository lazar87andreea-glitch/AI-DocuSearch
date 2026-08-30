"""Regression tests for live, simulated, and failed LLM response states."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.ai_query import generate_answer_with_meta
from src.pipeline import answer_question


def test_live_response_is_marked_successful() -> None:
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "Live answer"}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 3,
            "total_tokens": 13,
        },
    }
    provider_config = {
        "LLM_API_KEY": "test-key",
        "LLM_API_BASE": "https://provider.invalid/v1",
        "LLM_MODEL": "test-model",
    }

    with (
        patch.dict(os.environ, provider_config, clear=True),
        patch("src.ai_query._get_langsmith_client", return_value=None),
        patch("requests.post", return_value=response),
    ):
        result = generate_answer_with_meta("Test prompt")

    assert result["response_status"] == "success"
    assert result["answer"] == "Live answer"
    assert result["error_type"] is None
    assert result["total_tokens"] == 13


def test_provider_failure_is_not_returned_as_an_answer() -> None:
    provider_config = {
        "LLM_API_KEY": "test-key",
        "LLM_API_BASE": "https://provider.invalid/v1",
        "LLM_MODEL": "test-model",
    }

    with (
        patch.dict(os.environ, provider_config, clear=True),
        patch("src.ai_query._get_langsmith_client", return_value=None),
        patch("requests.post", side_effect=RuntimeError("provider unavailable")),
    ):
        result = generate_answer_with_meta("Test prompt")

    assert result["response_status"] == "error"
    assert result["answer"] == ""
    assert result["error_type"] == "RuntimeError"
    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0
    assert result["total_tokens"] == 0


def test_missing_configuration_is_an_explicit_simulation() -> None:
    with patch.dict(os.environ, {}, clear=True):
        result = generate_answer_with_meta("Test prompt")

    assert result["response_status"] == "simulated"
    assert result["answer"].startswith("[SIMULATED ANSWER]")
    assert result["error_type"] == "configuration_missing"


def test_pipeline_propagates_provider_failure_state() -> None:
    failed_meta: dict[str, Any] = {
        "answer": "",
        "elapsed_seconds": 0.1,
        "response_status": "error",
        "error_type": "Timeout",
        "error_message": "request timed out",
        "used_live_api": False,
        "langsmith_run_id": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_tokens": False,
        "temperature": 0.2,
    }

    with patch("src.pipeline.generate_answer_with_meta", return_value=failed_meta):
        result = answer_question(
            {"index": None, "chunks": ["Document context"], "lite_mode": True},
            "Question?",
        )

    assert result["response_status"] == "error"
    assert result["raw_answer"] == ""
    assert result["error_type"] == "Timeout"
    assert result["total_tokens"] == 0


def test_streamlit_provider_failure_is_not_saved() -> None:
    app = AppTest.from_file("web_app.py", default_timeout=30)
    app.session_state["gdpr_consent_given"] = True
    app.run()

    history_manager = app.session_state["history_manager"]
    history_path = Path(history_manager.history_file)
    history_path.unlink(missing_ok=True)
    app.session_state["uploaded_name"] = "provider-failure-test.txt"
    app.session_state["document_text"] = "Document context"
    app.session_state["rag_pipeline"] = {
        "index": None,
        "chunks": ["Document context"],
        "lite_mode": True,
    }
    app.session_state["chat_history"] = []

    provider_config = {
        "LLM_API_KEY": "test-key",
        "LLM_API_BASE": "https://provider.invalid/v1",
        "LLM_MODEL": "test-model",
    }

    try:
        app.run()
        with (
            patch.dict(os.environ, provider_config, clear=False),
            patch("src.ai_query._get_langsmith_client", return_value=None),
            patch("requests.post", side_effect=RuntimeError("provider unavailable")),
        ):
            app.chat_input[0].set_value("Question?").run()

        assert not app.exception
        assert app.session_state["chat_history"] == []
        assert not history_path.exists()
        assert any("No answer was saved" in error.value for error in app.error)
    finally:
        history_path.unlink(missing_ok=True)


def test_streamlit_budget_limit_blocks_chat_input() -> None:
    app = AppTest.from_file("web_app.py", default_timeout=30)
    app.session_state["gdpr_consent_given"] = True
    app.run()

    feedback_links = app.get("link_button")
    assert any(link.label == "Share feedback" for link in feedback_links)

    app.session_state["llm_cost_tracker"] = {
        "total_cost_usd": 0.50,
        "queries_count": 1,
        "queries": [],
        "blocked": True,
    }
    app.run()

    assert not app.exception
    assert any("Free testing trial complete" in error.value for error in app.error)
    feedback_links = app.get("link_button")
    assert len(feedback_links) == 1
    assert feedback_links[0].label == "Share feedback"
    assert "docs.google.com/forms" in feedback_links[0].url
    assert len(app.chat_input) == 0


if __name__ == "__main__":
    test_live_response_is_marked_successful()
    test_provider_failure_is_not_returned_as_an_answer()
    test_missing_configuration_is_an_explicit_simulation()
    test_pipeline_propagates_provider_failure_state()
    test_streamlit_provider_failure_is_not_saved()
    test_streamlit_budget_limit_blocks_chat_input()
    print("All AI query response-state tests passed.")