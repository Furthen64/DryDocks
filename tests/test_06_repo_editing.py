"""
Test 06: Existing multi-file repo editing flow.

Seeds a small Python repo locally, asks the model to edit existing files only,
then validates that the edited repo still builds and behaves correctly.
"""

import py_compile
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from drydocks.pytest_runner import run_test_case
from drydocks.tests.base import BaseTest, TestResult


class RepoEditingTest(BaseTest):
    """Existing multi-file repo editing test."""

    name = "repo_editing"
    description = "Edit existing files in a multi-file repo"

    def __init__(self):
        super().__init__()
        self.test_output_dir = Path.cwd() / "repo_edit_test_out"

    def setup(self):
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
        self.test_output_dir.mkdir(exist_ok=True)

    def run(self, client, config, run_index: int) -> TestResult:
        start = time.time()
        warnings = []

        nonce = f"{time.time_ns()}-{run_index}"
        out_dir = self.test_output_dir / f"run_{run_index:03d}"
        package_dir = out_dir / "calcapp"
        out_dir.mkdir(exist_ok=True)
        package_dir.mkdir(exist_ok=True)

        app_file = out_dir / "app.py"
        ops_file = package_dir / "operations.py"
        formatter_file = package_dir / "formatter.py"
        init_file = package_dir / "__init__.py"
        readme_file = out_dir / "README.md"

        artifacts = [
            str(app_file),
            str(ops_file),
            str(formatter_file),
            str(init_file),
            str(readme_file),
        ]

        initial_files = {
            "app.py": textwrap.dedent(
                """
                import sys

                from calcapp.formatter import format_result
                from calcapp.operations import calculate


                def main(argv):
                    if len(argv) != 4:
                        print("usage: python app.py <add|subtract> <a> <b>")
                        return 1

                    operation = argv[1]
                    a = float(argv[2])
                    b = float(argv[3])
                    result = calculate(operation, a, b)
                    print(format_result(result))
                    return 0


                if __name__ == "__main__":
                    raise SystemExit(main(sys.argv))
                """
            ).strip()
            + "\n",
            "calcapp/operations.py": textwrap.dedent(
                """
                def add(a, b):
                    return a + b


                def subtract(a, b):
                    return a - b


                def calculate(operation, a, b):
                    if operation == "add":
                        return add(a, b)
                    if operation == "subtract":
                        return subtract(a, b)
                    raise ValueError(f"unsupported operation: {operation}")
                """
            ).strip()
            + "\n",
            "calcapp/formatter.py": textwrap.dedent(
                """
                def format_result(value):
                    if value == int(value):
                        return str(int(value))
                    return str(value)
                """
            ).strip()
            + "\n",
            "calcapp/__init__.py": "",
            "README.md": textwrap.dedent(
                """
                # CalcApp

                Tiny sample calculator repo.
                Supported operations: add, subtract.
                """
            ).strip()
            + "\n",
        }

        app_file.write_text(initial_files["app.py"], encoding="utf-8")
        ops_file.write_text(initial_files["calcapp/operations.py"], encoding="utf-8")
        formatter_file.write_text(initial_files["calcapp/formatter.py"], encoding="utf-8")
        init_file.write_text(initial_files["calcapp/__init__.py"], encoding="utf-8")
        readme_file.write_text(initial_files["README.md"], encoding="utf-8")

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

        prompt = textwrap.dedent(
            f"""
            Test nonce: {nonce}.
            You are editing an existing multi-file Python repo. Do not create any new files.
            Update only these existing files if needed: app.py, calcapp/operations.py, README.md.
            Leave calcapp/formatter.py and calcapp/__init__.py unchanged.

            Goal:
            1. Add multiply support to the repo.
            2. Add an alias operation named mul that behaves the same as multiply.
            3. Update the CLI usage text so it mentions add, subtract, multiply, and mul.
            4. Update the README so it documents the new operations.
            5. Use the write_file tool once per changed file. Do not answer with text.

            Existing file: app.py
            ```python
            {initial_files["app.py"].rstrip()}
            ```

            Existing file: calcapp/operations.py
            ```python
            {initial_files["calcapp/operations.py"].rstrip()}
            ```

            Existing file: calcapp/formatter.py
            ```python
            {initial_files["calcapp/formatter.py"].rstrip()}
            ```

            Existing file: README.md
            ```markdown
            {initial_files["README.md"].rstrip()}
            ```
            """
        ).strip()
        messages = [{"role": "user", "content": prompt}]
        round_details = []

        try:
            modified_paths = []
            last_response = None
            last_stray_text = ""
            allowed_files = {"app.py", "calcapp/operations.py", "README.md"}

            for round_index in range(1, 4):
                response = client.post_message(
                    {
                        "model": config.get("model"),
                        "max_tokens": 3200,
                        "temperature": 0.0,
                        "tools": tools,
                        "messages": messages,
                    }
                )
                last_response = response
                stray_text = self._get_text(response)
                last_stray_text = stray_text
                if stray_text:
                    warnings.append(
                        f"Model returned stray text alongside repo edit tool_use blocks in round {round_index}; treated as caution pass."
                    )

                tool_uses = self._get_write_file_tools(response)
                round_written_paths = []

                if not tool_uses:
                    if self._get_text(response) == "done":
                        round_details.append(
                            {
                                "round": round_index,
                                "response": response,
                                "stray_text": stray_text,
                                "written_paths": round_written_paths,
                            }
                        )
                        break
                    if modified_paths:
                        round_details.append(
                            {
                                "round": round_index,
                                "response": response,
                                "stray_text": stray_text,
                                "written_paths": round_written_paths,
                            }
                        )
                        break
                    return TestResult(
                        test_name=self.name,
                        run_index=run_index,
                        passed=False,
                        duration_seconds=time.time() - start,
                        error_message="Missing write_file tool_use blocks for repo edits",
                        details={
                            "purpose": self.description,
                            "working_directory": str(Path.cwd()),
                            "nonce": nonce,
                            "request": prompt,
                            "response": response,
                            "stray_text": stray_text,
                        },
                        artifacts=artifacts,
                    )

                seen_paths_in_round = set()
                tool_results = []

                for tool_use in tool_uses:
                    tool_input = tool_use.get("input", {})
                    file_path = tool_input.get("file_path")
                    content = tool_input.get("content")

                    if file_path not in allowed_files:
                        return TestResult(
                            test_name=self.name,
                            run_index=run_index,
                            passed=False,
                            duration_seconds=time.time() - start,
                            error_message=f"Unexpected edited file '{file_path}'",
                            details={
                                "purpose": self.description,
                                "working_directory": str(Path.cwd()),
                                "nonce": nonce,
                                "request": prompt,
                                "response": response,
                                "stray_text": stray_text,
                                "tool_input": tool_input,
                                "round": round_index,
                            },
                            artifacts=artifacts,
                            warnings=warnings,
                        )

                    if file_path in seen_paths_in_round:
                        return TestResult(
                            test_name=self.name,
                            run_index=run_index,
                            passed=False,
                            duration_seconds=time.time() - start,
                            error_message=f"Duplicate write for '{file_path}' in one round",
                            details={
                                "purpose": self.description,
                                "working_directory": str(Path.cwd()),
                                "nonce": nonce,
                                "request": prompt,
                                "response": response,
                                "stray_text": stray_text,
                                "tool_input": tool_input,
                                "round": round_index,
                            },
                            artifacts=artifacts,
                            warnings=warnings,
                        )

                    if not isinstance(content, str):
                        return TestResult(
                            test_name=self.name,
                            run_index=run_index,
                            passed=False,
                            duration_seconds=time.time() - start,
                            error_message=f"Edited content for '{file_path}' was not a string",
                            details={
                                "purpose": self.description,
                                "working_directory": str(Path.cwd()),
                                "nonce": nonce,
                                "request": prompt,
                                "response": response,
                                "stray_text": stray_text,
                                "tool_input": tool_input,
                                "round": round_index,
                            },
                            artifacts=artifacts,
                            warnings=warnings,
                        )

                    seen_paths_in_round.add(file_path)
                    round_written_paths.append(file_path)
                    modified_paths.append(file_path)
                    self._path_for(out_dir, file_path).write_text(content, encoding="utf-8")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.get("id"),
                            "content": f"{file_path} was written successfully.",
                        }
                    )

                round_details.append(
                    {
                        "round": round_index,
                        "response": response,
                        "stray_text": stray_text,
                        "written_paths": round_written_paths,
                    }
                )

                messages.append({"role": "assistant", "content": response.get("content", [])})
                messages.append(
                    {
                        "role": "user",
                        "content": tool_results
                        + [
                            {
                                "type": "text",
                                "text": (
                                    "Continue editing any remaining allowed files needed to fully satisfy "
                                    "all goals. If the repo is complete, reply exactly: done"
                                ),
                            }
                        ],
                    }
                )

            if formatter_file.read_text(encoding="utf-8") != initial_files["calcapp/formatter.py"]:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="calcapp/formatter.py was modified unexpectedly",
                    details={
                        "purpose": self.description,
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "request": prompt,
                        "response": last_response,
                        "modified_paths": modified_paths,
                    },
                    artifacts=artifacts,
                    warnings=warnings,
                )

            self._assert_python_builds(app_file)
            self._assert_python_builds(ops_file)
            self._assert_python_builds(formatter_file)

            add_output = self._run_cli(out_dir, "add", "4", "5")
            multiply_output = self._run_cli(out_dir, "multiply", "6", "7")
            mul_output = self._run_cli(out_dir, "mul", "3", "8")

            if not self._output_matches_number(add_output, 9):
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    f"Expected add output 9, got '{add_output}'",
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            if not self._output_matches_number(multiply_output, 42):
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    f"Expected multiply output 42, got '{multiply_output}'",
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            if not self._output_matches_number(mul_output, 24):
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    f"Expected mul output 24, got '{mul_output}'",
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            usage_process = subprocess.run(
                [sys.executable, str(app_file)],
                capture_output=True,
                text=True,
                cwd=out_dir,
                check=False,
            )
            usage_text = (usage_process.stdout + usage_process.stderr).strip()
            if "multiply" not in usage_text or "mul" not in usage_text:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    "CLI usage text did not mention multiply and mul",
                    modified_paths,
                    last_stray_text,
                    extra_details={"usage_text": usage_text, "rounds": round_details},
                )

            if "calcapp/operations.py" not in modified_paths:
                warnings.append("Model did not rewrite calcapp/operations.py directly; pass is based on working repo behavior.")

            if "app.py" not in modified_paths:
                warnings.append(
                    "Model did not rewrite app.py directly; pass is based on working repo behavior."
                )

            readme_text = readme_file.read_text(encoding="utf-8")
            if "multiply" not in readme_text or "mul" not in readme_text:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    "README.md did not document multiply and mul",
                    modified_paths,
                    last_stray_text,
                    extra_details={"readme_text": readme_text, "rounds": round_details},
                )

            return TestResult(
                test_name=self.name,
                run_index=run_index,
                passed=True,
                duration_seconds=time.time() - start,
                details={
                    "purpose": self.description,
                    "working_directory": str(Path.cwd()),
                    "nonce": nonce,
                    "request": prompt,
                    "response": last_response,
                    "modified_paths": modified_paths,
                    "stray_text": last_stray_text,
                    "rounds": round_details,
                    "cli_outputs": {
                        "add 4 5": add_output,
                        "multiply 6 7": multiply_output,
                        "mul 3 8": mul_output,
                    },
                    "usage_text": usage_text,
                },
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
                    "nonce": nonce,
                    "rounds": round_details,
                },
                artifacts=artifacts,
                warnings=warnings,
            )

    def _failure(
        self,
        start: float,
        run_index: int,
        nonce: str,
        prompt: str,
        response,
        artifacts,
        warnings,
        error_message: str,
        modified_paths,
        stray_text: str,
        extra_details=None,
    ) -> TestResult:
        details = {
            "purpose": self.description,
            "working_directory": str(Path.cwd()),
            "nonce": nonce,
            "request": prompt,
            "response": response,
            "modified_paths": modified_paths,
            "stray_text": stray_text,
        }
        if extra_details:
            details.update(extra_details)

        return TestResult(
            test_name=self.name,
            run_index=run_index,
            passed=False,
            duration_seconds=time.time() - start,
            error_message=error_message,
            details=details,
            artifacts=artifacts,
            warnings=warnings,
        )

    @staticmethod
    def _path_for(root: Path, relative_path: str) -> Path:
        return root / relative_path

    @staticmethod
    def _get_text(response):
        text_blocks = [
            block.get("text", "")
            for block in response.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks).strip()

    @staticmethod
    def _get_write_file_tools(response):
        return [
            block
            for block in response.get("content", [])
            if block.get("type") == "tool_use" and block.get("name") == "write_file"
        ]

    @staticmethod
    def _assert_python_builds(file_path: Path) -> None:
        py_compile.compile(str(file_path), doraise=True)

    @staticmethod
    def _run_cli(root: Path, operation: str, a: str, b: str) -> str:
        process = subprocess.run(
            [sys.executable, "app.py", operation, a, b],
            capture_output=True,
            text=True,
            cwd=root,
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


def test_repo_editing():
    """Pytest entrypoint for the repo editing flow."""
    run_test_case(RepoEditingTest)
