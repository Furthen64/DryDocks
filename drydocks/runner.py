"""
Test runner and discovery for DryDocks.
"""

import importlib
import sys
from pathlib import Path
from typing import List, Type, Any

from .tests.base import BaseTest, TestResult


class TestRunner:
    """Discovers and runs DryDocks tests."""

    def __init__(self, tests_dir: Path = None):
        """
        Initialize TestRunner.

        Args:
            tests_dir: Path to tests directory (defaults to drydocks/tests/)
        """
        if tests_dir is None:
            tests_dir = Path(__file__).parent / "tests"
        self.tests_dir = tests_dir

    def discover_tests(self) -> dict[str, Type[BaseTest]]:
        """
        Discover all test modules in tests/ directory.

        Returns:
            Dict mapping test name to test class
        """
        tests = {}
        
        # Add tests directory to path temporarily
        sys.path.insert(0, str(self.tests_dir))
        
        try:
            for test_file in sorted(self.tests_dir.glob("test_*.py")):
                module_name = test_file.stem
                try:
                    module = importlib.import_module(module_name)
                    
                    # Find BaseTest subclasses in module
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, BaseTest)
                            and obj is not BaseTest
                        ):
                            test_name = getattr(obj, "name", name)
                            tests[test_name] = obj
                except Exception as e:
                    print(f"Warning: Failed to load test module {module_name}: {e}")
        finally:
            sys.path.pop(0)
        
        return tests

    def run_suite(
        self,
        tests: dict[str, Type[BaseTest]],
        client: Any,
        config: Any,
        num_runs: int = 1,
    ) -> List[TestResult]:
        """
        Run a suite of tests.

        Args:
            tests: Dict of test name -> test class
            client: LLMClient instance
            config: ConfigManager instance
            num_runs: Number of iterations per test

        Returns:
            List of TestResult objects
        """
        all_results = []

        for test_name, test_class in tests.items():
            test_instance = test_class()
            
            for run_index in range(1, num_runs + 1):
                try:
                    test_instance.setup()
                    result = test_instance.run(client, config, run_index)
                    all_results.append(result)
                except Exception as e:
                    result = TestResult(
                        test_name=test_name,
                        run_index=run_index,
                        passed=False,
                        duration_seconds=0.0,
                        error_message=str(e),
                    )
                    all_results.append(result)
                finally:
                    try:
                        test_instance.teardown()
                    except Exception:
                        pass

        return all_results

    def aggregate_results(self, results: List[TestResult]) -> dict[str, Any]:
        """
        Aggregate test results into summary statistics.

        Args:
            results: List of TestResult objects

        Returns:
            Dict with aggregated stats
        """
        if not results:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "total_duration": 0.0,
                "by_test": {},
            }

        by_test = {}
        total_duration = 0.0

        for result in results:
            test_name = result.test_name
            if test_name not in by_test:
                by_test[test_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                }
            
            by_test[test_name]["total"] += 1
            if result.passed:
                by_test[test_name]["passed"] += 1
            else:
                by_test[test_name]["failed"] += 1
            
            total_duration += result.duration_seconds

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0.0,
            "total_duration": total_duration,
            "by_test": by_test,
        }
