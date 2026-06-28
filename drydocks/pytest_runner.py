"""Pytest bridge for the object-style DryDocks tests."""

from __future__ import annotations

from drydocks.client import OpenAICompatClient
from drydocks.config import load_config


def run_test_case(test_case_class: type) -> None:
    """Instantiate a DryDocks test class and assert that it passes."""
    test_case = test_case_class()
    config = load_config()
    client = OpenAICompatClient(
        base_url=config["base_url"],
        api_key=config.get("api_key", ""),
    )

    setup = getattr(test_case, "setup", None)
    teardown = getattr(test_case, "teardown", None)

    if callable(setup):
        setup()

    try:
        result = test_case.run(client, config, run_index=1)
    finally:
        if callable(teardown):
            teardown()

    assert result.passed, result.error_message or f"{result.test_name} failed"
