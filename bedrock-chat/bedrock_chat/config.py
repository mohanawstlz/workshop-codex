"""Runtime configuration for the bedrock-chat app.

Settings come from environment variables so the app works with the AWS
credential chain and the region used elsewhere in the workshop. Nothing here
requires AWS access, which keeps the settings easy to unit test.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Defaults line up with the workshop's ~/.codex/config.toml.
DEFAULT_MODEL_ID = "openai.gpt-5.5"
DEFAULT_REGION = "us-west-2"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7


@dataclass
class Settings:
    """Resolved settings for a chat session."""

    model_id: str = DEFAULT_MODEL_ID
    region: str = DEFAULT_REGION
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Settings":
        """Build Settings from environment variables (defaults to os.environ)."""
        env = os.environ if env is None else env
        region = (
            env.get("BEDROCK_REGION")
            or env.get("AWS_REGION")
            or env.get("AWS_DEFAULT_REGION")
            or DEFAULT_REGION
        )
        return cls(
            model_id=env.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
            region=region,
            max_tokens=int(env.get("BEDROCK_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
            temperature=float(env.get("BEDROCK_TEMPERATURE", DEFAULT_TEMPERATURE)),
        )
