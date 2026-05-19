"""
HTTP client for OpenAI-compatible LLM API endpoints.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict


class LLMClient:
    """Client for communicating with OpenAI-compatible LLM endpoints."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: int = 120,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Initialize LLMClient.

        Args:
            endpoint: Full URL to /v1/messages endpoint
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Number of retries on transient failures
            retry_delay: Delay between retries in seconds
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def post_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the LLM and get response.

        Args:
            payload: Request payload (dict with model, messages, etc.)

        Returns:
            Parsed JSON response from server

        Raises:
            HTTPError: On HTTP errors (4xx, 5xx)
            ConnectionError: On network issues
            ValueError: On invalid JSON response
        """
        body_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint,
                    data=body_bytes,
                    method="POST",
                    headers={
                        "content-type": "application/json",
                        "anthropic-version": "2023-06-01",
                        "x-api-key": self.api_key,
                        "Connection": "close",
                    },
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    response_body = response.read().decode("utf-8")
                    return json.loads(response_body)

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"HTTP {e.code}: {error_body[:200]}"
                ) from e

            except urllib.error.URLError as e:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                raise ConnectionError(
                    f"Failed to connect to {self.endpoint}: {e.reason}"
                ) from e

            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in response: {response_body[:200]}"
                ) from e

            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                raise

        raise RuntimeError("Unexpected error in post_message")
