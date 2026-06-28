"""
Test 04: Multi-turn agent flow test.

Comprehensive agent flow test with multi-turn conversations, text responses, and tool usage.
Tests a realistic agentic workflow.
"""

import time
from pathlib import Path
from drydocks.tests.base import BaseTest, TestResult
from drydocks.pytest_runner import run_test_case


class AgentFlowTest(BaseTest):
    """Agent flow test - comprehensive multi-turn conversation with tools."""

    name = "agent_flow"
    description = "Multi-turn agent flow with tool usage"

    def __init__(self):
        """Initialize AgentFlowTest."""
        super().__init__()
        self.test_output_dir = Path.cwd() / "agent_test_out"

    def setup(self):
        """Create output directory."""
        self.test_output_dir.mkdir(exist_ok=True)

    def run(self, client, config, run_index: int) -> TestResult:
        """Run agent flow test."""
        start = time.time()
        warnings = []

        try:
            nonce = f"{time.time_ns()}-{run_index}"
            messages = []

            # Step 1: Simple greeting
            messages.append({
                "role": "user",
                "content": f"Test nonce: {nonce}. Reply exactly: Hi. How can I help you?"
            })

            response1 = client.post_message({
                "model": config.get("model"),
                "max_tokens": 768,
                "messages": messages
            })

            text1 = self._get_text(response1)

            if text1 != "Hi. How can I help you?":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 1: bad greeting, got '{text1}'",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "request_messages": messages,
                            "response": response1,
                            "validated_output": text1,
                        },
                    },
                )

            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": text1}]
            })

            # Step 2: Request tool call
            messages.append({
                "role": "user",
                "content": (
                    f"Test nonce: {nonce}. "
                    "Use the write_file tool to create a new file named main.cpp. "
                    "The file should be a minimal C++ hello world program. "
                    "Do not answer with text."
                )
            })

            tools = [
                {
                    "name": "write_file",
                    "description": "Write text to a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["file_path", "content"]
                    }
                }
            ]

            response2 = client.post_message({
                "model": config.get("model"),
                "max_tokens": 768,
                "tools": tools,
                "messages": messages
            })
            step_2_text_blocks = [
                block.get("text", "")
                for block in response2.get("content", [])
                if block.get("type") == "text" and block.get("text", "").strip()
            ]
            step_2_stray_text = "\n".join(step_2_text_blocks).strip()
            if step_2_stray_text:
                warnings.append(
                    "Model returned stray text alongside the step 2 tool_use; treated as caution pass."
                )

            # Find write_file tool_use
            tool_use = self._get_write_file_tool(response2)
            if tool_use is None:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: missing write_file tool_use",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "validated_output": text1,
                        },
                        "step_2": {
                            "request_messages": messages,
                            "tools": tools,
                            "response": response2,
                            "stray_text": step_2_stray_text,
                        },
                    },
                )

            tool_input = tool_use.get("input", {})
            file_path = tool_input.get("file_path")
            content = tool_input.get("content")

            if file_path != "main.cpp":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 2: wrong file_path '{file_path}'",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                        },
                    },
                )

            if not isinstance(content, str):
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: content was not a string",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                        },
                    },
                )

            if "int main" not in content:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: content missing 'int main'",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                        },
                    },
                )

            if "Hello" not in content and "hello" not in content:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: content missing hello text",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                        },
                    },
                )

            # Write file locally
            out_dir = self.test_output_dir / f"run_{run_index:03d}"
            out_dir.mkdir(exist_ok=True)
            local_file = out_dir / "main.cpp"
            local_file.write_text(content, encoding="utf-8")

            # Get tool_use_id for tool_result
            tool_use_id = tool_use.get("id")
            if tool_use_id is None:
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message="Step 2: tool_use block had no id",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                            "artifact_path": str(local_file),
                        },
                    },
                    artifacts=[str(local_file)],
                )

            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": response2.get("content", [])
            })

            # Step 3: Send tool result and ask for final text
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "The file main.cpp was written successfully."
                    },
                    {
                        "type": "text",
                        "text": "The tool succeeded. Now reply exactly: done"
                    }
                ]
            })

            response3 = client.post_message({
                "model": config.get("model"),
                "max_tokens": 768,
                "tools": tools,
                "messages": messages
            })

            text3 = self._get_text(response3)

            if text3 != "done":
                return TestResult(
                    test_name=self.name,
                    run_index=run_index,
                    passed=False,
                    duration_seconds=time.time() - start,
                    error_message=f"Step 3: bad final text '{text3}'",
                    details={
                        "purpose": "Multi-turn agent flow with tool usage",
                        "working_directory": str(Path.cwd()),
                        "nonce": nonce,
                        "step_1": {
                            "response": response1,
                            "validated_output": text1,
                        },
                        "step_2": {
                            "response": response2,
                            "stray_text": step_2_stray_text,
                            "tool_input": tool_input,
                            "artifact_path": str(local_file),
                        },
                        "step_3": {
                            "request_messages": messages,
                            "response": response3,
                            "validated_output": text3,
                        },
                    },
                    artifacts=[str(local_file)],
                )

            passed = True
            error_msg = None
            details = {
                "purpose": "Multi-turn agent flow with tool usage",
                "working_directory": str(Path.cwd()),
                "nonce": nonce,
                "step_1": {
                    "request_messages": [
                        {
                            "role": "user",
                            "content": f"Test nonce: {nonce}. Reply exactly: Hi. How can I help you?"
                        }
                    ],
                    "response": response1,
                    "validated_output": text1,
                },
                "step_2": {
                    "request_messages": messages[:3],
                    "tools": tools,
                    "response": response2,
                    "stray_text": step_2_stray_text,
                    "tool_input": tool_input,
                    "artifact_path": str(local_file),
                },
                "step_3": {
                    "request_messages": messages,
                    "response": response3,
                    "validated_output": text3,
                },
            }
            artifacts = [str(local_file)]

        except Exception as e:
            passed = False
            error_msg = str(e)
            details = {
                "purpose": "Multi-turn agent flow with tool usage",
                "working_directory": str(Path.cwd()),
            }
            artifacts = []

        duration = time.time() - start

        return TestResult(
            test_name=self.name,
            run_index=run_index,
            passed=passed,
            duration_seconds=duration,
            error_message=error_msg,
            details=details,
            artifacts=artifacts,
            warnings=warnings,
        )

    @staticmethod
    def _get_text(response):
        """Extract text from response."""
        text_blocks = [
            block.get("text", "")
            for block in response.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks).strip()

    @staticmethod
    def _get_write_file_tool(response):
        """Extract write_file tool_use from response."""
        tool_blocks = [
            block
            for block in response.get("content", [])
            if block.get("type") == "tool_use" and block.get("name") == "write_file"
        ]
        return tool_blocks[0] if len(tool_blocks) == 1 else None


def test_agent_flow():
    """Pytest entrypoint for the object-style test case."""
    run_test_case(AgentFlowTest)
