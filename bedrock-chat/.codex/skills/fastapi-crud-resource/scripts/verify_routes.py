#!/usr/bin/env python3
"""Verify the route contract for a FastAPI CRUD resource."""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute


@dataclass(frozen=True)
class ExpectedRoute:
    """A route required by the resource contract."""

    method: str
    path: str
    status_code: int
    requires_response_model: bool = True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify methods, status codes, response models, and OpenAPI.",
    )
    parser.add_argument(
        "--app",
        required=True,
        help="FastAPI application import in module:attribute form",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Collection path, for example /api/orders",
    )
    parser.add_argument(
        "--without-patch",
        action="store_true",
        help="Do not require the PATCH operation",
    )
    parser.add_argument(
        "--without-put",
        action="store_true",
        help="Do not require the PUT operation",
    )
    return parser.parse_args()


def load_app(import_path: str) -> FastAPI:
    """Import and return a FastAPI application."""
    module_name, separator, attribute_name = import_path.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError("--app must use module:attribute form")
    repository_root = str(Path.cwd())
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    module = importlib.import_module(module_name)
    app = getattr(module, attribute_name, None)
    if not isinstance(app, FastAPI):
        raise TypeError(f"{import_path} does not resolve to a FastAPI application")
    return app


def normalize_path(path: str) -> str:
    """Normalize trailing slashes and path parameter names."""
    normalized = path.rstrip("/") or "/"
    return re.sub(r"\{[^}]+\}", "{}", normalized)


def expected_routes(
    prefix: str,
    *,
    include_patch: bool,
    include_put: bool,
) -> list[ExpectedRoute]:
    """Build the expected CRUD route contract."""
    collection_path = normalize_path(prefix)
    item_path = f"{collection_path}/{{}}"
    routes = [
        ExpectedRoute("POST", collection_path, 201),
        ExpectedRoute("GET", collection_path, 200),
        ExpectedRoute("GET", item_path, 200),
    ]
    if include_patch:
        routes.append(ExpectedRoute("PATCH", item_path, 200))
    if include_put:
        routes.append(ExpectedRoute("PUT", item_path, 200))
    routes.append(
        ExpectedRoute(
            "DELETE",
            item_path,
            204,
            requires_response_model=False,
        )
    )
    return routes


def find_route(
    routes: list[tuple[str, APIRoute]],
    expected: ExpectedRoute,
) -> APIRoute | None:
    """Find a route matching an expected method and normalized path."""
    for path, route in routes:
        if (
            expected.method in route.methods
            and normalize_path(path) == expected.path
        ):
            return route
    return None


def collect_api_routes(
    routes: list[object],
    prefix: str = "",
) -> list[tuple[str, APIRoute]]:
    """Collect API routes, including routers retained lazily by FastAPI."""
    collected: list[tuple[str, APIRoute]] = []
    for route in routes:
        if isinstance(route, APIRoute):
            collected.append((f"{prefix}{route.path}", route))
            continue
        original_router = getattr(route, "original_router", None)
        include_context = getattr(route, "include_context", None)
        if original_router is not None and include_context is not None:
            nested_prefix = f"{prefix}{include_context.prefix}"
            collected.extend(collect_api_routes(original_router.routes, nested_prefix))
    return collected


def verify_app(
    app: FastAPI,
    prefix: str,
    *,
    include_patch: bool = True,
    include_put: bool = True,
) -> list[str]:
    """Return contract violations found in a FastAPI application."""
    errors: list[str] = []
    api_routes = collect_api_routes(app.routes)
    for expected in expected_routes(
        prefix,
        include_patch=include_patch,
        include_put=include_put,
    ):
        route = find_route(api_routes, expected)
        label = f"{expected.method} {expected.path}"
        if route is None:
            errors.append(f"missing route: {label}")
            continue
        actual_status = route.status_code or 200
        if actual_status != expected.status_code:
            errors.append(
                f"{label} declares status {actual_status}, expected {expected.status_code}"
            )
        if expected.requires_response_model and route.response_model is None:
            errors.append(f"{label} has no response model")

    try:
        app.openapi()
    except Exception as exc:  # noqa: BLE001 - report arbitrary schema failures
        errors.append(f"OpenAPI generation failed: {exc}")
    return errors


def main() -> int:
    """Run route verification and return a process exit code."""
    args = parse_args()
    try:
        app = load_app(args.app)
        errors = verify_app(
            app,
            args.prefix,
            include_patch=not args.without_patch,
            include_put=not args.without_put,
        )
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Verified CRUD routes under {normalize_path(args.prefix)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
