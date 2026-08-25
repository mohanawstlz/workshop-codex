"""Offline tests for the FastAPI chat service."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bedrock_chat.api import create_app
from bedrock_chat.config import Settings


class _FakeClient:
    """Record API conversations and return a deterministic reply."""

    instances: list["_FakeClient"] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history: list[dict[str, str]] = []
        self.sent: list[str] = []
        self.__class__.instances.append(self)

    def send(self, text: str) -> str:
        self.sent.append(text)
        return f"Reply to: {text}"


def _test_client() -> TestClient:
    _FakeClient.instances = []
    settings = Settings(model_id="openai.test-model", region="us-test-1")
    return TestClient(create_app(settings=settings, client_factory=_FakeClient))


def test_health_does_not_create_bedrock_client() -> None:
    client = _test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert _FakeClient.instances == []


def test_config_returns_public_model_settings() -> None:
    client = _test_client()

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {
        "model": "openai.test-model",
        "region": "us-test-1",
    }


def test_chat_passes_prior_history_and_latest_user_message() -> None:
    client = _test_client()
    messages = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Follow up"},
    ]

    response = client.post("/api/chat", json={"messages": messages})

    assert response.status_code == 200
    assert response.json() == {
        "message": {"role": "assistant", "content": "Reply to: Follow up"},
        "model": "openai.test-model",
        "region": "us-test-1",
    }
    instance = _FakeClient.instances[0]
    assert instance.history == messages[:-1]
    assert instance.sent == ["Follow up"]


def test_chat_rejects_invalid_conversation_order() -> None:
    client = _test_client()

    response = client.post(
        "/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "user", "content": "Another question"},
            ]
        },
    )

    assert response.status_code == 422
    assert _FakeClient.instances == []


def test_chat_rejects_blank_messages() -> None:
    client = _test_client()

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "   "}]},
    )

    assert response.status_code == 422


def test_chat_sanitizes_upstream_errors() -> None:
    class FailingClient(_FakeClient):
        def send(self, text: str) -> str:
            raise RuntimeError("secret upstream detail")

    settings = Settings(model_id="openai.test-model", region="us-test-1")
    client = TestClient(create_app(settings=settings, client_factory=FailingClient))

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 502
    assert "secret upstream detail" not in response.text
    assert response.json()["detail"].startswith("The model request failed")


def test_built_frontend_is_served_for_spa_routes(tmp_path: Path) -> None:
    index = tmp_path / "index.html"
    index.write_text("<html>built app</html>", encoding="utf-8")
    app = create_app(
        settings=Settings(),
        client_factory=_FakeClient,
        static_dir=tmp_path,
    )
    client = TestClient(app)

    response = client.get("/conversation/example")

    assert response.status_code == 200
    assert "built app" in response.text
