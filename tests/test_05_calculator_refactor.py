"""
Test 05: Calculator generation and refactor flow.

Creates a Python calculator app, modifies it, then removes one function while
verifying the app still compiles and works after each step.
"""

import importlib.util
import py_compile
import subprocess
import sys
import time
from pathlib import Path

from drydocks.pytest_runner import run_test_case
from drydocks.tests.base import BaseTest, TestResult


class CalculatorRefactorTest(BaseTest):
    """Three-step calculator generation and refactor test."""

    name = "calculator_refactor"
    description = "Generate, adjust, and simplify a calculator app"

    def __init__(self):
        super().__init__()
        self.test_output_dir = Path.cwd() / "calculator_test_out"

    def setup(self):
        self.test_output_dir.mkdir(exist_ok=True)

    def run(self, client, config, run_index: int) -> TestResult:
        start = time.time()
        warnings = []
        artifacts: list[str] = []

        try:
            nonce = f"{time.time_ns()}-{run_index}"
            out_dir = self.test_output_dir / f"run_{run_index:03d}"
            out_dir.mkdir(exist_ok=True)
            calculator_file = out_dir / "calculator.py"
            artifacts.append(str(calculator_file))

            tools = [
                {
                    "name": "write_file",
                    "description": "Write text to a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["file_path", "content"],
                    },
                }
            ]

            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Test nonce: {nonce}. "
                        "Use the write_file tool to create calculator.py. "
                        "It must be a Python calculator app with functions add(a, b), "
                        "subtract(a, b), multiply(a, b), divide(a, b), and "
                        "calculate(operation, a, b). "
                        "Also include a CLI so `python calculator.py add 2 3` prints 5. "
                        "Do not answer with text."
                    ),
                }
            ]

            response1 = client.post_message(
                {
                    "model": config.get("model"),
                    "max_tokens": 1400,
                    "tools": tools,
                    "messages": messages,
                }
            )
            step_1_stray_text = self._get_text(response1)
            if step_1_stray_text:
                warnings.append(
                    "Model returned stray text alongside the step 1 tool_use; treated as caution pass."
                )

            tool_use1 = self._get_write_file_tool(response1)
            if tool_use1 is None:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 1: missing write_file tool_use",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "request_messages": messages,
                            "tools": tools,
                            "response": response1,
                            "stray_text": step_1_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            tool_input1 = tool_use1.get("input", {})
            if tool_input1.get("file_path") != "calculator.py":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 1: wrong file_path '{tool_input1.get('file_path')}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "tool_input": tool_input1,
                            "stray_text": step_1_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            content1 = tool_input1.get("content")
            if not isinstance(content1, str):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 1: calculator content was not a string",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "tool_input": tool_input1,
                            "stray_text": step_1_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            calculator_file.write_text(content1, encoding="utf-8")
            self._assert_python_builds(calculator_file)
            module1 = self._load_module(calculator_file, module_name=f"calculator_step1_{run_index}")

            required_functions = ["add", "subtract", "multiply", "divide", "calculate"]
            missing_functions = [name for name in required_functions if not hasattr(module1, name)]
            if missing_functions:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 1: missing functions {missing_functions}",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "tool_input": tool_input1,
                            "stray_text": step_1_stray_text,
                            "artifact_path": str(calculator_file),
                        },
                    },
                    artifacts=artifacts,
                )

            cli_add_output = self._run_calculator_cli(calculator_file, "add", "2", "3")
            if not self._output_matches_number(cli_add_output, 5):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 1: expected CLI add output 5, got '{cli_add_output}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "tool_input": tool_input1,
                            "artifact_path": str(calculator_file),
                            "cli_add_output": cli_add_output,
                            "stray_text": step_1_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            messages.append({"role": "assistant", "content": response1.get("content", [])})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use1.get("id"),
                            "content": "calculator.py was written successfully.",
                        },
                        {
                            "type": "text",
                            "text": (
                                "Now update calculator.py. Keep the existing features and add "
                                "a power(a, b) function. Update calculate() and the CLI so "
                                "`python calculator.py power 2 5` prints 32. "
                                "Do not answer with text."
                            ),
                        },
                    ],
                }
            )

            response2 = client.post_message(
                {
                    "model": config.get("model"),
                    "max_tokens": 1600,
                    "tools": tools,
                    "messages": messages,
                }
            )
            step_2_stray_text = self._get_text(response2)
            if step_2_stray_text:
                warnings.append(
                    "Model returned stray text alongside the step 2 tool_use; treated as caution pass."
                )

            tool_use2 = self._get_write_file_tool(response2)
            if tool_use2 is None:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: missing write_file tool_use",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "request_messages": messages,
                            "response": response2,
                            "stray_text": step_2_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            tool_input2 = tool_use2.get("input", {})
            if tool_input2.get("file_path") != "calculator.py":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 2: wrong file_path '{tool_input2.get('file_path')}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "tool_input": tool_input2,
                            "stray_text": step_2_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            content2 = tool_input2.get("content")
            if not isinstance(content2, str):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: calculator content was not a string",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "tool_input": tool_input2,
                            "stray_text": step_2_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            calculator_file.write_text(content2, encoding="utf-8")
            self._assert_python_builds(calculator_file)
            module2 = self._load_module(calculator_file, module_name=f"calculator_step2_{run_index}")

            if not hasattr(module2, "power"):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: missing power function after update",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "tool_input": tool_input2,
                            "artifact_path": str(calculator_file),
                            "stray_text": step_2_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            power_output = self._run_calculator_cli(calculator_file, "power", "2", "5")
            if not self._output_matches_number(power_output, 32):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 2: expected CLI power output 32, got '{power_output}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "tool_input": tool_input2,
                            "artifact_path": str(calculator_file),
                            "power_output": power_output,
                            "stray_text": step_2_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            messages.append({"role": "assistant", "content": response2.get("content", [])})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use2.get("id"),
                            "content": "calculator.py was updated successfully.",
                        },
                        {
                            "type": "text",
                            "text": (
                                "Now update calculator.py again. Remove the multiply(a, b) "
                                "function completely and remove multiply support from "
                                "calculate() and the CLI. Keep add, subtract, divide, and "
                                "power working. Do not answer with text."
                            ),
                        },
                    ],
                }
            )

            response3 = client.post_message(
                {
                    "model": config.get("model"),
                    "max_tokens": 1600,
                    "tools": tools,
                    "messages": messages,
                }
            )
            step_3_stray_text = self._get_text(response3)
            if step_3_stray_text:
                warnings.append(
                    "Model returned stray text alongside the step 3 tool_use; treated as caution pass."
                )

            tool_use3 = self._get_write_file_tool(response3)
            if tool_use3 is None:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 3: missing write_file tool_use",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "request_messages": messages,
                            "response": response3,
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            tool_input3 = tool_use3.get("input", {})
            if tool_input3.get("file_path") != "calculator.py":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 3: wrong file_path '{tool_input3.get('file_path')}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            content3 = tool_input3.get("content")
            if not isinstance(content3, str):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 3: calculator content was not a string",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            calculator_file.write_text(content3, encoding="utf-8")
            self._assert_python_builds(calculator_file)
            module3 = self._load_module(calculator_file, module_name=f"calculator_step3_{run_index}")

            if hasattr(module3, "multiply"):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 3: multiply function still exists after requested removal",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "artifact_path": str(calculator_file),
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            add_output = self._run_calculator_cli(calculator_file, "add", "10", "7")
            power_output_after_delete = self._run_calculator_cli(calculator_file, "power", "3", "3")
            if not self._output_matches_number(add_output, 17):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 3: expected CLI add output 17, got '{add_output}'",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "artifact_path": str(calculator_file),
                            "add_output": add_output,
                            "power_output": power_output_after_delete,
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            if not self._output_matches_number(power_output_after_delete, 27):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=(
                        "Step 3: expected CLI power output 27 after multiply removal, "
                        f"got '{power_output_after_delete}'"
                    ),
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "artifact_path": str(calculator_file),
                            "add_output": add_output,
                            "power_output": power_output_after_delete,
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            multiply_process = subprocess.run(
                [sys.executable, str(calculator_file), "multiply", "2", "3"],
                capture_output=True,
                text=True,
                cwd=out_dir,
            )
            if multiply_process.returncode == 0:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 3: multiply CLI still succeeded after multiply removal",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_3": {
                            "response": response3,
                            "tool_input": tool_input3,
                            "artifact_path": str(calculator_file),
                            "multiply_stdout": multiply_process.stdout.strip(),
                            "multiply_stderr": multiply_process.stderr.strip(),
                            "stray_text": step_3_stray_text,
                        },
                    },
                    artifacts=artifacts,
                )

            details = {
                "purpose": self.description,
                "working_directory": str(Path.cwd()),
                "nonce": nonce,
                "step_1": {
                    "request_messages": messages[:1],
                    "response": response1,
                    "tool_input": tool_input1,
                    "artifact_path": str(calculator_file),
                    "cli_add_output": cli_add_output,
                    "stray_text": step_1_stray_text,
                },
                "step_2": {
                    "response": response2,
                    "tool_input": tool_input2,
                    "artifact_path": str(calculator_file),
                    "power_output": power_output,
                    "stray_text": step_2_stray_text,
                },
                "step_3": {
                    "response": response3,
                    "tool_input": tool_input3,
                    "artifact_path": str(calculator_file),
                    "add_output": add_output,
                    "power_output": power_output_after_delete,
                    "multiply_returncode": multiply_process.returncode,
                    "multiply_stdout": multiply_process.stdout.strip(),
                    "multiply_stderr": multiply_process.stderr.strip(),
                    "stray_text": step_3_stray_text,
                },
            }

            return TestResult(
                test_name=self.name,
                run_index=run_index,
                passed=True,
                duration_seconds=time.time() - start,
                details=details,
                artifacts=artifacts,
                warnings=warnings,
            )

        except Exception as exc:
            return TestResult(
                test_name=self.name,
                run_index=run_index,
                passed=False,
                duration_seconds=time.time() - start,
                error_message=str(exc),
                details={
                    "purpose": self.description,
                    "working_directory": str(Path.cwd()),
                },
                artifacts=artifacts,
                warnings=warnings,
            )

    @staticmethod
    def _get_text(response):
        text_blocks = [
            block.get("text", "")
            for block in response.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks).strip()

    @staticmethod
    def _get_write_file_tool(response):
        tool_blocks = [
            block
            for block in response.get("content", [])
            if block.get("type") == "tool_use" and block.get("name") == "write_file"
        ]
        return tool_blocks[0] if len(tool_blocks) == 1 else None

    @staticmethod
    def _assert_python_builds(file_path: Path) -> None:
        py_compile.compile(str(file_path), doraise=True)

    @staticmethod
    def _load_module(file_path: Path, module_name: str):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load module from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _run_calculator_cli(file_path: Path, operation: str, a: str, b: str) -> str:
        process = subprocess.run(
            [sys.executable, str(file_path), operation, a, b],
            capture_output=True,
            text=True,
            cwd=file_path.parent,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"CLI command failed for {operation}: stdout='{process.stdout.strip()}' "
                f"stderr='{process.stderr.strip()}'"
            )
        return process.stdout.strip()

    @staticmethod
    def _output_matches_number(output: str, expected: float) -> bool:
        try:
            return float(output) == float(expected)
        except ValueError:
            return False


def test_calculator_refactor():
    """Pytest entrypoint for the calculator refactor flow."""
    run_test_case(CalculatorRefactorTest)
