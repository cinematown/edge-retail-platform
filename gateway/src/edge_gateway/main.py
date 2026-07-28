"""Gateway process entry point."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from .checkout_service import CheckoutService
from .config import ConfigurationError, GatewaySettings
from .database import Database
from .mqtt_client import MqttSubscriber
from .status_service import DeviceStatusService


LOGGER = logging.getLogger("edge_gateway")
WARNING_EVENTS = {
    "MESSAGE_VALIDATION_FAILED",
    "MQTT_DISCONNECTED",
    "MQTT_SUBSCRIBE_FAILED",
    "UNKNOWN_SKU",
    "CHECKOUT_DUPLICATE_SKIPPED",
}
ERROR_EVENTS = {
    "DATABASE_ERROR",
    "MESSAGE_HANDLER_ERROR",
    "MQTT_CONNECTION_FAILED",
}


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )


def emit_log(event: str, **fields: Any) -> None:
    record = {"event": event, **fields}
    message = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    if event in ERROR_EVENTS:
        LOGGER.error(message)
    elif event in WARNING_EVENTS:
        LOGGER.warning(message)
    else:
        LOGGER.info(message)


def main() -> int:
    configure_logging("INFO")
    try:
        settings = GatewaySettings.from_env()
        configure_logging(settings.log_level)
        database = Database(settings)
        subscriber = MqttSubscriber(
            settings,
            CheckoutService(database),
            DeviceStatusService(database),
            emit_log,
        )
        subscriber.run_forever()
    except KeyboardInterrupt:
        emit_log("GATEWAY_STOPPED", reason="keyboard_interrupt")
        return 0
    except ConfigurationError as exc:
        emit_log(
            "CONFIGURATION_ERROR",
            error_type=type(exc).__name__,
            message=str(exc),
        )
        return 1
    except (ConnectionError, OSError) as exc:
        emit_log(
            "MQTT_CONNECTION_FAILED",
            error_type=type(exc).__name__,
            message=str(exc),
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

