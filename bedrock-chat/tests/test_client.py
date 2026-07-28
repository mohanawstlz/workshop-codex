"""Unit tests for the pure helpers and the client's conversation handling.

These tests never touch AWS: BedrockChatClient accepts an injected fake client,
and the helpers are plain functions. Run with `pytest` from the bedrock-chat
folder.
"""

import pytest

from bedrock_chat.client import BedrockChatClient, build_message, extract_text
from bedrock_chat.config import Settings


def test_build_message_shape():
    assert build_message("user", "hi") == {
        "role": "user",
        "content": [{"text": "hi"}],
    }


def test_build_message_rejects_bad_role():
    with pytest.raises(ValueError):
        build_message("system", "nope")


def test_extract_text_joins_blocks():
    response = {
        "output": {"message": {"content": [{"text": "Hello "}, {"text": "world"}]}}
    }
    assert extract_text(response) == "Hello world"


def test_extract_text_handles_empty_response():
    assert extract_text({}) == ""


class _FakeBedrock:
    """Minimal stand-in for the boto3 bedrock-runtime client."""

    def __init__(self, reply="pong"):
        self.reply = reply
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self.reply}]}}}


def test_send_records_history_and_returns_reply():
    fake = _FakeBedrock(reply="pong")
    client = BedrockChatClient(settings=Settings(), client=fake)

    reply = client.send("ping")

    assert reply == "pong"
    # One user turn + one assistant turn recorded.
    assert client.history == [
        {"role": "user", "content": [{"text": "ping"}]},
        {"role": "assistant", "content": [{"text": "pong"}]},
    ]
    # The full history is sent on each call.
    assert fake.calls[0]["messages"] == client.history
    assert fake.calls[0]["modelId"] == Settings().model_id


def test_send_passes_inference_config():
    fake = _FakeBedrock()
    settings = Settings(max_tokens=256, temperature=0.1)
    client = BedrockChatClient(settings=settings, client=fake)

    client.send("hi")

    cfg = fake.calls[0]["inferenceConfig"]
    assert cfg == {"maxTokens": 256, "temperature": 0.1}
