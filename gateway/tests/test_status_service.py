from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from edge_gateway.models import DeviceStatus
from edge_gateway.status_service import DeviceStatusService


def online_status() -> DeviceStatus:
    return DeviceStatus.model_validate(
        {
            "schemaVersion": 1,
            "deviceId": "jetson-01",
            "status": "ONLINE",
            "modelVersion": "mock-yolo-v1",
            "trackingSessionId": "mock-run-status-001",
            "observedAt": "2026-07-26T14:20:40.000+09:00",
        }
    )


class DeviceStatusServiceTests(unittest.TestCase):
    @patch("edge_gateway.status_service.DeviceStatusRepository")
    def test_upserts_utc_time_and_commits(
        self, repository_class: MagicMock
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        status = online_status()

        DeviceStatusService(database).process(status)

        connection.start_transaction.assert_called_once_with()
        repository_class.return_value.upsert.assert_called_once_with(
            status,
            datetime(2026, 7, 26, 5, 20, 40),
        )
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once_with()

    @patch("edge_gateway.status_service.DeviceStatusRepository")
    def test_rolls_back_repository_failure(
        self, repository_class: MagicMock
    ) -> None:
        connection = MagicMock()
        database = MagicMock()
        database.connect.return_value = connection
        repository_class.return_value.upsert.side_effect = RuntimeError(
            "write failed"
        )

        with self.assertRaises(RuntimeError):
            DeviceStatusService(database).process(online_status())

        connection.commit.assert_not_called()
        connection.rollback.assert_called_once_with()
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
