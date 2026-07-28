"""Checkout pricing and atomic persistence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timezone
from typing import Any

import mysql.connector

from .database import Database
from .models import (
    CheckoutCompleted,
    PricedCheckout,
    PricedCheckoutItem,
)
from .repositories import CheckoutRepository, ProductRepository


MYSQL_UNSIGNED_INT_MAX = 4_294_967_295


class CheckoutProcessingError(ValueError):
    """Business rule failure while processing a checkout."""


class UnknownSkuError(CheckoutProcessingError):
    def __init__(self, skus: list[str]) -> None:
        super().__init__(f"unknown SKU: {', '.join(skus)}")
        self.skus = skus


class CheckoutAmountOverflowError(CheckoutProcessingError):
    """Calculated totals do not fit the current MySQL schema."""


class DuplicateEventError(CheckoutProcessingError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"event already processed: {event_id}")
        self.event_id = event_id



def price_checkout(
    event: CheckoutCompleted, unit_prices: Mapping[str, int]
) -> PricedCheckout:
    unknown_skus = sorted({item.sku for item in event.items} - unit_prices.keys())
    if unknown_skus:
        raise UnknownSkuError(unknown_skus)

    priced_items: list[PricedCheckoutItem] = []
    total_item_count = 0
    total_amount = 0

    for item in event.items:
        unit_price = int(unit_prices[item.sku])
        subtotal = unit_price * item.quantity
        total_item_count += item.quantity
        total_amount += subtotal
        priced_items.append(
            PricedCheckoutItem(
                sku=item.sku,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal_amount=subtotal,
                confidence=item.confidence,
            )
        )

    if (
        total_item_count > MYSQL_UNSIGNED_INT_MAX
        or total_amount > MYSQL_UNSIGNED_INT_MAX
        or any(item.subtotal_amount > MYSQL_UNSIGNED_INT_MAX for item in priced_items)
    ):
        raise CheckoutAmountOverflowError(
            "checkout totals exceed MySQL INT UNSIGNED"
        )

    completed_at_utc = (
        event.completed_at.astimezone(timezone.utc).replace(tzinfo=None)
    )
    return PricedCheckout(
        event=event,
        items=tuple(priced_items),
        total_item_count=total_item_count,
        total_amount=total_amount,
        completed_at_utc=completed_at_utc,
    )


class CheckoutService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def process(self, event: CheckoutCompleted) -> PricedCheckout:
        connection: Any | None = None
        checkout_repository: CheckoutRepository | None = None
        try:
            connection = self._database.connect()
            connection.start_transaction()
            checkout_repository = CheckoutRepository(connection)
            if checkout_repository.event_exists(event.event_id):
                raise DuplicateEventError(event.event_id)

            product_repository = ProductRepository(connection)
            prices = product_repository.get_unit_prices(
                [item.sku for item in event.items]
            )
            checkout = price_checkout(event, prices)
            checkout_repository.insert(checkout)
            connection.commit()
            return checkout
        except mysql.connector.IntegrityError as exc:
            if connection is not None:
                connection.rollback()
            if (
                exc.errno == 1062
                and checkout_repository is not None
                and checkout_repository.event_exists(event.event_id)
            ):
                raise DuplicateEventError(event.event_id) from exc
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        finally:
            if connection is not None:
                connection.close()

