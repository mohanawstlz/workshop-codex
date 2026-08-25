"""FastAPI application for the Bedrock chat web client."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .client import BedrockChatClient
from .config import Settings
from .orders import create_order_router

LOGGER = logging.getLogger(__name__)
DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
ClientFactory = Callable[[Settings], BedrockChatClient]


class ChatMessage(BaseModel):
    """A user or assistant message exchanged by the web client."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=50_000)


class ChatRequest(BaseModel):
    """A complete conversation ending with the new user message."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_conversation(self) -> "ChatRequest":
        """Require alternating user and assistant messages ending with the user."""
        expected_role = "user"
        for message in self.messages:
            if not message.content.strip():
                raise ValueError("message content cannot be blank")
            if message.role != expected_role:
                raise ValueError(f"expected a {expected_role} message")
            expected_role = "assistant" if expected_role == "user" else "user"
        if self.messages[-1].role != "user":
            raise ValueError("conversation must end with a user message")
        return self


class ChatResponse(BaseModel):
    """The assistant reply and effective model metadata."""

    message: ChatMessage
    model: str
    region: str


class AppConfigResponse(BaseModel):
    """Public runtime configuration shown by the web client."""

    model: str
    region: str


def create_app(
    settings: Settings | None = None,
    client_factory: ClientFactory = BedrockChatClient,
    static_dir: Path | None = None,
) -> FastAPI:
    """Create a web application with injectable settings and Bedrock client."""
    resolved_settings = settings or Settings.from_env()
    app = FastAPI(
        title="Bedrock Chat API",
        description="Chat with OpenAI GPT models through Amazon Bedrock.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["DELETE", "GET", "PATCH", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    app.include_router(create_order_router())

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Return a lightweight readiness response without contacting AWS."""
        return {"status": "ok"}

    @app.get("/api/config", response_model=AppConfigResponse)
    def config() -> AppConfigResponse:
        """Return non-secret model configuration for the interface."""
        return AppConfigResponse(
            model=resolved_settings.model_id,
            region=resolved_settings.region,
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        """Send the validated conversation to Bedrock and return its next reply."""
        try:
            client = client_factory(resolved_settings)
            client.history = [
                message.model_dump() for message in request.messages[:-1]
            ]
            reply = client.send(request.messages[-1].content)
        except Exception as exc:  # noqa: BLE001 - convert upstream failures to HTTP
            LOGGER.exception("Bedrock chat request failed")
            raise HTTPException(
                status_code=502,
                detail="The model request failed. Check AWS credentials and model access.",
            ) from exc

        return ChatResponse(
            message=ChatMessage(role="assistant", content=reply),
            model=resolved_settings.model_id,
            region=resolved_settings.region,
        )

    frontend_dir = static_dir if static_dir is not None else DEFAULT_STATIC_DIR
    index_file = frontend_dir / "index.html"
    assets_dir = frontend_dir / "assets"
    if index_file.is_file():
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            """Serve the React single-page application for non-API routes."""
            return FileResponse(index_file)

    return app


app = create_app()
