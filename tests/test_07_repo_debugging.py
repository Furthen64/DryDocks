"""
Test 07: Multi-file repo editing with hidden validation and repair rounds.

Seeds a larger repo, asks the model to implement coordinated edits, then runs
hidden runtime validation. If validation fails, the model gets diagnostics and
one or more repair rounds.
"""

import json
import py_compile
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from drydocks.pytest_runner import run_test_case
from drydocks.tests.base import BaseTest, TestResult


class RepoDebuggingTest(BaseTest):
    """Harder repo editing and debugging test."""

    name = "repo_debugging"
    description = "Edit and debug an existing multi-file repo"

    def __init__(self):
        super().__init__()
        self.test_output_dir = Path.cwd() / "repo_debug_test_out"

    def setup(self):
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
        self.test_output_dir.mkdir(exist_ok=True)

    def run(self, client, config, run_index: int) -> TestResult:
        start = time.time()
        warnings = []
        nonce = f"{time.time_ns()}-{run_index}"

        out_dir = self.test_output_dir / f"run_{run_index:03d}"
        package_dir = out_dir / "inventory"
        out_dir.mkdir(exist_ok=True)
        package_dir.mkdir(exist_ok=True)

        files = {
            "app.py": out_dir / "app.py",
            "README.md": out_dir / "README.md",
            "inventory/__init__.py": package_dir / "__init__.py",
            "inventory/commands.py": package_dir / "commands.py",
            "inventory/report.py": package_dir / "report.py",
            "inventory/service.py": package_dir / "service.py",
            "inventory/storage.py": package_dir / "storage.py",
            "inventory/validators.py": package_dir / "validators.py",
        }
        artifacts = [str(path) for path in files.values()]

        initial_files = {
            "app.py": textwrap.dedent(
                """
                import sys

                from inventory.commands import COMMANDS
                from inventory.report import format_inventory
                from inventory.service import add_item, sell_item, show_inventory
                from inventory.validators import parse_args


                def main(argv):
                    command_name, payload = parse_args(argv)
                    command = COMMANDS[command_name]

                    if command == "add_item":
                        result = add_item(payload["name"], payload["quantity"], payload["price"])
                        print(result)
                        return 0

                    if command == "sell_item":
                        result = sell_item(payload["name"], payload["quantity"])
                        print(result)
                        return 0

                    if command == "show_inventory":
                        print(format_inventory(show_inventory()))
                        return 0

                    raise ValueError(f"unknown command mapping: {command}")


                if __name__ == "__main__":
                    raise SystemExit(main(sys.argv))
                """
            ).strip()
            + "\n",
            "README.md": textwrap.dedent(
                """
                # Inventory CLI

                Commands:
                - add-item <name> <quantity> <price>
                - sell-item <name> <quantity>
                - show
                """
            ).strip()
            + "\n",
            "inventory/__init__.py": "",
            "inventory/commands.py": textwrap.dedent(
                """
                COMMANDS = {
                    "add-item": "add_item",
                    "sell-item": "sell_item",
                    "show": "show_inventory",
                }
                """
            ).strip()
            + "\n",
            "inventory/report.py": textwrap.dedent(
                """
                def format_inventory(items):
                    if not items:
                        return "empty"

                    lines = []
                    for item in items:
                        lines.append(f"{item['name']} ({item['quantity']})")
                    return "\\n".join(lines)
                """
            ).strip()
            + "\n",
            "inventory/service.py": textwrap.dedent(
                """
                from inventory.storage import load_inventory, save_inventory


                def add_item(name, quantity, price):
                    items = load_inventory()
                    item = items.get(name)
                    if item is None:
                        items[name] = {"quantity": quantity, "price": price}
                    else:
                        item["quantity"] += quantity
                        item["price"] = price
                    save_inventory(items)
                    return f"added {name}"


                def sell_item(name, quantity):
                    items = load_inventory()
                    if name not in items:
                        raise ValueError(f"missing item: {name}")
                    items[name]["quantity"] -= quantity
                    save_inventory(items)
                    return f"sold {name}"


                def show_inventory():
                    items = load_inventory()
                    rows = []
                    for name, item in sorted(items.items()):
                        rows.append(
                            {
                                "name": name,
                                "quantity": item["quantity"],
                                "price": item["price"],
                            }
                        )
                    return rows
                """
            ).strip()
            + "\n",
            "inventory/storage.py": textwrap.dedent(
                """
                import json
                from pathlib import Path


                DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"


                def load_inventory():
                    if not DATA_FILE.exists():
                        return {}
                    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


                def save_inventory(items):
                    DATA_FILE.write_text(json.dumps(items, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
                """
            ).strip()
            + "\n",
            "inventory/validators.py": textwrap.dedent(
                """
                from inventory.commands import COMMANDS


                def parse_args(argv):
                    if len(argv) < 2:
                        raise ValueError("usage: python app.py <command> ...")

                    command_name = argv[1]
                    if command_name not in COMMANDS:
                        raise ValueError(f"unsupported command: {command_name}")

                    if command_name == "add-item":
                        if len(argv) != 5:
                            raise ValueError("usage: python app.py add-item <name> <quantity> <price>")
                        return command_name, {
                            "name": argv[2],
                            "quantity": int(argv[3]),
                            "price": float(argv[4]),
                        }

                    if command_name == "sell-item":
                        if len(argv) != 4:
                            raise ValueError("usage: python app.py sell-item <name> <quantity>")
                        return command_name, {
                            "name": argv[2],
                            "quantity": int(argv[3]),
                        }

                    if command_name == "show":
                        if len(argv) != 2:
                            raise ValueError("usage: python app.py show")
                        return command_name, {}

                    raise ValueError(f"unsupported command: {command_name}")
                """
            ).strip()
            + "\n",
        }

        for relative_path, content in initial_files.items():
            files[relative_path].write_text(content, encoding="utf-8")

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
            You may edit only: app.py, README.md, inventory/commands.py, inventory/report.py,
            inventory/service.py, inventory/validators.py.
            Do not modify inventory/storage.py or inventory/__init__.py.

            Goals:
            1. Add a new `restock <name> <quantity>` command that increases quantity without changing price.
            2. Add an alias command `ls` for `show`.
            3. Change the inventory report format to `name: quantity @ price` with price shown to two decimals.
            4. Keep add-item, sell-item, and show working.
            5. Update README documentation and CLI usage behavior accordingly.
            6. Use the write_file tool once per changed file. Do not answer with text.

            Existing file: app.py
            ```python
            {initial_files["app.py"].rstrip()}
            ```

            Existing file: README.md
            ```markdown
            {initial_files["README.md"].rstrip()}
            ```

            Existing file: inventory/commands.py
            ```python
            {initial_files["inventory/commands.py"].rstrip()}
            ```

            Existing file: inventory/report.py
            ```python
            {initial_files["inventory/report.py"].rstrip()}
            ```

            Existing file: inventory/service.py
            ```python
            {initial_files["inventory/service.py"].rstrip()}
            ```

            Existing file: inventory/storage.py
            ```python
            {initial_files["inventory/storage.py"].rstrip()}
            ```

            Existing file: inventory/validators.py
            ```python
            {initial_files["inventory/validators.py"].rstrip()}
            ```
            """
        ).strip()

        messages = [{"role": "user", "content": prompt}]
        round_details = []
        modified_paths = []
        last_response = None
        last_stray_text = ""
        allowed_files = {
            "app.py",
            "README.md",
            "inventory/commands.py",
            "inventory/report.py",
            "inventory/service.py",
            "inventory/validators.py",
        }

        try:
            for round_index in range(1, 4):
                response = client.post_message(
                    {
                        "model": config.get("model"),
                        "max_tokens": 4200,
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
                        f"Model returned stray text alongside repo debug tool_use blocks in round {round_index}; treated as caution pass."
                    )

                tool_uses = self._get_write_file_tools(response)
                written_paths = []

                if not tool_uses:
                    if stray_text == "done" and round_index > 1:
                        round_details.append(
                            {
                                "round": round_index,
                                "response": response,
                                "stray_text": stray_text,
                                "written_paths": written_paths,
                            }
                        )
                        break
                    return TestResult(
                        test_name=self.name,
                        run_index=run_index,
                        passed=False,
                        duration_seconds=time.time() - start,
                        error_message="Missing write_file tool_use blocks during repo debugging",
                        details={
                            "purpose": self.description,
                            "working_directory": str(Path.cwd()),
                            "nonce": nonce,
                            "request": prompt,
                            "response": response,
                            "round": round_index,
                        },
                        artifacts=artifacts,
                        warnings=warnings,
                    )

                seen_in_round = set()
                tool_results = []

                for tool_use in tool_uses:
                    tool_input = tool_use.get("input", {})
                    file_path = tool_input.get("file_path")
                    content = tool_input.get("content")

                    if file_path not in allowed_files:
                        return self._failure(
                            start,
                            run_index,
                            nonce,
                            prompt,
                            response,
                            artifacts,
                            warnings,
                            f"Unexpected edited file '{file_path}'",
                            modified_paths,
                            stray_text,
                            extra_details={"round": round_index, "tool_input": tool_input},
                        )

                    if file_path in seen_in_round:
                        return self._failure(
                            start,
                            run_index,
                            nonce,
                            prompt,
                            response,
                            artifacts,
                            warnings,
                            f"Duplicate write for '{file_path}' in one round",
                            modified_paths,
                            stray_text,
                            extra_details={"round": round_index, "tool_input": tool_input},
                        )

                    if not isinstance(content, str):
                        return self._failure(
                            start,
                            run_index,
                            nonce,
                            prompt,
                            response,
                            artifacts,
                            warnings,
                            f"Edited content for '{file_path}' was not a string",
                            modified_paths,
                            stray_text,
                            extra_details={"round": round_index, "tool_input": tool_input},
                        )

                    seen_in_round.add(file_path)
                    written_paths.append(file_path)
                    modified_paths.append(file_path)
                    files[file_path].write_text(content, encoding="utf-8")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.get("id"),
                            "content": f"{file_path} was written successfully.",
                        }
                    )

                validation_error = self._validate_repo(out_dir, files)

                round_details.append(
                    {
                        "round": round_index,
                        "response": response,
                        "stray_text": stray_text,
                        "written_paths": written_paths,
                        "validation_error": validation_error,
                    }
                )

                if validation_error is None:
                    break

                messages.append({"role": "assistant", "content": response.get("content", [])})
                messages.append(
                    {
                        "role": "user",
                        "content": tool_results
                        + [
                            {
                                "type": "text",
                                "text": (
                                    "The repo still fails hidden validation. "
                                    f"Failure details:\n{validation_error}\n"
                                    "Edit any remaining allowed files needed to fix the repo. "
                                    "If you believe it is fully fixed after your edits, do not answer with text."
                                ),
                            }
                        ],
                    }
                )
            else:
                validation_error = self._validate_repo(out_dir, files)

            if validation_error is not None:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    validation_error,
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            if files["inventory/storage.py"].read_text(encoding="utf-8") != initial_files["inventory/storage.py"]:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    "inventory/storage.py was modified unexpectedly",
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            if files["inventory/__init__.py"].read_text(encoding="utf-8") != initial_files["inventory/__init__.py"]:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    "inventory/__init__.py was modified unexpectedly",
                    modified_paths,
                    last_stray_text,
                    extra_details={"rounds": round_details},
                )

            readme_text = files["README.md"].read_text(encoding="utf-8")
            if "restock" not in readme_text or "ls" not in readme_text:
                return self._failure(
                    start,
                    run_index,
                    nonce,
                    prompt,
                    last_response,
                    artifacts,
                    warnings,
                    "README.md did not document restock and ls",
                    modified_paths,
                    last_stray_text,
                    extra_details={"readme_text": readme_text, "rounds": round_details},
                )

            data_file = out_dir / "data.json"
            data_snapshot = {}
            if data_file.exists():
                data_snapshot = json.loads(data_file.read_text(encoding="utf-8"))

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
                    "data_snapshot": data_snapshot,
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

    def _validate_repo(self, root: Path, files: dict[str, Path]) -> str | None:
        for key in ("app.py", "inventory/commands.py", "inventory/report.py", "inventory/service.py", "inventory/validators.py"):
            py_compile.compile(str(files[key]), doraise=True)

        add_result = self._run_cli(root, "add-item", "apple", "10", "2.5")
        if add_result != "added apple":
            return f"Expected 'added apple', got '{add_result}'"

        restock_result = self._run_cli(root, "restock", "apple", "5")
        if restock_result != "restocked apple":
            return f"Expected 'restocked apple', got '{restock_result}'"

        sell_result = self._run_cli(root, "sell-item", "apple", "3")
        if sell_result != "sold apple":
            return f"Expected 'sold apple', got '{sell_result}'"

        show_output = self._run_cli(root, "show")
        ls_output = self._run_cli(root, "ls")
        expected_line = "apple: 12 @ 2.50"
        if expected_line not in show_output:
            return f"Expected show output to contain '{expected_line}', got '{show_output}'"
        if expected_line not in ls_output:
            return f"Expected ls output to contain '{expected_line}', got '{ls_output}'"

        usage_process = subprocess.run(
            [sys.executable, "app.py"],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        usage_text = (usage_process.stdout + usage_process.stderr).strip()
        if "restock" not in usage_text or "ls" not in usage_text:
            return f"Usage output did not mention restock and ls: '{usage_text}'"

        data = json.loads((root / "data.json").read_text(encoding="utf-8"))
        apple = data.get("apple")
        if apple is None:
            return "data.json did not contain apple"
        if apple.get("quantity") != 12:
            return f"Expected apple quantity 12, got {apple.get('quantity')}"
        if float(apple.get("price")) != 2.5:
            return f"Expected apple price 2.5, got {apple.get('price')}"

        return None

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
    def _run_cli(root: Path, *args: str) -> str:
        process = subprocess.run(
            [sys.executable, "app.py", *args],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"CLI command failed for {' '.join(args)}: stdout='{process.stdout.strip()}' "
                f"stderr='{process.stderr.strip()}'"
            )
        return process.stdout.strip()


def test_repo_debugging():
    """Pytest entrypoint for the repo debugging flow."""
    run_test_case(RepoDebuggingTest)
