"""Environment-backed Gateway configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_CHECKOUT_TOPIC = "retail/jetson-01/checkout/completed"
DEFAULT_STATUS_TOPIC = "retail/jetson-01/status"


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigurationError(f"{name} must be set")
    return value


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


@dataclass(frozen=True)
class GatewaySettings:
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id: str
    status_topic: str
    mqtt_keepalive: int
    checkout_topic: str
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    mysql_connection_timeout: int
    log_level: str

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "GatewaySettings":
        load_dotenv(env_file or DEFAULT_ENV_FILE, override=False)
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("LOG_LEVEL is invalid")

        return cls(
            mqtt_host=_required("MQTT_HOST"),
            mqtt_port=_integer("MQTT_PORT", 1883, 1, 65535),
            mqtt_username=_required("MQTT_USERNAME"),
            mqtt_password=_required("MQTT_PASSWORD"),
            mqtt_client_id=_required("MQTT_CLIENT_ID"),
            mqtt_keepalive=_integer("MQTT_KEEPALIVE", 60, 1, 65535),
            checkout_topic=os.getenv(
                "MQTT_CHECKOUT_TOPIC", DEFAULT_CHECKOUT_TOPIC
            ),
            mysql_host=_required("MYSQL_HOST"),
            status_topic=os.getenv("MQTT_STATUS_TOPIC", DEFAULT_STATUS_TOPIC),
            mysql_port=_integer("MYSQL_PORT", 3306, 1, 65535),
            mysql_database=_required("MYSQL_DATABASE"),
            mysql_user=_required("MYSQL_USER"),
            mysql_password=_required("MYSQL_PASSWORD"),
            mysql_connection_timeout=_integer(
                "MYSQL_CONNECTION_TIMEOUT", 5, 1, 300
            ),
            log_level=log_level,
        )

