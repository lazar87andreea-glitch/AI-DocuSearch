#!/usr/bin/env python3
"""Export and summarize LangSmith runs associated with user feedback.

Examples:
    python langsmith_feedback_report.py --project ai-docusearch
    python langsmith_feedback_report.py --project ai-docusearch --score 0 --format csv
    python langsmith_feedback_report.py --project another-project --include-content
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from dotenv import load_dotenv

DEFAULT_FEEDBACK_KEY = "user_rating"
DEFAULT_OUTPUT_STEM = "langsmith_feedback_report"


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date or datetime and normalize it to UTC."""
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def serialize(value: Any) -> Any:
    """Convert LangSmith/Pydantic values into JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return as_utc(value).isoformat() if as_utc(value) else None
    if isinstance(value, dict):
        return {str(key): serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize(item) for item in value]
    if hasattr(value, "model_dump"):
        return serialize(value.model_dump())
    return str(value)


def score_matches(actual: Any, expected: Optional[float]) -> bool:
    if expected is None:
        return True
    if isinstance(actual, bool):
        actual = int(actual)
    try:
        return float(actual) == expected
    except (TypeError, ValueError):
        return False


def feedback_in_range(
    feedback: Any, since: Optional[datetime], until: Optional[datetime]
) -> bool:
    created_at = as_utc(getattr(feedback, "created_at", None))
    if since and (created_at is None or created_at < since):
        return False
    if until and (created_at is None or created_at > until):
        return False
    return True


def chunks(values: Sequence[Any], size: int = 100) -> Iterable[Sequence[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def load_project_runs(client: Any, project: str, run_ids: Sequence[Any]) -> dict[str, Any]:
    """Batch-load runs while using the LangSmith project as an access filter."""
    runs: dict[str, Any] = {}
    for run_id_batch in chunks(run_ids):
        for run in client.list_runs(project_name=project, run_ids=run_id_batch):
            runs[str(run.id)] = run
    return runs


def child_run_record(run: Any, include_content: bool) -> dict[str, Any]:
    record = {
        "run_id": str(run.id),
        "name": run.name,
        "run_type": run.run_type,
        "status": getattr(run, "status", None),
        "error": getattr(run, "error", None),
    }
    if include_content:
        record["inputs"] = serialize(getattr(run, "inputs", None))
        record["outputs"] = serialize(getattr(run, "outputs", None))
    return record


def build_record(
    feedback: Any,
    run: Any,
    project: str,
    include_content: bool,
    child_runs: Optional[list[Any]] = None,
) -> dict[str, Any]:
    start_time = as_utc(getattr(run, "start_time", None))
    end_time = as_utc(getattr(run, "end_time", None))
    latency_seconds = None
    if start_time and end_time:
        latency_seconds = (end_time - start_time).total_seconds()

    extra = getattr(run, "extra", None) or {}
    metadata = extra.get("metadata", {}) if isinstance(extra, dict) else {}
    model = None
    inputs = getattr(run, "inputs", None) or {}
    if isinstance(inputs, dict):
        model = inputs.get("model")
    if not model and isinstance(metadata, dict):
        model = metadata.get("ls_model_name") or metadata.get("model")

    record = {
        "project": project,
        "run_id": str(run.id),
        "trace_id": str(run.trace_id) if getattr(run, "trace_id", None) else None,
        "run_name": run.name,
        "run_type": run.run_type,
        "status": getattr(run, "status", None),
        "error": getattr(run, "error", None),
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "latency_seconds": latency_seconds,
        "prompt_tokens": getattr(run, "prompt_tokens", None),
        "completion_tokens": getattr(run, "completion_tokens", None),
        "total_tokens": getattr(run, "total_tokens", None),
        "total_cost": getattr(run, "total_cost", None),
        "model": model,
        "tags": serialize(getattr(run, "tags", None) or []),
        "metadata": serialize(metadata),
        "feedback_id": str(feedback.id),
        "feedback_key": feedback.key,
        "feedback_score": feedback.score,
        "feedback_value": serialize(getattr(feedback, "value", None)),
        "feedback_comment": getattr(feedback, "comment", None),
        "feedback_created_at": serialize(getattr(feedback, "created_at", None)),
    }
    if include_content:
        record["inputs"] = serialize(getattr(run, "inputs", None))
        record["outputs"] = serialize(getattr(run, "outputs", None))
    if child_runs is not None:
        record["child_runs"] = [
            child_run_record(child_run, include_content) for child_run in child_runs
        ]
    return record


def collect_feedback_records(
    client: Any,
    project: str,
    feedback_key: str = DEFAULT_FEEDBACK_KEY,
    score: Optional[float] = 0,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: Optional[int] = None,
    include_content: bool = False,
    include_child_runs: bool = False,
) -> list[dict[str, Any]]:
    """Collect feedback and its project-scoped LangSmith runs."""
    feedback_items = [
        feedback
        for feedback in client.list_feedback(feedback_key=[feedback_key])
        if getattr(feedback, "run_id", None)
        and score_matches(getattr(feedback, "score", None), score)
        and feedback_in_range(feedback, since, until)
    ]
    feedback_items.sort(
        key=lambda item: as_utc(getattr(item, "created_at", None))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    run_ids = [feedback.run_id for feedback in feedback_items]
    runs = load_project_runs(client, project, run_ids)
    records: list[dict[str, Any]] = []

    for feedback in feedback_items:
        run = runs.get(str(feedback.run_id))
        if run is None:
            continue
        loaded_children = None
        if include_child_runs:
            detailed_run = client.read_run(run.id, load_child_runs=True)
            loaded_children = list(getattr(detailed_run, "child_runs", None) or [])
        records.append(
            build_record(
                feedback,
                run,
                project,
                include_content=include_content,
                child_runs=loaded_children,
            )
        )
        if limit is not None and len(records) >= limit:
            break
    return records


def numeric_average(records: Sequence[dict[str, Any]], key: str) -> Optional[float]:
    values = [record[key] for record in records if isinstance(record.get(key), (int, float))]
    return sum(values) / len(values) if values else None


def summarize(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "error_count": sum(1 for record in records if record.get("error")),
        "average_latency_seconds": numeric_average(records, "latency_seconds"),
        "average_total_tokens": numeric_average(records, "total_tokens"),
        "average_total_cost": numeric_average(records, "total_cost"),
        "runs_by_name": dict(Counter(record.get("run_name") or "unknown" for record in records)),
        "runs_by_model": dict(Counter(record.get("model") or "unknown" for record in records)),
        "scores": dict(Counter(str(record.get("feedback_score")) for record in records)),
    }


def write_json(path: Path, records: Sequence[dict[str, Any]], summary: dict[str, Any]) -> None:
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "records": records}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(path: Path, records: Sequence[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {key: csv_value(value) for key, value in record.items()} for record in records
        )


def print_summary(summary: dict[str, Any], output: Path) -> None:
    print("LangSmith feedback report")
    print(f"Records: {summary['record_count']}")
    print(f"Runs with errors: {summary['error_count']}")
    latency = summary["average_latency_seconds"]
    tokens = summary["average_total_tokens"]
    cost = summary["average_total_cost"]
    print(f"Average latency: {latency:.2f}s" if latency is not None else "Average latency: N/A")
    print(f"Average tokens: {tokens:.1f}" if tokens is not None else "Average tokens: N/A")
    print(f"Average cost: ${cost:.6f}" if cost is not None else "Average cost: N/A")
    print(f"Runs by name: {summary['runs_by_name']}")
    print(f"Runs by model: {summary['runs_by_model']}")
    print(f"Output: {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export and summarize LangSmith runs linked to feedback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python langsmith_feedback_report.py --project ai-docusearch
  python langsmith_feedback_report.py --project ai-docusearch --score 0 --format csv
  python langsmith_feedback_report.py --project support-bot --score any --since 2026-08-01
  python langsmith_feedback_report.py --project ai-docusearch --include-content --include-child-runs
""",
    )
    parser.add_argument(
        "--project",
        default=os.getenv("LANGSMITH_PROJECT"),
        help="LangSmith project name (default: LANGSMITH_PROJECT).",
    )
    parser.add_argument("--feedback-key", default=DEFAULT_FEEDBACK_KEY)
    parser.add_argument(
        "--score",
        default="0",
        help="Numeric feedback score, or 'any' (default: 0).",
    )
    parser.add_argument("--since", help="ISO date/datetime lower bound, interpreted as UTC.")
    parser.add_argument("--until", help="ISO date/datetime upper bound, interpreted as UTC.")
    parser.add_argument("--limit", type=int, help="Maximum matching feedback records.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Output path; defaults to langsmith_feedback_report.<format>.")
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include run inputs and outputs. They may contain sensitive data.",
    )
    parser.add_argument(
        "--include-child-runs",
        action="store_true",
        help="Load child-run summaries for each matched run (additional API calls).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None, client: Any = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.project:
        parser.error("--project is required when LANGSMITH_PROJECT is not set")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        score = None if args.score.lower() == "any" else float(args.score)
        since = parse_datetime(args.since)
        until = parse_datetime(args.until)
    except ValueError as exc:
        parser.error(str(exc))
    if since and until and since > until:
        parser.error("--since must be earlier than or equal to --until")

    if client is None:
        if not os.getenv("LANGSMITH_API_KEY"):
            print("LANGSMITH_API_KEY is not configured.", file=sys.stderr)
            return 2
        try:
            from langsmith import Client

            client = Client()
        except Exception as exc:
            print(f"Could not initialize LangSmith: {exc}", file=sys.stderr)
            return 2

    try:
        records = collect_feedback_records(
            client=client,
            project=args.project,
            feedback_key=args.feedback_key,
            score=score,
            since=since,
            until=until,
            limit=args.limit,
            include_content=args.include_content,
            include_child_runs=args.include_child_runs,
        )
    except Exception as exc:
        print(f"Could not query LangSmith: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output or f"{DEFAULT_OUTPUT_STEM}.{args.format}")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(records)
    if args.format == "json":
        write_json(output, records, summary)
    else:
        write_csv(output, records)
    print_summary(summary, output)
    if not args.include_content:
        print("Inputs and outputs were redacted. Use --include-content only when necessary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
