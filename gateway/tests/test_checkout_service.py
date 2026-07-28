from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import mysql.connector

from edge_gateway.checkout_service import (
    CheckoutService,
    DuplicateEventError,
    UnknownSkuError,
    price_checkout,
)
from edge_gateway.models import CheckoutCompleted


def multiple_item_event() -> CheckoutCompleted:
    return CheckoutCompleted.model_validate(
        {
            "schemaVersion": 1,
            "eventId": "evt-checkout-unit-multiple-001",
            "checkoutId": "checkout-unit-multiple-001",
            "deviceId": "jetson-01",
            "trackingSessionId": "unit-run-multiple-001",
            "cartTrackId": 22,
            "payerTrackId": 17,
            "items": [
                {
                    "sku": "cola_can",
                    "quantity": 2,
                    "confidence": 0.93,
                },
                {
                    "sku": "snack_red",
                    "quantity": 1,
                    "confidence": 0.89,
                },
            ],
            "completedAt": "2026-07-26T14:20:42.456+09:00",
        }
    )


class CheckoutPricingTests(unittest.TestCase):
    def test_prices_items_and_normalizes_time_to_utc(self) -> None:
        checkout = price_checkout(
            multiple_item_event(),
            {"cola_can": 1500, "snack_red": 2000},
        )

        self.assertEqual(checkout.total_item_count, 3)
        self.assertEqual(checkout.total_amount, 5000)
        self.assertEqual(checkout.items[0].subtotal_amount, 3000)
        self.assertEqual(
            checkout.completed_at_utc,
            datetime(2026, 7, 26, 5, 20, 42, 456000),
        )

    def test_unknown_sku_is_rejected(self) -> None:
        with self.assertRaises(UnknownSkuError) as raised:
            price_checkout(multiple_item_event(), {"cola_can": 1500})

        self.assertEqual(raised.exception.skus, ["snack_red"])


class CheckoutTransactionTests(unittest.TestCase):
    @patch("edge_gateway.checkout_service.CheckoutRepository")
    @patch("edge_gateway.checkout_service.ProductRepository")
    def test_commits_checkout_and_items_together(
        self,
        product_repository_class: MagicMock,
        checkout_repository_class: MagicMock,
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        product_repository_class.return_value.get_unit_prices.return_value = {
            "cola_can": 1500,
            "snack_red": 2000,
        }
        checkout_repository_class.return_value.event_exists.return_value = False

        result = CheckoutService(database).process(multiple_item_event())

        connection.start_transaction.assert_called_once_with()
        checkout_repository_class.return_value.insert.assert_called_once_with(result)
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once_with()

    @patch("edge_gateway.checkout_service.CheckoutRepository")
    @patch("edge_gateway.checkout_service.ProductRepository")
    def test_rolls_back_when_a_product_is_missing(
        self,
        product_repository_class: MagicMock,
        checkout_repository_class: MagicMock,
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        product_repository_class.return_value.get_unit_prices.return_value = {
            "cola_can": 1500
        }
        checkout_repository_class.return_value.event_exists.return_value = False

        with self.assertRaises(UnknownSkuError):
            CheckoutService(database).process(multiple_item_event())

        connection.commit.assert_not_called()
        connection.rollback.assert_called_once_with()
        checkout_repository_class.return_value.insert.assert_not_called()
        connection.close.assert_called_once_with()

    @patch("edge_gateway.checkout_service.CheckoutRepository")
    @patch("edge_gateway.checkout_service.ProductRepository")
    def test_skips_known_event_before_product_lookup(
        self,
        product_repository_class: MagicMock,
        checkout_repository_class: MagicMock,
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        checkout_repository_class.return_value.event_exists.return_value = True

        with self.assertRaises(DuplicateEventError):
            CheckoutService(database).process(multiple_item_event())

        product_repository_class.return_value.get_unit_prices.assert_not_called()
        checkout_repository_class.return_value.insert.assert_not_called()
        connection.commit.assert_not_called()
        connection.rollback.assert_called_once_with()
        connection.close.assert_called_once_with()

    @patch("edge_gateway.checkout_service.CheckoutRepository")
    @patch("edge_gateway.checkout_service.ProductRepository")
    def test_unique_constraint_race_is_treated_as_duplicate(
        self,
        product_repository_class: MagicMock,
        checkout_repository_class: MagicMock,
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        repository = checkout_repository_class.return_value
        repository.event_exists.side_effect = [False, True]
        repository.insert.side_effect = mysql.connector.IntegrityError(
            msg="duplicate event_id",
            errno=1062,
        )
        product_repository_class.return_value.get_unit_prices.return_value = {
            "cola_can": 1500,
            "snack_red": 2000,
        }

        with self.assertRaises(DuplicateEventError):
            CheckoutService(database).process(multiple_item_event())

        connection.commit.assert_not_called()
        connection.rollback.assert_called_once_with()
        connection.close.assert_called_once_with()



if __name__ == "__main__":
    unittest.main()

