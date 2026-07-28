"""Device status upsert transaction."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from .database import Database
from .models import DeviceStatus
from .repositories import DeviceStatusRepository


class DeviceStatusService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def process(self, status: DeviceStatus) -> None:
        connection: Any | None = None
        try:
            connection = self._database.connect()
            connection.start_transaction()
            observed_at_utc = (
                status.observed_at.astimezone(timezone.utc).replace(tzinfo=None)
            )
            DeviceStatusRepository(connection).upsert(status, observed_at_utc)
            connection.commit()
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
