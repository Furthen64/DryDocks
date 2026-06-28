"""OpenAI-compatible API client used by the DryDocks tests."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class OpenAICompatClient:
    """Minimal client adapter for OpenAI-compatible chat endpoints."""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def post_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one chat completion request and normalize the response."""
        request_payload = self._build_request_payload(payload)
        raw_response = self._post_json(
            f"{self.base_url}/chat/completions",
            request_payload,
        )
        return self._normalize_response(raw_response)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(url, data=body, method="POST")
        http_request.add_header("Content-Type", "application/json")
        http_request.add_header("Accept", "application/json")
        if self.api_key:
            http_request.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with request.urlopen(http_request, timeout=60) as response:
                return json.load(response)
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from {url}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc

    def _build_request_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload: dict[str, Any] = {
            "model": payload["model"],
            "messages": self._convert_messages(payload.get("messages", [])),
        }

        if "max_tokens" in payload:
            request_payload["max_tokens"] = payload["max_tokens"]

        tools = payload.get("tools")
        if tools:
            request_payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {"type": "object"}),
                    },
                }
                for tool in tools
            ]

        return request_payload

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []

        for message in messages:
            role = message["role"]
            content = message.get("content", "")

            if isinstance(content, str):
                converted.append({"role": role, "content": content})
                continue

            if role == "assistant":
                converted.append(self._convert_assistant_message(content))
                continue

            if role == "user":
                converted.extend(self._convert_user_blocks(content))
                continue

            raise ValueError(f"Unsupported message role: {role}")

        return converted

    def _convert_assistant_message(self, blocks: list[dict[str, Any]]) -> dict[str, Any]:
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in blocks:
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    {
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(part for part in text_parts if part).strip(),
        }
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
            if not assistant_message["content"]:
                assistant_message["content"] = None
        return assistant_message

    def _convert_user_blocks(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        text_parts: list[str] = []

        for block in blocks:
            block_type = block.get("type")
            if block_type == "tool_result":
                tool_content = block.get("content", "")
                if isinstance(tool_content, list):
                    tool_content = "\n".join(str(item) for item in tool_content)
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": str(tool_content),
                    }
                )
            elif block_type == "text":
                text_parts.append(block.get("text", ""))

        if text_parts:
            converted.append(
                {
                    "role": "user",
                    "content": "\n".join(part for part in text_parts if part).strip(),
                }
            )

        return converted

    def _normalize_response(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not choices:
            raise RuntimeError(f"Missing choices in response: {response}")

        message = choices[0].get("message", {})
        content_blocks: list[dict[str, Any]] = []

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            content_blocks.append({"type": "text", "text": content.strip()})
        elif isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            text = "\n".join(part for part in text_parts if part).strip()
            if text:
                content_blocks.append({"type": "text", "text": text})

        for tool_call in message.get("tool_calls", []) or []:
            function_payload = tool_call.get("function", {})
            arguments = function_payload.get("arguments", "{}")
            try:
                parsed_arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                parsed_arguments = {}

            content_blocks.append(
                {
                    "type": "tool_use",
                    "id": tool_call.get("id"),
                    "name": function_payload.get("name"),
                    "input": parsed_arguments,
                }
            )

        return {"content": content_blocks}
