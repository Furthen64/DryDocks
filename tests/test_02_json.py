"""
Test 02: JSON contract validation.

Tests that the LLM can generate properly formatted JSON responses according to a contract.
"""

import json
import time
from pathlib import Path
from drydocks.tests.base import BaseTest, TestResult
from drydocks.pytest_runner import run_test_case


class JsonContractTest(BaseTest):
    """JSON contract test - validates structured output."""

    name = "json"
    description = "JSON response contract validation"

    def run(self, client, config, run_index: int) -> TestResult:
        """Run JSON contract test."""
        start = time.time()

        try:
            payload = {
                "model": config.get("model"),
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Return only this JSON object as the final answer, "
                            "no markdown fences, no extra text: "
                            '{"command":"ping","reply":"pong","ok":true,"count":3}'
                        )
                    }
                ]
            }

            response = client.post_message(payload)

            # Extract text from response
            text_blocks = [
                block.get("text", "")
                for block in response.get("content", [])
                if block.get("type") == "text"
            ]
            text = "\n".join(text_blocks).strip()

            # Try to parse as JSON
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as e:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Invalid JSON: {e}",
                    details={
                        "purpose": "Structured JSON contract validation",
                        "working_directory": str(Path.cwd()),
                        "request": payload,
                        "response": response,
                        "raw_text": text,
                    },
                )

            # Validate structure
            required_keys = {"command", "reply", "ok", "count"}
            actual_keys = set(obj.keys())

            if not required_keys.issubset(actual_keys):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Missing keys: {required_keys - actual_keys}",
                    details={
                        "purpose": "Structured JSON contract validation",
                        "working_directory": str(Path.cwd()),
                        "request": payload,
                        "response": response,
                        "parsed_json": obj,
                    },
                )

            # Check values
            if (
                obj.get("command") == "ping"
                and obj.get("reply") == "pong"
                and obj.get("ok") is True
                and obj.get("count") == 3
            ):
                passed = True
                error_msg = None
            else:
                passed = False
                error_msg = f"Unexpected values in JSON: {obj}"

            details = {
                "purpose": "Structured JSON contract validation",
                "working_directory": str(Path.cwd()),
                "request": payload,
                "response": response,
                "raw_text": text,
                "parsed_json": obj,
            }

        except Exception as e:
            passed = False
            error_msg = str(e)
            details = {
                "purpose": "Structured JSON contract validation",
                "working_directory": str(Path.cwd()),
                "request": payload,
            }

        duration = time.time() - start

        return TestResult(
            test_name=self.name,
            run_index=run_index,
            passed=passed,
            duration_seconds=duration,
            error_message=error_msg,
            details=details,
        )


def test_json_contract():
    """Pytest entrypoint for the object-style test case."""
    run_test_case(JsonContractTest)
