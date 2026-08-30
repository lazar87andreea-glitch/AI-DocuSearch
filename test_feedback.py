#!/usr/bin/env python3
"""
Test suite for feedback collection functionality

Run with: python test_feedback.py
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.feedback_manager import FeedbackManager
from src.langsmith_feedback import submit_langsmith_feedback


def cleanup_test_session(session_id: str):
    """Clean up test feedback files"""
    feedback_file = os.path.join("feedback", f"user_{session_id}.json")
    if os.path.exists(feedback_file):
        os.remove(feedback_file)


def test_add_feedback():
    """Test adding feedback entries"""
    session_id = "test_session_001"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    manager.add_feedback(
        answer_id="test_001",
        rating=True,
        question="What is this document about?",
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
    assert feedback[0]["rating"] is True
    assert feedback[0]["comment"] == "Great answer!"
    assert feedback[0]["answer_id"] == "test_001"
    print("✅ test_add_feedback passed")
    
    cleanup_test_session(session_id)


def test_multiple_feedbacks():
    """Test adding multiple feedback entries"""
    session_id = "test_session_002"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("ans_2", True, "Q2", "doc.pdf", "Good", "answer_rating", "RAG", 150, 2, 1.0)
    manager.add_feedback("ans_3", False, "Q3", "doc.pdf", "Bad", "answer_rating", "RAG", 80, 2, 1.0)

    feedback = manager.load_feedback()
    assert len(feedback) == 3
    print("✅ test_multiple_feedbacks passed")
    
    cleanup_test_session(session_id)


def test_feedback_summary():
    """Test feedback aggregation and summary"""
    session_id = "test_session_003"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    # Add various feedback entries
    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("ans_2", True, "Q2", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("ans_3", False, "Q3", "doc.pdf", "Bad", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback(
        "req_001", None, "N/A", "N/A", "Add export to PDF", 
        "feature_request", "N/A", 0, 0, 0.0
    )
    manager.add_feedback(
        "bug_001", None, "N/A", "N/A", "OCR fails on scanned PDFs",
        "bug_report", "N/A", 0, 0, 0.0
    )

    summary = manager.get_feedback_summary()
    assert summary["positive_rating_count"] == 2
    assert summary["negative_rating_count"] == 1
    assert abs(summary["positive_percentage"] - 66.67) < 1
    assert summary["feature_requests"] == 1
    assert summary["bug_reports"] == 1
    assert summary["total_responses"] == 5
    print("✅ test_feedback_summary passed")
    
    cleanup_test_session(session_id)


def test_get_feedback_by_type():
    """Test filtering feedback by type"""
    session_id = "test_session_004"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("req_001", None, "N/A", "N/A", "Add dark mode", "feature_request", "N/A", 0, 0, 0.0)
    manager.add_feedback("bug_001", None, "N/A", "N/A", "Slow on large files", "bug_report", "N/A", 0, 0, 0.0)

    ratings = manager.get_feedback_by_type("answer_rating")
    features = manager.get_feedback_by_type("feature_request")
    bugs = manager.get_feedback_by_type("bug_report")

    assert len(ratings) == 1
    assert len(features) == 1
    assert len(bugs) == 1
    print("✅ test_get_feedback_by_type passed")
    
    cleanup_test_session(session_id)


def test_update_feedback_rating():
    """Test updating an existing feedback entry"""
    session_id = "test_session_005"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    
    # Verify initial rating
    feedback = manager.load_feedback()
    assert feedback[0]["rating"] is True

    # Update rating
    manager.update_feedback_rating("ans_1", False)
    
    # Verify updated rating
    feedback = manager.load_feedback()
    assert feedback[0]["rating"] is False
    print("✅ test_update_feedback_rating passed")
    
    cleanup_test_session(session_id)


def test_export_feedback():
    """Test exporting feedback to file"""
    session_id = "test_session_006"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)

    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", "Great", "answer_rating", "RAG", 100, 2, 1.0)
    manager.add_feedback("req_001", None, "N/A", "N/A", "Feature X", "feature_request", "N/A", 0, 0, 0.0)

    export_file = manager.export_feedback()
    
    # Verify export file exists and contains correct data
    assert os.path.exists(export_file)
    with open(export_file, 'r') as f:
        exported_data = json.load(f)
    assert len(exported_data) == 2
    
    # Clean up
    os.remove(export_file)
    cleanup_test_session(session_id)
    print("✅ test_export_feedback passed")


def test_feedback_comment_truncation():
    """Test that long comments are truncated to 500 chars"""
    session_id = "test_session_007"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)
    
    long_comment = "x" * 1000
    manager.add_feedback("ans_1", True, "Q1", "doc.pdf", long_comment, "answer_rating", "RAG", 100, 2, 1.0)
    
    feedback = manager.load_feedback()
    assert len(feedback[0]["comment"]) == 500
    print("✅ test_feedback_comment_truncation passed")
    
    cleanup_test_session(session_id)


def test_feedback_file_persistence():
    """Test that feedback persists across sessions"""
    session_id = "test_session_008"
    cleanup_test_session(session_id)
    
    # First session: add feedback
    manager1 = FeedbackManager(session_id)
    manager1.add_feedback("ans_1", True, "Q1", "doc.pdf", "Good", "answer_rating", "RAG", 100, 2, 1.0)
    
    # Second session: load feedback
    manager2 = FeedbackManager(session_id)
    feedback = manager2.load_feedback()
    
    assert len(feedback) == 1
    assert feedback[0]["answer_id"] == "ans_1"
    print("✅ test_feedback_file_persistence passed")
    
    cleanup_test_session(session_id)


def test_empty_feedback_file():
    """Test behavior with empty feedback directory"""
    session_id = "test_session_empty"
    cleanup_test_session(session_id)
    
    manager = FeedbackManager(session_id)
    feedback = manager.load_feedback()
    summary = manager.get_feedback_summary()
    
    assert feedback == []
    assert summary["total_responses"] == 0
    assert summary["positive_percentage"] == 0.0
    print("✅ test_empty_feedback_file passed")
    
    cleanup_test_session(session_id)


def test_langsmith_feedback_delivery():
    """Test that a rating is linked to its LangSmith run without a network call."""
    client = Mock()
    environment = {
        "LANGSMITH_API_KEY": "test-key",
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_FEEDBACK_ENABLED": "true",
    }

    with patch.dict(os.environ, environment, clear=True), patch(
        "langsmith.Client", return_value=client
    ):
        delivered = submit_langsmith_feedback(
            "11111111-1111-4111-8111-111111111111", False
        )

    assert delivered is True
    client.create_feedback.assert_called_once_with(
        run_id="11111111-1111-4111-8111-111111111111",
        key="user_rating",
        score=0,
        comment=None,
        source_info={"source": "streamlit_feedback"},
    )
    print("✅ test_langsmith_feedback_delivery passed")


def test_langsmith_feedback_disabled():
    """Test that delivery is skipped when the operator disables it."""
    environment = {
        "LANGSMITH_API_KEY": "test-key",
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_FEEDBACK_ENABLED": "false",
    }

    with patch.dict(os.environ, environment, clear=True), patch(
        "langsmith.Client"
    ) as client_class:
        delivered = submit_langsmith_feedback(
            "11111111-1111-4111-8111-111111111111", True
        )

    assert delivered is False
    client_class.assert_not_called()
    print("✅ test_langsmith_feedback_disabled passed")


def test_streamlit_feedback_buttons():
    """Test that both chat feedback buttons persist complete rating records."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file("web_app.py", default_timeout=30)
    app.session_state["gdpr_consent_given"] = True
    app.run()

    manager = app.session_state["feedback_manager"]
    feedback_path = Path(manager.feedback_file)
    if feedback_path.exists():
        feedback_path.unlink()

    history_entry = {
        "timestamp": "2026-08-30T12:30:00",
        "question": "What is covered?",
        "answer": "The document covers testing.",
        "mode": "Hybrid (RAG)",
        "document_name": "feedback-test.txt",
        "metrics": {"chunk_count": 3, "retrieval_seconds": 0.75},
    }

    try:
        app.session_state["uploaded_name"] = "feedback-test.txt"
        app.session_state["document_text"] = "test document"
        app.session_state["file_path"] = "unused-test-path.txt"
        app.session_state["chat_history"] = [history_entry]
        app.run()

        next(button for button in app.button if button.label == "👍 Helpful").click().run()
        next(button for button in app.button if button.label == "👎 Not helpful").click().run()

        feedback = manager.load_feedback()
        assert len(app.exception) == 0
        assert len(feedback) == 2
        assert sorted(item["rating"] for item in feedback) == [False, True]
        assert all(item["document_name"] == "feedback-test.txt" for item in feedback)
        assert all(item["answer_length"] == len(history_entry["answer"]) for item in feedback)
        assert all(item["chunk_count"] == 3 for item in feedback)
        assert all(item["retrieval_seconds"] == 0.75 for item in feedback)
        print("✅ test_streamlit_feedback_buttons passed")
    finally:
        if feedback_path.exists():
            feedback_path.unlink()


def run_all_tests():
    """Run all tests"""
    print("Running Feedback Collection Tests...\n")
    
    test_functions = [
        test_add_feedback,
        test_multiple_feedbacks,
        test_feedback_summary,
        test_get_feedback_by_type,
        test_update_feedback_rating,
        test_export_feedback,
        test_feedback_comment_truncation,
        test_feedback_file_persistence,
        test_empty_feedback_file,
        test_langsmith_feedback_delivery,
        test_langsmith_feedback_disabled,
        test_streamlit_feedback_buttons,
    ]
    
    for test_func in test_functions:
        try:
            test_func()
        except AssertionError as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            return False
    
    print("\n✅ All feedback tests passed!")
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
