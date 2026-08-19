"""
History CLI tool for inspection, analytics, and batch operations on session history.

Usage:
    python history_cli.py list [--session SESSION_ID] [--document DOCUMENT_NAME]
    python history_cli.py show --session SESSION_ID --index INDEX
    python history_cli.py export [--output OUTPUT_FILE] [--session SESSION_ID] [--document DOCUMENT_NAME]
    python history_cli.py cleanup [--days RETENTION_DAYS]
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from src.history_manager import HistoryManager


def cmd_list(args) -> None:
    """List questions from history files with optional filtering."""
    history_dir = "history"
    
    if not os.path.exists(history_dir):
        print("No history directory found.")
        return
    
    session_files = sorted([f for f in os.listdir(history_dir) if f.startswith("user_")])
    
    if not session_files:
        print("No session history files found.")
        return
    
    total_questions = 0
    
    for filename in session_files:
        session_id = filename.replace("user_", "").replace(".json", "")
        filepath = os.path.join(history_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue
        
        # Filter by session if specified
        if args.session and session_id != args.session:
            continue
        
        # Filter by document if specified
        if args.document:
            history = [h for h in history if h.get("document_name") == args.document]
        
        if not history:
            continue
        
        print(f"\n📁 Session: {session_id}")
        print(f"   Questions: {len(history)}")
        total_questions += len(history)
        
        for i, entry in enumerate(history):
            timestamp = entry.get("timestamp", "unknown")[:19]
            question = entry.get("question", "")[:60]
            mode = entry.get("mode", "")
            document = entry.get("document_name", "")
            
            print(f"   [{i}] {timestamp} [{mode}] {document}")
            print(f"       Q: {question}...")
    
    print(f"\n✓ Total: {total_questions} questions")


def cmd_show(args) -> None:
    """Show full details of a specific question."""
    if not args.session or args.index is None:
        print("Error: --session and --index are required")
        return
    
    filepath = os.path.join("history", f"user_{args.session}.json")
    
    if not os.path.exists(filepath):
        print(f"Session file not found: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading history: {e}")
        return
    
    if args.index < 0 or args.index >= len(history):
        print(f"Index out of range. Session has {len(history)} questions.")
        return
    
    entry = history[args.index]
    
    print(f"\n{'='*80}")
    print(f"Session ID: {args.session}")
    print(f"Entry Index: {args.index}")
    print(f"{'='*80}")
    print(f"Timestamp:  {entry.get('timestamp', 'unknown')}")
    print(f"Mode:       {entry.get('mode', 'unknown')}")
    print(f"Document:   {entry.get('document_name', 'unknown')}")
    print(f"\nQuestion:")
    print(f"{entry.get('question', '(none)')}\n")
    print(f"Answer:")
    print(f"{entry.get('answer', '(none)')}\n")
    print(f"Metrics:")
    metrics = entry.get('metrics', {})
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    print(f"{'='*80}\n")


def cmd_export(args) -> None:
    """Export history to CSV file."""
    history_dir = "history"
    
    if not os.path.exists(history_dir):
        print("No history directory found.")
        return
    
    output_file = args.output or "history_export.csv"
    session_files = sorted([f for f in os.listdir(history_dir) if f.startswith("user_")])
    
    all_rows = []
    
    for filename in session_files:
        session_id = filename.replace("user_", "").replace(".json", "")
        filepath = os.path.join(history_dir, filename)
        
        # Filter by session if specified
        if args.session and session_id != args.session:
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue
        
        # Filter by document if specified
        if args.document:
            history = [h for h in history if h.get("document_name") == args.document]
        
        for entry in history:
            metrics = entry.get('metrics', {})
            row = {
                'timestamp': entry.get('timestamp', ''),
                'session_id': session_id,
                'document_name': entry.get('document_name', ''),
                'mode': entry.get('mode', ''),
                'question': entry.get('question', ''),
                'answer': entry.get('answer', ''),
                'total_seconds': metrics.get('total_seconds', ''),
                'retrieval_seconds': metrics.get('retrieval_seconds', ''),
                'generation_seconds': metrics.get('generation_seconds', ''),
                'chunk_count': metrics.get('chunk_count', ''),
                'prompt_tokens': metrics.get('prompt_tokens', ''),
                'completion_tokens': metrics.get('completion_tokens', ''),
                'total_tokens': metrics.get('total_tokens', ''),
                'temperature': metrics.get('temperature', ''),
            }
            all_rows.append(row)
    
    if not all_rows:
        print("No history entries found matching the criteria.")
        return
    
    # Write CSV
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = all_rows[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"✓ Exported {len(all_rows)} entries to {output_file}")
    except IOError as e:
        print(f"Error writing CSV: {e}")


def cmd_cleanup(args) -> None:
    """Cleanup old session files."""
    retention_days = args.days or 30
    HistoryManager.cleanup_old_sessions(retention_days=retention_days)
    print(f"✓ Cleanup completed (retention: {retention_days} days)")


def main():
    """Parse arguments and dispatch to appropriate command."""
    parser = argparse.ArgumentParser(
        description="History tracking CLI tool for AI-DocuSearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python history_cli.py list
  python history_cli.py list --document contract.pdf
  python history_cli.py show --session abc123 --index 0
  python history_cli.py export --output history.csv
  python history_cli.py cleanup --days 30
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List history entries')
    list_parser.add_argument('--session', help='Filter by session ID')
    list_parser.add_argument('--document', help='Filter by document name')
    list_parser.set_defaults(func=cmd_list)
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show full details of an entry')
    show_parser.add_argument('--session', required=True, help='Session ID')
    show_parser.add_argument('--index', type=int, required=True, help='Entry index')
    show_parser.set_defaults(func=cmd_show)
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export history to CSV')
    export_parser.add_argument('--output', default='history_export.csv', help='Output CSV file')
    export_parser.add_argument('--session', help='Filter by session ID')
    export_parser.add_argument('--document', help='Filter by document name')
    export_parser.set_defaults(func=cmd_export)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old session files')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Retention days (default: 30)')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
