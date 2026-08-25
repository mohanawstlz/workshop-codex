"""Offline tests for the Order REST API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bedrock_chat.api import create_app
from bedrock_chat.config import Settings


def _test_client() -> TestClient:
    return TestClient(create_app(settings=Settings()))


def _order_payload() -> dict[str, object]:
    return {
        "customer_id": "customer-123",
        "items": [
            {"sku": "keyboard", "quantity": 1},
            {"sku": "mouse", "quantity": 2},
        ],
        "shipping_address": "100 Main Street",
    }


def test_order_crud_lifecycle() -> None:
    client = _test_client()
    payload = _order_payload()

    created_response = client.post("/api/orders", json=payload)

    assert created_response.status_code == 201
    created = created_response.json()
    order_id = created["id"]
    assert created_response.headers["location"] == f"/api/orders/{order_id}"
    assert created["customer_id"] == payload["customer_id"]
    assert created["items"] == payload["items"]
    assert created["shipping_address"] == payload["shipping_address"]
    assert created["status"] == "pending"
    assert created["created_at"] == created["updated_at"]

    list_response = client.get("/api/orders")
    assert list_response.status_code == 200
    assert list_response.json() == [created]

    get_response = client.get(f"/api/orders/{order_id}")
    assert get_response.status_code == 200
    assert get_response.json() == created

    update_response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "shipping_address": "200 Market Street",
            "status": "processing",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["shipping_address"] == "200 Market Street"
    assert updated["status"] == "processing"
    assert updated["items"] == payload["items"]
    assert updated["updated_at"] >= updated["created_at"]

    replacement = {
        "customer_id": "customer-456",
        "items": [{"sku": "monitor", "quantity": 3}],
        "shipping_address": "300 State Street",
        "status": "shipped",
    }
    replace_response = client.put(
        f"/api/orders/{order_id}",
        json=replacement,
    )
    assert replace_response.status_code == 200
    replaced = replace_response.json()
    assert replaced["customer_id"] == replacement["customer_id"]
    assert replaced["items"] == replacement["items"]
    assert replaced["shipping_address"] == replacement["shipping_address"]
    assert replaced["status"] == replacement["status"]
    assert replaced["created_at"] == created["created_at"]

    delete_response = client.delete(f"/api/orders/{order_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get(f"/api/orders/{order_id}").status_code == 404
    assert client.get("/api/orders").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {
            "customer_id": " ",
            "items": [{"sku": "keyboard", "quantity": 1}],
            "shipping_address": "100 Main Street",
        },
        {
            "customer_id": "customer-123",
            "items": [],
            "shipping_address": "100 Main Street",
        },
        {
            "customer_id": "customer-123",
            "items": [{"sku": "keyboard", "quantity": 0}],
            "shipping_address": "100 Main Street",
        },
        {
            "customer_id": "customer-123",
            "items": [{"sku": " ", "quantity": 1}],
            "shipping_address": "100 Main Street",
        },
        {
            "customer_id": "customer-123",
            "items": [{"sku": "keyboard", "quantity": 1}],
            "shipping_address": " ",
        },
    ],
)
def test_create_order_rejects_invalid_payloads(payload: dict[str, object]) -> None:
    client = _test_client()

    response = client.post("/api/orders", json=payload)

    assert response.status_code == 422
    assert client.get("/api/orders").json() == []


def test_update_order_rejects_empty_or_invalid_payload() -> None:
    client = _test_client()
    order_id = client.post("/api/orders", json=_order_payload()).json()["id"]

    assert client.patch(f"/api/orders/{order_id}", json={}).status_code == 422
    assert (
        client.patch(
            f"/api/orders/{order_id}",
            json={"status": "not-a-real-status"},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/orders/{order_id}",
            json={"shipping_address": None},
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/orders/{order_id}",
            json={
                "customer_id": "customer-456",
                "items": [{"sku": "monitor", "quantity": 1}],
                "shipping_address": "200 Market Street",
            },
        ).status_code
        == 422
    )


def test_order_endpoints_return_not_found_for_missing_order() -> None:
    client = _test_client()
    missing_id = uuid4()

    get_response = client.get(f"/api/orders/{missing_id}")
    update_response = client.patch(
        f"/api/orders/{missing_id}",
        json={"status": "cancelled"},
    )
    replace_payload = {
        **_order_payload(),
        "status": "cancelled",
    }
    replace_response = client.put(f"/api/orders/{missing_id}", json=replace_payload)
    delete_response = client.delete(f"/api/orders/{missing_id}")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Order not found"}
    assert update_response.status_code == 404
    assert update_response.json() == {"detail": "Order not found"}
    assert replace_response.status_code == 404
    assert replace_response.json() == {"detail": "Order not found"}
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Order not found"}
