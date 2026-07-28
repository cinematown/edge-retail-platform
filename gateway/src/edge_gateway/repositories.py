"""Minimal MySQL repositories used by the checkout transaction."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .models import DeviceStatus, PricedCheckout


class ProductRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def get_unit_prices(self, skus: Sequence[str]) -> dict[str, int]:
        unique_skus = sorted(set(skus))
        if not unique_skus:
            return {}

        placeholders = ", ".join(["%s"] * len(unique_skus))
        cursor = self._connection.cursor()
        try:
            cursor.execute(
                f"SELECT sku, unit_price FROM products WHERE sku IN ({placeholders})",
                tuple(unique_skus),
            )
            return {str(sku): int(unit_price) for sku, unit_price in cursor}
        finally:
            cursor.close()


class CheckoutRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def event_exists(self, event_id: str) -> bool:
        cursor = self._connection.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM checkouts WHERE event_id = %s LIMIT 1",
                (event_id,),
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()


    def insert(self, checkout: PricedCheckout) -> None:
        event = checkout.event
        cursor = self._connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO checkouts (
                    checkout_id,
                    event_id,
                    device_id,
                    tracking_session_id,
                    cart_track_id,
                    payer_track_id,
                    total_item_count,
                    total_amount,
                    completed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.checkout_id,
                    event.event_id,
                    event.device_id,
                    event.tracking_session_id,
                    event.cart_track_id,
                    event.payer_track_id,
                    checkout.total_item_count,
                    checkout.total_amount,
                    checkout.completed_at_utc,
                ),
            )
            cursor.executemany(
                """
                INSERT INTO checkout_items (
                    checkout_id,
                    sku,
                    quantity,
                    unit_price,
                    subtotal_amount,
                    confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        event.checkout_id,
                        item.sku,
                        item.quantity,
                        item.unit_price,
                        item.subtotal_amount,
                        item.confidence,
                    )
                    for item in checkout.items
                ],
            )
        finally:
            cursor.close()


class DeviceStatusRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def upsert(self, status: DeviceStatus, observed_at_utc: Any) -> None:
        cursor = self._connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO device_status (
                    device_id,
                    status,
                    model_version,
                    tracking_session_id,
                    last_seen_at
                )
                VALUES (%s, %s, %s, %s, %s) AS incoming
                ON DUPLICATE KEY UPDATE
                    status = incoming.status,
                    model_version = incoming.model_version,
                    tracking_session_id = incoming.tracking_session_id,
                    last_seen_at = incoming.last_seen_at
                """,
                (
                    status.device_id,
                    status.status,
                    status.model_version,
                    status.tracking_session_id,
                    observed_at_utc,
                ),
            )
        finally:
            cursor.close()

