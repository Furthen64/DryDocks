"""
Test 01: Simple pong connectivity test.

Tests basic LLM connectivity by sending a simple prompt and verifying a "pong" response.
"""

import time
from drydocks.tests.base import BaseTest, TestResult


class PongTest(BaseTest):
    """Simple pong test - basic connectivity check."""

    name = "pong"
    description = "Simple pong connectivity test"

    def run(self, client, config, run_index: int) -> TestResult:
        """Run pong test."""
        start = time.time()

        try:
            payload = {
                "model": config.get("model"),
                "max_tokens": 256,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with exactly: pong"
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

            # Check if response is exactly "pong"
            if text == "pong":
                passed = True
                error_msg = None
            else:
                passed = False
                error_msg = f"Expected 'pong', got '{text}'"

        except Exception as e:
            passed = False
            error_msg = str(e)

        duration = time.time() - start

        return TestResult(
            test_name=self.name,
            run_index=run_index,
            passed=passed,
            duration_seconds=duration,
            error_message=error_msg,
        )
