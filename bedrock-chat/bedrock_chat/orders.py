"""REST models, storage, and routes for the Order resource."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderStatus(str, Enum):
    """Supported states in the Order lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """A product and quantity included in an Order."""

    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=10_000)

    @field_validator("sku")
    @classmethod
    def strip_sku(cls, value: str) -> str:
        """Normalize and reject blank product identifiers."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("sku cannot be blank")
        return normalized


class OrderCreate(BaseModel):
    """Fields accepted when creating an Order."""

    customer_id: str = Field(min_length=1, max_length=100)
    items: list[OrderItem] = Field(min_length=1, max_length=100)
    shipping_address: str = Field(min_length=1, max_length=500)

    @field_validator("customer_id", "shipping_address")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Normalize and reject blank required text fields."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be blank")
        return normalized


class OrderUpdate(BaseModel):
    """Fields accepted when partially updating an Order."""

    customer_id: str | None = Field(default=None, min_length=1, max_length=100)
    items: list[OrderItem] | None = Field(default=None, min_length=1, max_length=100)
    shipping_address: str | None = Field(default=None, min_length=1, max_length=500)
    status: OrderStatus | None = None

    @field_validator("customer_id", "shipping_address")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        """Normalize and reject blank text when an optional field is provided."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be blank")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "OrderUpdate":
        """Require at least one field in a partial update."""
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if any(getattr(self, field_name) is None for field_name in self.model_fields_set):
            raise ValueError("updated fields cannot be null")
        return self


class OrderReplace(OrderCreate):
    """Fields required when replacing an Order."""

    status: OrderStatus


class Order(BaseModel):
    """A stored Order returned by the API."""

    id: UUID
    customer_id: str
    items: list[OrderItem]
    shipping_address: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderStore:
    """Thread-safe in-memory storage for Orders."""

    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}
        self._lock = Lock()

    def create(self, payload: OrderCreate) -> Order:
        """Create and store an Order."""
        now = datetime.now(timezone.utc)
        order = Order(
            id=uuid4(),
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        with self._lock:
            self._orders[order.id] = order
        return order.model_copy(deep=True)

    def list(self) -> list[Order]:
        """Return all Orders in creation order."""
        with self._lock:
            orders = sorted(
                self._orders.values(),
                key=lambda order: (order.created_at, str(order.id)),
            )
            return [order.model_copy(deep=True) for order in orders]

    def get(self, order_id: UUID) -> Order | None:
        """Return an Order by identifier, or None when it does not exist."""
        with self._lock:
            order = self._orders.get(order_id)
            return order.model_copy(deep=True) if order is not None else None

    def update(self, order_id: UUID, payload: OrderUpdate) -> Order | None:
        """Apply a partial update to an Order, if it exists."""
        with self._lock:
            current = self._orders.get(order_id)
            if current is None:
                return None
            changes = payload.model_dump(exclude_unset=True)
            changes["updated_at"] = datetime.now(timezone.utc)
            updated = current.model_copy(update=changes, deep=True)
            self._orders[order_id] = updated
            return updated.model_copy(deep=True)

    def replace(self, order_id: UUID, payload: OrderReplace) -> Order | None:
        """Replace all mutable fields on an Order, if it exists."""
        with self._lock:
            current = self._orders.get(order_id)
            if current is None:
                return None
            replaced = Order(
                id=current.id,
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc),
                **payload.model_dump(),
            )
            self._orders[order_id] = replaced
            return replaced.model_copy(deep=True)

    def delete(self, order_id: UUID) -> bool:
        """Delete an Order and report whether it existed."""
        with self._lock:
            return self._orders.pop(order_id, None) is not None


def create_order_router(store: OrderStore | None = None) -> APIRouter:
    """Create an Order CRUD router backed by the provided store."""
    order_store = store or OrderStore()
    router = APIRouter(prefix="/api/orders", tags=["orders"])

    @router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
    def create_order(payload: OrderCreate, response: Response) -> Order:
        """Create an Order and return its generated identifier."""
        order = order_store.create(payload)
        response.headers["Location"] = f"/api/orders/{order.id}"
        return order

    @router.get("", response_model=list[Order])
    def list_orders() -> list[Order]:
        """List all Orders."""
        return order_store.list()

    @router.get("/{order_id}", response_model=Order)
    def get_order(order_id: UUID) -> Order:
        """Return one Order by identifier."""
        order = order_store.get(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @router.patch("/{order_id}", response_model=Order)
    def update_order(order_id: UUID, payload: OrderUpdate) -> Order:
        """Partially update an existing Order."""
        order = order_store.update(order_id, payload)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @router.put("/{order_id}", response_model=Order)
    def replace_order(order_id: UUID, payload: OrderReplace) -> Order:
        """Replace all mutable fields on an existing Order."""
        order = order_store.replace(order_id, payload)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_order(order_id: UUID) -> Response:
        """Delete an existing Order."""
        if not order_store.delete(order_id):
            raise HTTPException(status_code=404, detail="Order not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
