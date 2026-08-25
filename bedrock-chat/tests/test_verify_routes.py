"""Tests for the project-local FastAPI route verifier."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_route_verifier_supports_included_fastapi_routers() -> None:
    """Verify routes nested by newer FastAPI versions are discovered."""
    repository_root = Path(__file__).resolve().parent.parent
    script = (
        repository_root
        / ".codex"
        / "skills"
        / "fastapi-crud-resource"
        / "scripts"
        / "verify_routes.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--app",
            "bedrock_chat.api:app",
            "--prefix",
            "/api/orders",
        ],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "Verified CRUD routes under /api/orders"
