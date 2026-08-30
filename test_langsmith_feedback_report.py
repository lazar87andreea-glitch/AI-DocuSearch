"""Offline tests for the reusable LangSmith feedback report CLI."""

import csv
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator, Sequence
from uuid import UUID, uuid4

from langsmith_feedback_report import collect_feedback_records, main


def utc(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def make_feedback(
    run_id: UUID, score: float, day: int, comment: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        run_id=run_id,
        key="user_rating",
        score=score,
        value=None,
        comment=comment,
        created_at=utc(day),
    )


def make_run(run_id: UUID, name: str, day: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=run_id,
        trace_id=uuid4(),
        name=name,
        run_type="llm",
        status="success",
        error=None,
        start_time=utc(day),
        end_time=utc(day).replace(second=2),
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        total_cost=0.001,
        inputs={"model": "test-model", "question": "private question"},
        outputs={"answer": "private answer"},
        tags=["test"],
        extra={"metadata": {"environment": "test"}},
    )


class FakeClient:
    def __init__(self):
        target_negative_id = uuid4()
        target_positive_id = uuid4()
        target_old_id = uuid4()
        other_project_id = uuid4()
        self.feedback: list[SimpleNamespace] = [
            make_feedback(other_project_id, 0, 20),
            make_feedback(target_negative_id, 0, 15, "Needs a citation"),
            make_feedback(target_positive_id, 1, 14),
            make_feedback(target_old_id, 0, 1),
        ]
        self.runs_by_project: dict[str, dict[UUID, SimpleNamespace]] = {
            "target-project": {
                target_negative_id: make_run(target_negative_id, "generate_answer", 15),
                target_positive_id: make_run(target_positive_id, "generate_answer", 14),
                target_old_id: make_run(target_old_id, "generate_answer", 1),
            },
            "other-project": {
                other_project_id: make_run(other_project_id, "other_answer", 20),
            },
        }

    def list_feedback(self, feedback_key: list[str]) -> Iterator[SimpleNamespace]:
        assert feedback_key == ["user_rating"]
        return iter(self.feedback)

    def list_runs(
        self, project_name: str, run_ids: Sequence[UUID]
    ) -> Iterator[SimpleNamespace]:
        project_runs = self.runs_by_project.get(project_name, {})
        return iter(project_runs[run_id] for run_id in run_ids if run_id in project_runs)


def test_filters_project_score_date_and_limit():
    records = collect_feedback_records(
        FakeClient(),
        project="target-project",
        score=0,
        since=datetime(2026, 8, 10, tzinfo=timezone.utc),
        limit=1,
    )

    assert len(records) == 1
    assert records[0]["project"] == "target-project"
    assert records[0]["feedback_score"] == 0
    assert records[0]["feedback_comment"] == "Needs a citation"
    assert records[0]["latency_seconds"] == 2


def test_redacts_content_by_default_and_supports_opt_in():
    client = FakeClient()
    redacted = collect_feedback_records(client, "target-project", score=0, limit=1)
    included = collect_feedback_records(
        client, "target-project", score=0, limit=1, include_content=True
    )

    assert "inputs" not in redacted[0]
    assert "outputs" not in redacted[0]
    assert included[0]["inputs"]["question"] == "private question"
    assert included[0]["outputs"]["answer"] == "private answer"


def test_cli_writes_json_and_csv_exports():
    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = Path(temp_dir) / "report.json"
        csv_path = Path(temp_dir) / "report.csv"

        json_exit = main(
            ["--project", "target-project", "--limit", "1", "--output", str(json_path)],
            client=FakeClient(),
        )
        csv_exit = main(
            [
                "--project",
                "target-project",
                "--limit",
                "1",
                "--format",
                "csv",
                "--output",
                str(csv_path),
            ],
            client=FakeClient(),
        )

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        with csv_path.open(encoding="utf-8", newline="") as csv_file:
            csv_rows = list(csv.DictReader(csv_file))

        assert json_exit == 0
        assert csv_exit == 0
        assert payload["summary"]["record_count"] == 1
        assert payload["summary"]["average_total_tokens"] == 120
        assert "inputs" not in payload["records"][0]
        assert len(csv_rows) == 1
        assert csv_rows[0]["run_name"] == "generate_answer"


def test_cli_writes_empty_json_report():
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "empty.json"
        exit_code = main(
            [
                "--project",
                "target-project",
                "--score",
                "99",
                "--output",
                str(output_path),
            ],
            client=FakeClient(),
        )
        payload = json.loads(output_path.read_text(encoding="utf-8"))

        assert exit_code == 0
        assert payload["summary"]["record_count"] == 0
        assert payload["records"] == []


if __name__ == "__main__":
    test_filters_project_score_date_and_limit()
    test_redacts_content_by_default_and_supports_opt_in()
    test_cli_writes_json_and_csv_exports()
    test_cli_writes_empty_json_report()
    print("All LangSmith feedback report tests passed.")