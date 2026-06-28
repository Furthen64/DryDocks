"""Shared types for DryDocks tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TestResult:
    """Normalized result returned by each DryDocks test."""

    __test__ = False

    test_name: str
    run_index: int
    passed: bool
    duration_seconds: float
    error_message: str | None = None


class BaseTest(ABC):
    """Base class for the object-style DryDocks tests."""

    __test__ = False

    name = ""
    description = ""

    def setup(self) -> None:
        """Optional per-test setup hook."""

    def teardown(self) -> None:
        """Optional per-test cleanup hook."""

    @abstractmethod
    def run(self, client, config, run_index: int) -> TestResult:
        """Execute one test run."""
