"""MySQL connection creation."""

from __future__ import annotations

from typing import Any

import mysql.connector

from .config import GatewaySettings


class Database:
    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings

    def connect(self) -> Any:
        return mysql.connector.connect(
            host=self._settings.mysql_host,
            port=self._settings.mysql_port,
            database=self._settings.mysql_database,
            user=self._settings.mysql_user,
            password=self._settings.mysql_password,
            autocommit=False,
            connection_timeout=self._settings.mysql_connection_timeout,
            charset="utf8mb4",
            time_zone="+00:00",
        )

