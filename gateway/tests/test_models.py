from __future__ import annotations

import json
import unittest
from datetime import datetime
from decimal import Decimal

from pydantic import ValidationError

from edge_gateway.models import CheckoutCompleted, DeviceStatus
from edge_gateway.validator import (
    MessageValidationError,
    parse_checkout_message,
    parse_status_message,
)


def valid_payload() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "eventId": "evt-checkout-unit-001",
        "checkoutId": "checkout-unit-001",
        "deviceId": "jetson-01",
        "trackingSessionId": "unit-run-001",
        "cartTrackId": 12,
        "payerTrackId": 7,
        "items": [
            {
                "sku": "cola_can",
                "quantity": 2,
                "confidence": 0.93,
            }
        ],
        "completedAt": "2026-07-26T14:20:42.456+09:00",
    }


class CheckoutModelTests(unittest.TestCase):
    def test_valid_payload_uses_contract_aliases(self) -> None:
        event = CheckoutCompleted.model_validate(valid_payload())

        self.assertEqual(event.schema_version, 1)
        self.assertEqual(event.cart_track_id, 12)
        self.assertEqual(event.items[0].confidence, Decimal("0.93"))
        self.assertIsInstance(event.completed_at, datetime)
        self.assertIsNotNone(event.completed_at.utcoffset())

    def test_empty_items_are_rejected(self) -> None:
        payload = valid_payload()
        payload["items"] = []

        with self.assertRaises(ValidationError):
            CheckoutCompleted.model_validate(payload)

    def test_wrong_schema_version_is_rejected(self) -> None:
        payload = valid_payload()
        payload["schemaVersion"] = 2

        with self.assertRaises(ValidationError):
            CheckoutCompleted.model_validate(payload)

    def test_naive_completed_at_is_rejected(self) -> None:
        payload = valid_payload()
        payload["completedAt"] = "2026-07-26T14:20:42.456"

        with self.assertRaises(ValidationError):
            CheckoutCompleted.model_validate(payload)

    def test_invalid_json_exposes_only_field_and_error_type(self) -> None:
        payload = valid_payload()
        payload["items"] = []

        with self.assertRaises(MessageValidationError) as raised:
            parse_checkout_message(json.dumps(payload).encode())

        self.assertEqual(raised.exception.details[0]["field"], "items")
        self.assertIn("type", raised.exception.details[0])
        self.assertNotIn("input", raised.exception.details[0])

class DeviceStatusModelTests(unittest.TestCase):
    def test_valid_status_payload(self) -> None:
        status = parse_status_message(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "deviceId": "jetson-01",
                    "status": "ONLINE",
                    "modelVersion": "mock-yolo-v1",
                    "trackingSessionId": "mock-run-001",
                    "observedAt": "2026-07-26T14:20:40.000+09:00",
                }
            ).encode()
        )

        self.assertIsInstance(status, DeviceStatus)
        self.assertEqual(status.status, "ONLINE")
        self.assertIsNotNone(status.observed_at.utcoffset())

    def test_invalid_status_value_is_rejected(self) -> None:
        payload = {
            "schemaVersion": 1,
            "deviceId": "jetson-01",
            "status": "UNKNOWN",
            "observedAt": "2026-07-26T14:20:40.000+09:00",
        }

        with self.assertRaises(MessageValidationError):
            parse_status_message(json.dumps(payload).encode())




if __name__ == "__main__":
    unittest.main()

