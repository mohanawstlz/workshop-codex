"""Thin wrapper around the Amazon Bedrock Converse API.

The chat app uses Bedrock's Converse API because it gives a single, model-
agnostic request/response shape for multi-turn conversations. `boto3` is only
imported when a client is actually created, so the pure helpers in this module
(message building, response parsing) can be unit tested without AWS access.
"""

from __future__ import annotations

from typing import Any

from .config import Settings


def build_message(role: str, text: str) -> dict[str, Any]:
    """Build a single Converse API message.

    Converse messages carry a role ("user" or "assistant") and a list of
    content blocks. For plain chat we only ever send one text block.
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")
    return {"role": role, "content": [{"text": text}]}


def extract_text(response: dict[str, Any]) -> str:
    """Pull the assistant's reply text out of a Converse API response.

    The reply lives at output.message.content[*].text. Multiple text blocks
    are joined so nothing is silently dropped.
    """
    message = response.get("output", {}).get("message", {})
    parts = [block["text"] for block in message.get("content", []) if "text" in block]
    return "".join(parts)


class BedrockChatClient:
    """Maintains conversation history and calls Bedrock Converse."""

    def __init__(self, settings: Settings | None = None, client: Any = None) -> None:
        self.settings = settings or Settings.from_env()
        # Allow injecting a fake client in tests; only touch boto3 otherwise.
        if client is not None:
            self._client = client
        else:
            import boto3  # imported lazily so tests need no AWS/boto3 setup

            self._client = boto3.client(
                "bedrock-runtime", region_name=self.settings.region
            )
        self.history: list[dict[str, Any]] = []

    def send(self, text: str) -> str:
        """Send a user turn, record the exchange, and return the reply text."""
        self.history.append(build_message("user", text))
        response = self._client.converse(
            modelId=self.settings.model_id,
            messages=self.history,
            inferenceConfig={
                "maxTokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
            },
        )
        reply = extract_text(response)
        self.history.append(build_message("assistant", reply))
        return reply
