"""Tests for the interactive terminal entry point."""

from __future__ import annotations

import builtins
from typing import ClassVar

import pytest

from bedrock_chat import __main__ as app


class _FakeClient:
    """Record construction and messages without touching AWS."""

    instances: ClassVar[list["_FakeClient"]] = []

    def __init__(self, settings):
        self.settings = settings
        self.messages = []
        self.__class__.instances.append(self)

    def send(self, text):
        self.messages.append(text)
        return f"reply to {text}"


def test_main_reuses_one_client_and_ignores_blank_and_exit(monkeypatch, capsys):
    _FakeClient.instances = []
    inputs = iter(["", "first question", "second question", "QuIt"])
    monkeypatch.setattr(app, "BedrockChatClient", _FakeClient)
    monkeypatch.setattr(builtins, "input", lambda prompt: next(inputs))

    assert app.main() == 0

    assert len(_FakeClient.instances) == 1
    assert _FakeClient.instances[0].messages == [
        "first question",
        "second question",
    ]
    output = capsys.readouterr().out
    assert "gpt> reply to first question" in output
    assert "gpt> reply to second question" in output


def test_main_continues_after_send_error(monkeypatch, capsys):
    class FailOnceClient(_FakeClient):
        def send(self, text):
            self.messages.append(text)
            if len(self.messages) == 1:
                raise RuntimeError("temporary API error")
            return "recovered"

    FailOnceClient.instances = []
    inputs = iter(["first question", "second question", "exit"])
    monkeypatch.setattr(app, "BedrockChatClient", FailOnceClient)
    monkeypatch.setattr(builtins, "input", lambda prompt: next(inputs))

    assert app.main() == 0

    assert len(FailOnceClient.instances) == 1
    assert FailOnceClient.instances[0].messages == [
        "first question",
        "second question",
    ]
    captured = capsys.readouterr()
    assert "[error] temporary API error" in captured.err
    assert "gpt> recovered" in captured.out


@pytest.mark.parametrize("interrupt", [EOFError, KeyboardInterrupt])
def test_main_exits_cleanly_on_input_interrupt(monkeypatch, capsys, interrupt):
    _FakeClient.instances = []
    monkeypatch.setattr(app, "BedrockChatClient", _FakeClient)

    def interrupt_input(prompt):
        raise interrupt

    monkeypatch.setattr(builtins, "input", interrupt_input)

    assert app.main() == 0
    assert len(_FakeClient.instances) == 1
    assert _FakeClient.instances[0].messages == []
    assert capsys.readouterr().err == ""
