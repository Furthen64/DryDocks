"""
Test 03: Tool use freshness test.

Tests the LLM's ability to use tools (function calling) with fresh, unique tool definitions.
"""

import time
import random
from pathlib import Path
from drydocks.tests.base import BaseTest, TestResult
from drydocks.pytest_runner import run_test_case


class ToolUseTest(BaseTest):
    """Tool use test - validates tool calling with fresh definitions."""

    name = "tool_use"
    description = "Tool use freshness test"

    def run(self, client, config, run_index: int) -> TestResult:
        """Run tool use test."""
        start = time.time()
        warnings = []

        try:
            # Generate unique nonce for this run
            nonce = f"{time.time_ns()}-{random.randint(0, 999999)}-{run_index}"

            payload = {
                "model": config.get("model"),
                "max_tokens": 256,
                "tools": [
                    {
                        "name": "write_file",
                        "description": f"Write text to a file. Request nonce: {nonce}",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["file_path", "content"]
                        }
                    }
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Request nonce: {nonce}. "
                            "Use the write_file tool to create TEST.txt with empty content. "
                            "Do not answer with text."
                        )
                    }
                ]
            }

            response = client.post_message(payload)
            text_blocks = [
                block.get("text", "")
                for block in response.get("content", [])
                if block.get("type") == "text" and block.get("text", "").strip()
            ]
            stray_text = "\n".join(text_blocks).strip()
            if stray_text:
                warnings.append(
                    "Model returned stray text alongside tool_use; treated as caution pass."
                )

            # Check for tool_use block
            tool_uses = [
                block
                for block in response.get("content", [])
                if block.get("type") == "tool_use" and block.get("name") == "write_file"
            ]

            if len(tool_uses) != 1:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Expected 1 write_file tool_use, got {len(tool_uses)}",
                    details={
                        "purpose": "Function calling validation",
                        "working_directory": str(Path.cwd()),
                        "request": payload,
                        "response": response,
                        "nonce": nonce,
                        "stray_text": stray_text,
                    },
                )

            tool_use = tool_uses[0]
            tool_input = tool_use.get("input", {})
            file_path = tool_input.get("file_path")
            content = tool_input.get("content")

            # Validate tool inputs
            if file_path != "TEST.txt":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Expected file_path='TEST.txt', got '{file_path}'",
                    details={
                        "purpose": "Function calling validation",
                        "working_directory": str(Path.cwd()),
                        "request": payload,
                        "response": response,
                        "nonce": nonce,
                        "stray_text": stray_text,
                        "tool_input": tool_input,
                    },
                )

            if content != "":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Expected empty content, got '{content}'",
                    details={
                        "purpose": "Function calling validation",
                        "working_directory": str(Path.cwd()),
                        "request": payload,
                        "response": response,
                        "nonce": nonce,
                        "stray_text": stray_text,
                        "tool_input": tool_input,
                    },
                )

            passed = True
            error_msg = None
            details = {
                "purpose": "Function calling validation",
                "working_directory": str(Path.cwd()),
                "request": payload,
                "response": response,
                "nonce": nonce,
                "stray_text": stray_text,
                "tool_input": tool_input,
            }

        except Exception as e:
            passed = False
            error_msg = str(e)
            details = {
                "purpose": "Function calling validation",
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
            warnings=warnings,
        )


def test_tool_use():
    """Pytest entrypoint for the object-style test case."""
    run_test_case(ToolUseTest)
