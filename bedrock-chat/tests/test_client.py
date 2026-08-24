"""Unit tests for the pure helpers and the client's conversation handling.

These tests never touch AWS: BedrockChatClient accepts an injected fake
transport, and the helpers are plain functions. Run with `pytest` from the
bedrock-chat folder.
"""

import json

import pytest

from bedrock_chat.client import BedrockChatClient, build_message, extract_text
from bedrock_chat.config import Settings


def test_build_message_shape():
    assert build_message("user", "hi") == {"role": "user", "content": "hi"}


def test_build_message_rejects_bad_role():
    with pytest.raises(ValueError):
        build_message("system", "nope")


def test_extract_text_joins_output_text_blocks():
    response = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Hello "},
                    {"type": "output_text", "text": "world"},
                ],
            }
        ]
    }
    assert extract_text(response) == "Hello world"


def test_extract_text_skips_reasoning_items():
    # Reasoning items and non-output_text blocks must not leak into the reply.
    response = {
        "output": [
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "hmm"}]},
            {"type": "message", "content": [{"type": "output_text", "text": "READY"}]},
        ]
    }
    assert extract_text(response) == "READY"


def test_extract_text_handles_empty_response():
    assert extract_text({}) == ""


class _FakeTransport:
    """Records requests and returns a canned responses-API payload."""

    def __init__(self, reply="pong", replies=None):
        self.replies = iter(replies if replies is not None else [reply])
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(body)})
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": next(self.replies)}],
                }
            ]
        }


def test_send_records_history_and_returns_reply():
    fake = _FakeTransport(reply="pong")
    client = BedrockChatClient(settings=Settings(), transport=fake)

    reply = client.send("ping")

    assert reply == "pong"
    # One user turn + one assistant turn recorded, in responses-API shape.
    assert client.history == [
        {"role": "user", "content": "ping"},
        {"role": "assistant", "content": "pong"},
    ]
    # The request `input` carries the conversation up to (and including) this
    # user turn; the assistant reply is appended to history afterward.
    sent = fake.calls[0]["body"]
    assert sent["input"] == [{"role": "user", "content": "ping"}]
    assert sent["model"] == Settings().model_id


def test_send_includes_completed_history_on_later_turns():
    fake = _FakeTransport(replies=["first reply", "second reply"])
    client = BedrockChatClient(settings=Settings(), transport=fake)

    assert client.send("first question") == "first reply"
    assert client.send("second question") == "second reply"

    assert fake.calls[0]["body"]["input"] == [
        {"role": "user", "content": "first question"},
    ]
    assert fake.calls[1]["body"]["input"] == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first reply"},
        {"role": "user", "content": "second question"},
    ]
    assert client.history == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first reply"},
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second reply"},
    ]


def test_client_instances_have_independent_history():
    first = BedrockChatClient(
        settings=Settings(), transport=_FakeTransport(reply="first reply")
    )
    second = BedrockChatClient(
        settings=Settings(), transport=_FakeTransport(reply="second reply")
    )

    first.send("first question")

    assert first.history == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first reply"},
    ]
    assert second.history == []


def test_send_transport_failure_leaves_history_unchanged():
    def failing_transport(url, headers, body):
        raise RuntimeError("network unavailable")

    client = BedrockChatClient(settings=Settings(), transport=failing_transport)

    with pytest.raises(RuntimeError, match="network unavailable"):
        client.send("do not remember this")

    assert client.history == []


def test_send_response_processing_failure_leaves_history_unchanged(monkeypatch):
    fake = _FakeTransport(reply="unused")
    client = BedrockChatClient(settings=Settings(), transport=fake)

    def fail_to_extract(response):
        raise ValueError("malformed response")

    monkeypatch.setattr("bedrock_chat.client.extract_text", fail_to_extract)

    with pytest.raises(ValueError, match="malformed response"):
        client.send("do not remember this")

    assert client.history == []


def test_success_after_failure_excludes_failed_turn():
    class FailOnceTransport:
        def __init__(self):
            self.calls = []

        def __call__(self, url, headers, body):
            self.calls.append(json.loads(body))
            if len(self.calls) == 1:
                raise RuntimeError("temporary failure")
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "recovered"}],
                    }
                ]
            }

    fake = FailOnceTransport()
    client = BedrockChatClient(settings=Settings(), transport=fake)

    with pytest.raises(RuntimeError, match="temporary failure"):
        client.send("failed turn")
    assert client.send("successful turn") == "recovered"

    assert fake.calls[1]["input"] == [
        {"role": "user", "content": "successful turn"},
    ]
    assert client.history == [
        {"role": "user", "content": "successful turn"},
        {"role": "assistant", "content": "recovered"},
    ]


def test_send_empty_text_response_leaves_history_unchanged():
    client = BedrockChatClient(
        settings=Settings(), transport=lambda url, headers, body: {"output": []}
    )

    with pytest.raises(ValueError, match="no output text"):
        client.send("do not remember this")

    assert client.history == []


def test_send_preserves_unicode_multiline_and_large_text():
    fake = _FakeTransport(reply="received")
    client = BedrockChatClient(settings=Settings(), transport=fake)
    message = "こんにちは\nsecond line\n" + ("x" * 4096)

    client.send(message)

    assert fake.calls[0]["body"]["input"] == [
        {"role": "user", "content": message},
    ]
    assert client.history[0] == {"role": "user", "content": message}


def test_send_interruption_leaves_history_unchanged():
    def interrupted_transport(url, headers, body):
        raise KeyboardInterrupt

    client = BedrockChatClient(settings=Settings(), transport=interrupted_transport)

    with pytest.raises(KeyboardInterrupt):
        client.send("interrupted turn")

    assert client.history == []


def test_send_targets_regional_responses_endpoint():
    fake = _FakeTransport()
    client = BedrockChatClient(settings=Settings(region="us-east-2"), transport=fake)

    client.send("hi")

    assert (
        fake.calls[0]["url"]
        == "https://bedrock-mantle.us-east-2.api.aws/openai/v1/responses"
    )


def test_send_passes_inference_params():
    fake = _FakeTransport()
    settings = Settings(max_tokens=256, temperature=0.1)
    client = BedrockChatClient(settings=settings, transport=fake)

    client.send("hi")

    sent = fake.calls[0]["body"]
    assert sent["max_output_tokens"] == 256
    assert sent["temperature"] == 0.1


def test_send_omits_temperature_by_default():
    # GPT-5.x reasoning models reject `temperature`; it must not be sent unless set.
    fake = _FakeTransport()
    client = BedrockChatClient(settings=Settings(), transport=fake)

    client.send("hi")

    assert "temperature" not in fake.calls[0]["body"]
