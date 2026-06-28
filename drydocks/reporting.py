"""Plain-text report generation for DryDocks test runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, UTC
import json
import os
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
        self.latest_report_path = self.reports_dir / "latest-report.txt"
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
            f"Working Directory: {Path.cwd()}",
            f"Python Executable: {os.environ.get('VIRTUAL_ENV', '')}/bin/python3"
            if os.environ.get("VIRTUAL_ENV")
            else f"Python Executable: {os.sys.executable}",
            f"Base URL: {config.get('base_url', '')}",
            f"Model: {config.get('model', '')}",
            "",
        ]

        passed_count = sum(1 for result in self.results if result.get("passed"))
        caution_count = sum(
            1 for result in self.results if result.get("passed") and result.get("warnings")
        )
        total_count = len(self.results)
        failed_count = total_count - passed_count
        lines.extend(
            [
                (
                    f"Summary: {passed_count} passed, {caution_count} caution passes, "
                    f"{failed_count} failed, {total_count} total"
                ),
                "",
                "Results:",
            ]
        )

        for result in self.results:
            status = "FAIL"
            if result.get("passed"):
                status = "CAUTION PASS" if result.get("warnings") else "PASS"
            lines.append(
                f"- {status} {result.get('test_name')} "
                f"({result.get('duration_seconds', 0.0):.2f}s)"
            )
            error_message = result.get("error_message")
            if error_message:
                lines.append(f"  Error: {error_message}")

            warnings = result.get("warnings") or []
            if warnings:
                lines.append("  Warnings:")
                for warning in warnings:
                    lines.append(f"    - {warning}")

            details = result.get("details") or {}
            if details:
                lines.extend(self._format_details(details))

            artifacts = result.get("artifacts") or []
            if artifacts:
                lines.append("  Artifacts:")
                for artifact in artifacts:
                    lines.append(f"    - {artifact}")

        report_text = "\n".join(lines) + "\n"
        self.report_path.write_text(report_text, encoding="utf-8")
        self.latest_report_path.write_text(report_text, encoding="utf-8")
        self.results_path.write_text(json.dumps(self.results, indent=2) + "\n", encoding="utf-8")
        return self.report_path

    def _format_details(self, details: dict[str, Any]) -> list[str]:
        """Render nested detail data into readable indented lines."""
        lines = ["  Details:"]
        lines.extend(self._render_mapping(details, indent="    "))
        return lines

    def _render_mapping(self, value: Any, indent: str) -> list[str]:
        """Render arbitrary JSON-like values into indented report lines."""
        if isinstance(value, dict):
            lines: list[str] = []
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}{key}:")
                    lines.extend(self._render_mapping(item, indent + "  "))
                else:
                    lines.append(f"{indent}{key}: {item}")
            return lines

        if isinstance(value, list):
            lines = []
            for item in value:
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}-")
                    lines.extend(self._render_mapping(item, indent + "  "))
                else:
                    lines.append(f"{indent}- {item}")
            return lines

        return [f"{indent}{value}"]
