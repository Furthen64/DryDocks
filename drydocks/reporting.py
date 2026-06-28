"""Plain-text report generation for DryDocks test runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, UTC
import json
from pathlib import Path
from typing import Any

from drydocks.tests.base import TestResult


class RunReporter:
    """Collects test results and writes a user-readable text report."""

    def __init__(self, reports_dir: str | Path = "reports") -> None:
        self.reports_dir = Path(reports_dir)
        self.run_started_at = datetime.now(UTC)
        self.run_id = self.run_started_at.strftime("%Y%m%d-%H%M%S")
        self.report_path = self.reports_dir / f"drydocks-report-{self.run_id}.txt"
        self.results_path = self.reports_dir / ".latest-results.json"
        self.results: list[dict[str, Any]] = []

    def record(self, result: TestResult) -> None:
        """Append one normalized result for later report generation."""
        self.results.append(asdict(result))

    def write(self, config: dict[str, Any]) -> Path:
        """Write the current run report and return its path."""
        self.reports_dir.mkdir(exist_ok=True)

        lines = [
            "DryDocks Test Report",
            f"Run ID: {self.run_id}",
            f"Generated: {self.run_started_at.isoformat()}",
            f"Base URL: {config.get('base_url', '')}",
            f"Model: {config.get('model', '')}",
            "",
        ]

        passed_count = sum(1 for result in self.results if result.get("passed"))
        total_count = len(self.results)
        failed_count = total_count - passed_count
        lines.extend(
            [
                f"Summary: {passed_count} passed, {failed_count} failed, {total_count} total",
                "",
                "Results:",
            ]
        )

        for result in self.results:
            status = "PASS" if result.get("passed") else "FAIL"
            lines.append(
                f"- {status} {result.get('test_name')} "
                f"({result.get('duration_seconds', 0.0):.2f}s)"
            )
            error_message = result.get("error_message")
            if error_message:
                lines.append(f"  Error: {error_message}")

        self.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.results_path.write_text(json.dumps(self.results, indent=2) + "\n", encoding="utf-8")
        return self.report_path
