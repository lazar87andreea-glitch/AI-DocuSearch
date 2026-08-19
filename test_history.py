#!/usr/bin/env python
"""Test script for history tracking feature."""

import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.history_manager import HistoryManager


def test_basic_history():
    """Test basic history add and load."""
    print("\n[TEST 1] Basic history add and load")
    
    manager = HistoryManager("test_session_1")
    
    # Add a sample question
    metrics = {
        "total_seconds": 2.5,
        "retrieval_seconds": 1.2,
        "generation_seconds": 1.3,
        "chunk_count": 3,
        "prompt_tokens": 450,
        "completion_tokens": 120,
        "total_tokens": 570,
        "temperature": 0.2,
    }
    
    manager.add_question(
        question="What are the contract dates?",
        answer="The contract runs from January 1, 2026 to December 31, 2027.",
        mode="RAG",
        metrics_dict=metrics,
        document_name="contract.pdf"
    )
    
    # Load history
    history = manager.load_session_history()
    
    assert len(history) == 1, f"Expected 1 entry, got {len(history)}"
    assert history[0]["question"] == "What are the contract dates?"
    assert history[0]["mode"] == "RAG"
    assert history[0]["document_name"] == "contract.pdf"
    assert history[0]["metrics"]["total_tokens"] == 570
    
    print("✓ PASSED: History add and load")


def test_multiple_entries():
    """Test adding multiple entries."""
    print("\n[TEST 2] Multiple entries for same session")
    
    manager = HistoryManager("test_session_2")
    
    # Add three questions
    for i in range(3):
        manager.add_question(
            question=f"Question {i+1}?",
            answer=f"Answer {i+1}",
            mode=["RAG", "Direct LLM", "Hybrid"][i % 3],
            metrics_dict={"total_seconds": 1.0 + i, "total_tokens": 100 + i*10},
            document_name="sample.pdf"
        )
    
    history = manager.load_session_history()
    assert len(history) == 3, f"Expected 3 entries, got {len(history)}"
    
    # Should be sorted by timestamp (newest first)
    assert history[0]["question"] == "Question 3?"
    assert history[2]["question"] == "Question 1?"
    
    print("✓ PASSED: Multiple entries")


def test_document_filtering():
    """Test get_recent_questions with document filtering."""
    print("\n[TEST 3] Document filtering")
    
    manager = HistoryManager("test_session_3")
    
    # Add questions for different documents
    manager.add_question("Q1", "A1", "RAG", {"total_seconds": 1.0}, "doc1.pdf")
    manager.add_question("Q2", "A2", "Direct LLM", {"total_seconds": 1.0}, "doc2.pdf")
    manager.add_question("Q3", "A3", "RAG", {"total_seconds": 1.0}, "doc1.pdf")
    
    # Filter by document
    doc1_history = manager.get_recent_questions(document_name="doc1.pdf", limit=10)
    assert len(doc1_history) == 2, f"Expected 2 entries for doc1.pdf, got {len(doc1_history)}"
    
    doc2_history = manager.get_recent_questions(document_name="doc2.pdf", limit=10)
    assert len(doc2_history) == 1, f"Expected 1 entry for doc2.pdf, got {len(doc2_history)}"
    
    print("✓ PASSED: Document filtering")


def test_limit():
    """Test get_recent_questions limit parameter."""
    print("\n[TEST 4] Limit parameter")
    
    manager = HistoryManager("test_session_4")
    
    # Add 15 questions
    for i in range(15):
        manager.add_question(
            question=f"Q{i}",
            answer=f"A{i}",
            mode="RAG",
            metrics_dict={"total_seconds": 1.0},
            document_name="sample.pdf"
        )
    
    # Test limit=5
    recent = manager.get_recent_questions(limit=5)
    assert len(recent) == 5, f"Expected 5 entries with limit=5, got {len(recent)}"
    
    # Most recent should be Q14
    assert recent[0]["question"] == "Q14"
    
    print("✓ PASSED: Limit parameter")


def test_multi_session_isolation():
    """Test that different sessions have separate histories."""
    print("\n[TEST 5] Multi-session isolation")
    
    manager1 = HistoryManager("session_A")
    manager2 = HistoryManager("session_B")
    
    # Add to session A
    manager1.add_question("Q1", "A1", "RAG", {"total_seconds": 1.0}, "doc.pdf")
    
    # Add to session B
    manager2.add_question("Q2", "A2", "Direct LLM", {"total_seconds": 1.0}, "doc.pdf")
    
    # Check isolation
    hist_a = manager1.load_session_history()
    hist_b = manager2.load_session_history()
    
    assert len(hist_a) == 1, f"Session A should have 1 entry, got {len(hist_a)}"
    assert len(hist_b) == 1, f"Session B should have 1 entry, got {len(hist_b)}"
    assert hist_a[0]["question"] == "Q1"
    assert hist_b[0]["question"] == "Q2"
    
    print("✓ PASSED: Multi-session isolation")


def test_data_structure():
    """Test JSON structure is correct."""
    print("\n[TEST 6] JSON data structure")
    
    manager = HistoryManager("test_session_6")
    
    manager.add_question(
        question="Test question",
        answer="Test answer",
        mode="Hybrid",
        metrics_dict={
            "total_seconds": 3.5,
            "retrieval_seconds": 2.0,
            "generation_seconds": 1.5,
            "chunk_count": 5,
            "prompt_tokens": 500,
            "completion_tokens": 150,
            "total_tokens": 650,
            "temperature": 0.3,
        },
        document_name="test.pdf"
    )
    
    # Read JSON directly
    history_file = Path("history") / f"user_test_session_6.json"
    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert len(data) == 1
    entry = data[0]
    
    # Check structure
    assert "timestamp" in entry
    assert "question" in entry
    assert "answer" in entry
    assert "mode" in entry
    assert "document_name" in entry
    assert "metrics" in entry
    
    # Check metrics
    assert entry["metrics"]["total_tokens"] == 650
    assert entry["metrics"]["temperature"] == 0.3
    
    # Check timestamp format (ISO 8601)
    try:
        datetime.fromisoformat(entry["timestamp"])
    except ValueError:
        raise AssertionError(f"Invalid timestamp format: {entry['timestamp']}")
    
    print("✓ PASSED: JSON data structure")


def test_cleanup():
    """Test cleanup of old sessions."""
    print("\n[TEST 7] Cleanup old sessions")
    
    # Create a session with old timestamp
    old_manager = HistoryManager("test_old_session")
    old_manager.add_question("Old Q", "Old A", "RAG", {"total_seconds": 1.0}, "old.pdf")
    
    # Manually set old timestamp in JSON
    history_file = Path("history") / "user_test_old_session.json"
    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    old_time = (datetime.now() - timedelta(days=40)).isoformat()
    data[0]["timestamp"] = old_time
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    # Run cleanup with 30-day retention
    HistoryManager.cleanup_old_sessions(retention_days=30)
    
    # Old session should be deleted
    assert not history_file.exists(), "Old session file should have been deleted"
    
    print("✓ PASSED: Cleanup old sessions")


def main():
    """Run all tests."""
    print("=" * 60)
    print("History Tracking Feature Tests")
    print("=" * 60)
    
    try:
        test_basic_history()
        test_multiple_entries()
        test_document_filtering()
        test_limit()
        test_multi_session_isolation()
        test_data_structure()
        test_cleanup()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
