"""
Feedback Collection System for AI DocuSearch

Handles user feedback on answer quality, feature requests, and bug reports.
Stores feedback per-session with optional analytics and export capabilities.
"""

import json
import os
from typing import Any, List, Dict, Optional
from datetime import datetime, timezone


class FeedbackManager:
    """Manages user feedback collection and storage (per-session isolation)"""

    def __init__(self, session_id: str):
        """
        Initialize with unique session ID
        
        Args:
            session_id: Unique identifier for this user session
        """
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
        rating: Optional[bool] = None,
        question: str = "N/A",
        document_name: str = "N/A",
        comment: Optional[str] = None,
        feedback_type: str = "answer_rating",
        mode: str = "Hybrid",
        answer_length: int = 0,
        chunk_count: int = 0,
        retrieval_seconds: float = 0.0,
    ) -> None:
        """
        Append feedback entry to session's JSON file with ISO 8601 timestamp

        Args:
            answer_id: Unique identifier for this answer (e.g., hash of timestamp + question)
            rating: True for positive, False for negative (None for non-rating feedback)
            question: The question that was asked
            document_name: Name of the document being queried
            comment: Optional text feedback (max 500 chars)
            feedback_type: "answer_rating", "feature_request", "bug_report", or "general_comment"
            mode: RAG, Direct LLM, or Hybrid
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
            "comment": (comment or "")[:500],  # Cap at 500 chars
            "feedback_type": feedback_type,
            "mode": mode,
            "answer_length": answer_length,
            "chunk_count": chunk_count,
            "retrieval_seconds": round(retrieval_seconds, 2),
        }

        feedback_data.append(entry)
        self._save_feedback(feedback_data)

    def load_feedback(self) -> List[Dict[str, Any]]:
        """
        Load all feedback entries from disk, sorted newest first

        Returns:
            List of feedback entries, newest first
        """
        if not os.path.exists(self.feedback_file):
            return []

        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Sort by timestamp descending (newest first)
            return sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
        except (json.JSONDecodeError, IOError):
            return []

    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Get aggregate statistics for this session's feedback

        Returns:
            Dictionary with summary metrics
        """
        feedback = self.load_feedback()

        if not feedback:
            return {
                "total_responses": 0,
                "positive_rating_count": 0,
                "negative_rating_count": 0,
                "positive_percentage": 0.0,
                "feature_requests": 0,
                "bug_reports": 0,
                "general_comments": 0,
                "average_answer_length": 0,
            }

        # Count ratings
        positive = sum(
            1
            for f in feedback
            if f.get("feedback_type") == "answer_rating" and f.get("rating") is True
        )
        negative = sum(
            1
            for f in feedback
            if f.get("feedback_type") == "answer_rating" and f.get("rating") is False
        )
        total_ratings = positive + negative

        # Count feedback types
        feature_requests = sum(
            1 for f in feedback if f.get("feedback_type") == "feature_request"
        )
        bug_reports = sum(1 for f in feedback if f.get("feedback_type") == "bug_report")
        general_comments = sum(
            1 for f in feedback if f.get("feedback_type") == "general_comment"
        )

        # Calculate average answer length
        answer_lengths = [f.get("answer_length", 0) for f in feedback if f.get("feedback_type") == "answer_rating"]
        average_answer_length = (
            sum(answer_lengths) // len(answer_lengths) if answer_lengths else 0
        )

        return {
            "total_responses": len(feedback),
            "positive_rating_count": positive,
            "negative_rating_count": negative,
            "positive_percentage": (
                (positive / total_ratings * 100) if total_ratings > 0 else 0.0
            ),
            "feature_requests": feature_requests,
            "bug_reports": bug_reports,
            "general_comments": general_comments,
            "average_answer_length": average_answer_length,
        }

    def get_feedback_by_type(self, feedback_type: str) -> List[Dict[str, Any]]:
        """
        Get all feedback entries of a specific type

        Args:
            feedback_type: Type to filter by

        Returns:
            List of matching feedback entries
        """
        feedback = self.load_feedback()
        return [f for f in feedback if f.get("feedback_type") == feedback_type]

    def update_feedback_rating(self, answer_id: str, rating: bool) -> None:
        """
        Update an existing feedback entry's rating

        Args:
            answer_id: ID of the answer to update
            rating: New rating value
        """
        feedback = self.load_feedback()

        for entry in feedback:
            if entry.get("answer_id") == answer_id:
                entry["rating"] = rating
                break

        self._save_feedback(feedback)

    def _save_feedback(self, feedback_data: List[Dict[str, Any]]) -> None:
        """
        Write feedback data to JSON file

        Args:
            feedback_data: List of feedback entries to save
        """
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def cleanup_old_feedback(retention_days: int = 90) -> None:
        """
        Delete old feedback files (90-day retention by default)

        Args:
            retention_days: Days to retain feedback (default: 90)
        """
        if not os.path.exists("feedback"):
            return

        now = datetime.now(timezone.utc)
        retention_seconds = retention_days * 24 * 60 * 60

        for filename in os.listdir("feedback"):
            file_path = os.path.join("feedback", filename)
            if os.path.isfile(file_path):
                try:
                    mtime = os.path.getmtime(file_path)
                    file_age_seconds = now.timestamp() - mtime

                    if file_age_seconds > retention_seconds:
                        os.remove(file_path)
                        print(f"Cleaned up old feedback file: {filename}")
                except OSError:
                    pass

    def export_feedback(self, output_file: Optional[str] = None) -> str:
        """
        Export session feedback to a JSON file

        Args:
            output_file: Path to export file (default: feedback_export_{session_id}.json)

        Returns:
            Path to exported file
        """
        if output_file is None:
            output_file = f"feedback_export_{self.session_id}.json"

        feedback = self.load_feedback()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=2, ensure_ascii=False)

        return output_file
