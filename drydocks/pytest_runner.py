"""Pytest bridge for the object-style DryDocks tests."""

from __future__ import annotations

import atexit
from pathlib import Path

from drydocks.client import OpenAICompatClient
from drydocks.config import load_config
from drydocks.reporting import RunReporter


_REPORTER = RunReporter()
_REPORT_PATH: Path | None = None
_CONFIG = load_config()


def _write_report_at_exit() -> None:
    """Flush the collected run report when the process exits."""
    global _REPORT_PATH
    _REPORT_PATH = _REPORTER.write(_CONFIG)
    print(f"DryDocks report: {_REPORT_PATH}")


atexit.register(_write_report_at_exit)


def run_test_case(test_case_class: type) -> None:
    """Instantiate a DryDocks test class and assert that it passes."""
    test_case = test_case_class()
    client = OpenAICompatClient(
        base_url=_CONFIG["base_url"],
        api_key=_CONFIG.get("api_key", ""),
    )

    setup = getattr(test_case, "setup", None)
    teardown = getattr(test_case, "teardown", None)

    if callable(setup):
        setup()

    try:
        result = test_case.run(client, _CONFIG, run_index=1)
    finally:
        if callable(teardown):
            teardown()

    _REPORTER.record(result)
    assert result.passed, result.error_message or f"{result.test_name} failed"
