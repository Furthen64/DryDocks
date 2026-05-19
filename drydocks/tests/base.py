"""
Base test class and result dataclass for DryDocks tests.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict


@dataclass
class TestResult:
    """Result of a single test run."""

    test_name: str
    run_index: int
    passed: bool
    duration_seconds: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return asdict(self)


class BaseTest(ABC):
    """Abstract base class for DryDocks tests."""

    name: str = "BaseTest"
    description: str = "Base test class"

    @abstractmethod
    def run(self, client: Any, config: Any, run_index: int) -> TestResult:
        """
        Execute the test.

        Args:
            client: LLMClient instance
            config: ConfigManager instance
            run_index: Current run number (1-indexed)

        Returns:
            TestResult with pass/fail status and details
        """
        pass

    def setup(self) -> None:
        """Setup hook (optional)."""
        pass

    def teardown(self) -> None:
        """Teardown hook (optional)."""
        pass

    def _time_execution(self, func, *args, **kwargs):
        """Time a function execution."""
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            return result, duration
        except Exception as e:
            duration = time.time() - start
            raise
