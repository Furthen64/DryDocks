"""
Result formatting and reporting for DryDocks tests.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .tests.base import TestResult


class ReportFormatter:
    """Formats and outputs test results."""

    @staticmethod
    def format_table(results: List[TestResult]) -> str:
        """
        Format results as human-readable table.

        Args:
            results: List of TestResult objects

        Returns:
            Formatted table string
        """
        lines = []
        lines.append("")
        lines.append("=" * 90)
        lines.append(f"{'Test Name':<30} {'Run':<8} {'Status':<10} {'Duration':<12} {'Error':<20}")
        lines.append("=" * 90)

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            error_msg = result.error_message[:20] if result.error_message else ""
            lines.append(
                f"{result.test_name:<30} {result.run_index:<8} {status:<10} "
                f"{result.duration_seconds:<12.3f}s {error_msg:<20}"
            )

        lines.append("=" * 90)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_summary(stats: Dict[str, Any]) -> str:
        """
        Format summary statistics.

        Args:
            stats: Dict from TestRunner.aggregate_results()

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("")
        lines.append("=" * 60)
        lines.append("SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Total:       {stats['total']}")
        lines.append(f"Passed:      {stats['passed']}")
        lines.append(f"Failed:      {stats['failed']}")
        lines.append(f"Pass Rate:   {stats['pass_rate']:.1f}%")
        lines.append(f"Duration:    {stats['total_duration']:.2f}s")
        lines.append("")

        if stats["by_test"]:
            lines.append("By Test:")
            for test_name, counts in stats["by_test"].items():
                pass_rate = (
                    counts["passed"] / counts["total"] * 100
                    if counts["total"] > 0
                    else 0
                )
                lines.append(
                    f"  {test_name:<25} {counts['passed']}/{counts['total']} "
                    f"({pass_rate:.0f}%)"
                )

        lines.append("=" * 60)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def save_jsonl(results: List[TestResult], output_dir: Path = None) -> Path:
        """
        Save results as JSONL (one JSON object per line).

        Args:
            results: List of TestResult objects
            output_dir: Directory to save to (defaults to results/)

        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Path.cwd() / "results"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"drydocks_{timestamp}.jsonl"

        with open(output_file, "w") as f:
            for result in results:
                f.write(json.dumps(result.to_dict()) + "\n")

        return output_file

    @staticmethod
    def print_progress(result: TestResult) -> None:
        """
        Print a single test result as progress update.

        Args:
            result: TestResult object
        """
        status = "✓ PASS" if result.passed else "✗ FAIL"
        error = f" ({result.error_message[:40]})" if result.error_message else ""
        print(f"  [{result.run_index}] {status} {result.test_name}{error}")
