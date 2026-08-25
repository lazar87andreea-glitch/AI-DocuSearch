#!/usr/bin/env python3
"""
Feedback Export and Analytics Tool

Export all user feedback for analysis and generate summary statistics.

Usage:
    python export_feedback.py                    # Export and show stats
    python -c "from export_feedback import print_feedback_stats; print_feedback_stats()"
    python -c "from export_feedback import export_all_feedback; export_all_feedback('report.json')"
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def export_all_feedback(output_file: str = "feedback_export.json") -> None:
    """
    Aggregate feedback from all sessions into a single JSON file
    
    Args:
        output_file: Path to write aggregated feedback
    """
    feedback_dir = Path("feedback")
    all_feedback = []

    if not feedback_dir.exists():
        print(f"❌ No feedback directory found at {feedback_dir}")
        return

    session_count = 0
    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_feedback = json.load(f)
                all_feedback.extend(session_feedback)
                session_count += 1
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error reading {session_file}: {e}")

    if all_feedback:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_feedback, f, indent=2, ensure_ascii=False)
        print(f"✅ Exported {len(all_feedback)} feedback entries from {session_count} sessions")
        print(f"📁 File: {output_file}")
    else:
        print("⚠️  No feedback to export")


def print_feedback_stats() -> None:
    """Print aggregate statistics across all sessions"""

    feedback_dir = Path("feedback")
    all_feedback = []

    if not feedback_dir.exists():
        print("❌ No feedback directory found")
        return

    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                all_feedback.extend(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass

    if not all_feedback:
        print("⚠️  No feedback found")
        return

    # Calculate metrics
    total = len(all_feedback)
    rating_feedback = [
        f for f in all_feedback if f.get("feedback_type") == "answer_rating"
    ]
    positive = sum(1 for f in rating_feedback if f.get("rating") is True)
    negative = sum(1 for f in rating_feedback if f.get("rating") is False)
    neutral = len(rating_feedback) - positive - negative

    features = sum(1 for f in all_feedback if f.get("feedback_type") == "feature_request")
    bugs = sum(1 for f in all_feedback if f.get("feedback_type") == "bug_report")
    general = sum(1 for f in all_feedback if f.get("feedback_type") == "general_comment")

    # Mode analysis
    mode_counts = defaultdict(int)
    for f in rating_feedback:
        mode = f.get("mode", "N/A")
        mode_counts[mode] += 1

    mode_satisfaction = defaultdict(lambda: {"positive": 0, "total": 0})
    for f in rating_feedback:
        mode = f.get("mode", "N/A")
        mode_satisfaction[mode]["total"] += 1
        if f.get("rating") is True:
            mode_satisfaction[mode]["positive"] += 1

    # Document analysis
    doc_counts = defaultdict(int)
    for f in all_feedback:
        if f.get("feedback_type") == "answer_rating":
            doc = f.get("document_name", "N/A")
            doc_counts[doc] += 1

    # Timing analysis
    retrieval_times = [
        f.get("retrieval_seconds", 0)
        for f in rating_feedback
        if f.get("retrieval_seconds", 0) > 0
    ]

    avg_retrieval = (
        sum(retrieval_times) / len(retrieval_times)
        if retrieval_times
        else 0
    )

    # Answer length analysis
    answer_lengths = [f.get("answer_length", 0) for f in rating_feedback]
    avg_answer_length = (
        sum(answer_lengths) / len(answer_lengths) if answer_lengths else 0
    )

    positive_answers = [
        f.get("answer_length", 0)
        for f in rating_feedback
        if f.get("rating") is True
    ]
    negative_answers = [
        f.get("answer_length", 0)
        for f in rating_feedback
        if f.get("rating") is False
    ]
    avg_positive_length = (
        sum(positive_answers) / len(positive_answers) if positive_answers else 0
    )
    avg_negative_length = (
        sum(negative_answers) / len(negative_answers) if negative_answers else 0
    )

    # Print report
    print("\n" + "=" * 70)
    print("📊 AI DocuSearch Feedback Analytics Report".center(70))
    print("=" * 70)

    print("\n📈 OVERALL METRICS")
    print("-" * 70)
    print(f"  Total Feedback Entries:     {total}")
    print(f"  Answer Ratings:             {len(rating_feedback)}")
    print(f"  Feature Requests:           {features}")
    print(f"  Bug Reports:                {bugs}")
    print(f"  General Comments:           {general}")

    print("\n⭐ ANSWER SATISFACTION")
    print("-" * 70)
    satisfaction_pct = (
        (positive / len(rating_feedback) * 100) if rating_feedback else 0
    )
    print(f"  Positive (👍):              {positive} ({satisfaction_pct:.1f}%)")
    print(f"  Negative (👎):              {negative}")
    if neutral > 0:
        print(f"  Neutral (📊):               {neutral}")
    print(f"  Satisfaction Rate:          {satisfaction_pct:.1f}%")

    if satisfaction_pct >= 80:
        sentiment = "🟢 Excellent"
    elif satisfaction_pct >= 60:
        sentiment = "🟡 Good"
    elif satisfaction_pct >= 40:
        sentiment = "🟠 Fair"
    else:
        sentiment = "🔴 Poor"
    print(f"  Overall Sentiment:          {sentiment}")

    print("\n🔧 MODE PERFORMANCE")
    print("-" * 70)
    for mode, stats in sorted(mode_satisfaction.items()):
        if stats["total"] > 0:
            mode_pct = stats["positive"] / stats["total"] * 100
            print(
                f"  {mode:20} {stats['positive']:3}/{stats['total']:3} "
                f"({mode_pct:5.1f}%)"
            )

    print("\n⏱️  PERFORMANCE METRICS")
    print("-" * 70)
    print(f"  Avg Retrieval Time:         {avg_retrieval:.2f}s")
    print(f"  Avg Answer Length:          {avg_answer_length:.0f} chars")
    print(f"  Positive Answers Avg Len:   {avg_positive_length:.0f} chars")
    print(f"  Negative Answers Avg Len:   {avg_negative_length:.0f} chars")

    print("\n📄 TOP DOCUMENTS")
    print("-" * 70)
    for doc, count in sorted(doc_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {doc:30} {count:3} ratings")

    if features > 0:
        print("\n💡 TOP FEATURE REQUESTS (Most Recent)")
        print("-" * 70)
        feature_feedback = [
            f for f in all_feedback if f.get("feedback_type") == "feature_request"
        ]
        for f in sorted(
            feature_feedback, key=lambda x: x.get("timestamp", ""), reverse=True
        )[:5]:
            comment = f.get("comment", "")[:60]
            print(f"  • {comment}")

    if bugs > 0:
        print("\n🐛 TOP BUG REPORTS (Most Recent)")
        print("-" * 70)
        bug_feedback = [
            f for f in all_feedback if f.get("feedback_type") == "bug_report"
        ]
        for f in sorted(
            bug_feedback, key=lambda x: x.get("timestamp", ""), reverse=True
        )[:5]:
            comment = f.get("comment", "")[:60]
            print(f"  • {comment}")

    print("\n" + "=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")


def analyze_feedback_by_mode() -> None:
    """Detailed analysis of feedback by mode (Hybrid with RAG/fallback breakdown)"""

    feedback_dir = Path("feedback")
    all_feedback = []

    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                all_feedback.extend(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass

    if not all_feedback:
        print("⚠️  No feedback found")
        return

    print("\n" + "=" * 70)
    print("🔬 MODE COMPARISON ANALYSIS".center(70))
    print("=" * 70)

    rating_feedback = [
        f for f in all_feedback if f.get("feedback_type") == "answer_rating"
    ]

    modes = set(f.get("mode", "N/A") for f in rating_feedback)

    for mode in sorted(modes):
        mode_data = [f for f in rating_feedback if f.get("mode") == mode]
        positive = sum(1 for f in mode_data if f.get("rating") is True)
        negative = sum(1 for f in mode_data if f.get("rating") is False)
        total = len(mode_data)

        retrieval_times = [f.get("retrieval_seconds", 0) for f in mode_data if f.get("retrieval_seconds", 0) > 0]
        avg_retrieval = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0

        answer_lengths = [f.get("answer_length", 0) for f in mode_data]
        avg_length = sum(answer_lengths) / len(answer_lengths) if answer_lengths else 0

        satisfaction = (positive / total * 100) if total > 0 else 0

        print(f"\n📌 {mode}")
        print(f"  Samples:          {total}")
        print(f"  Satisfaction:     {satisfaction:.1f}% ({positive}👍 / {negative}👎)")
        print(f"  Avg Retrieval:    {avg_retrieval:.2f}s")
        print(f"  Avg Answer Len:   {avg_length:.0f} chars")

    print("\n" + "=" * 70 + "\n")


def export_feedback_csv(output_file: str = "feedback_export.csv") -> None:
    """
    Export feedback to CSV format for spreadsheet analysis
    
    Args:
        output_file: Path to write CSV file
    """
    import csv

    feedback_dir = Path("feedback")
    all_feedback = []

    for session_file in feedback_dir.glob("user_*.json"):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                all_feedback.extend(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass

    if not all_feedback:
        print("⚠️  No feedback to export")
        return

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "feedback_type",
                "rating",
                "question",
                "document_name",
                "comment",
                "mode",
                "answer_length",
                "chunk_count",
                "retrieval_seconds",
            ],
        )
        writer.writeheader()
        for feedback in sorted(all_feedback, key=lambda x: x.get("timestamp", "")):
            writer.writerow(feedback)

    print(f"✅ Exported {len(all_feedback)} entries to CSV")
    print(f"📁 File: {output_file}")


if __name__ == "__main__":
    print("AI DocuSearch Feedback Analytics Tool\n")

    # Export to JSON
    export_all_feedback()

    # Export to CSV
    export_feedback_csv()

    # Print statistics
    print_feedback_stats()

    # Detailed mode analysis
    analyze_feedback_by_mode()
