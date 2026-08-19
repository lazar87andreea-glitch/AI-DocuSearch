"""
History tracking module for persisting questions, answers, and metrics per session.

Each browser session maintains its own private history file (user_{session_id}.json)
with automatic cleanup of old sessions. Supports document filtering and analytics.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List


class HistoryManager:
    """Manages per-session question history with document filtering and multi-user isolation."""
    
    def __init__(self, session_id: str):
        """Initialize history manager for a specific session.
        
        Args:
            session_id: Unique identifier for this browser session
        """
        self.session_id = session_id
        self.history_dir = "history"
        self.history_file = os.path.join(self.history_dir, f"user_{session_id}.json")
        
        # Ensure history directory exists
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
    
    def add_question(
        self,
        question: str,
        answer: str,
        mode: str,
        metrics_dict: Dict[str, Any],
        document_name: str
    ) -> None:
        """Log a question+answer pair with complete metrics.
        
        Args:
            question: The user's question
            answer: The LLM's answer
            mode: Query mode (RAG, Direct LLM, or Hybrid)
            metrics_dict: Dict with keys: total_seconds, retrieval_seconds, generation_seconds,
                         chunk_count, prompt_tokens, completion_tokens, total_tokens, temperature
            document_name: Name of the document being queried
        """
        # Load existing history
        history = self._load_json()
        
        # Create new entry with ISO 8601 timestamp
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "mode": mode,
            "document_name": document_name,
            "metrics": metrics_dict
        }
        
        # Append and save
        history.append(entry)
        self._save_json(history)
    
    def load_session_history(self) -> List[Dict[str, Any]]:
        """Load all history entries for this session.
        
        Returns:
            List of history entries, sorted by timestamp (newest first)
        """
        history = self._load_json()
        # Sort by timestamp, newest first
        return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def get_recent_questions(
        self,
        document_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent questions, optionally filtered by document.
        
        Args:
            document_name: If provided, filter to only this document
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries (newest first), up to limit items
        """
        history = self.load_session_history()
        
        # Filter by document if specified
        if document_name:
            history = [h for h in history if h.get("document_name") == document_name]
        
        # Return up to limit items
        return history[:limit]
    
    @staticmethod
    def cleanup_old_sessions(retention_days: int = 30) -> None:
        """Delete session files where all entries are older than retention_days.
        
        Args:
            retention_days: Number of days to retain history files (default 30)
        """
        history_dir = "history"
        if not os.path.exists(history_dir):
            return
        
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        for filename in os.listdir(history_dir):
            if not filename.startswith("user_"):
                continue
            
            filepath = os.path.join(history_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            
            if not history:
                # Empty file, delete it
                try:
                    os.remove(filepath)
                    print(f"[HISTORY] Cleaned up empty session file: {filename}")
                except Exception as e:
                    print(f"[HISTORY] Could not delete {filename}: {e}")
                continue
            
            # Check if most recent entry is older than cutoff
            most_recent = history[0]  # Sorted newest first
            try:
                latest_timestamp = datetime.fromisoformat(most_recent.get("timestamp", ""))
                if latest_timestamp < cutoff_time:
                    os.remove(filepath)
                    print(f"[HISTORY] Cleaned up old session file: {filename}")
            except (ValueError, AttributeError):
                # Invalid timestamp format, skip
                pass
    
    # Private helper methods
    
    def _load_json(self) -> List[Dict[str, Any]]:
        """Load history from JSON file, return empty list if not found."""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_json(self, data: List[Dict[str, Any]]) -> None:
        """Save history to JSON file with proper formatting."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[HISTORY] Could not save history: {e}")
