"""MQTT Subscriber embedded in the Gateway process."""

from __future__ import annotations

from typing import Any, Protocol

import mysql.connector
import paho.mqtt.client as mqtt

from .checkout_service import (
    CheckoutProcessingError,
    CheckoutService,
    DuplicateEventError,
    UnknownSkuError,
)
from .config import GatewaySettings
from .models import CheckoutCompleted
from .status_service import DeviceStatusService
from .validator import (
    MessageValidationError,
    parse_checkout_message,
    parse_status_message,
)


class LogSink(Protocol):
    def __call__(self, event: str, **fields: Any) -> None: ...


def _event_context(event: CheckoutCompleted) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "checkout_id": event.checkout_id,
        "device_id": event.device_id,
        "tracking_session_id": event.tracking_session_id,
        "cart_track_id": event.cart_track_id,
        "payer_track_id": event.payer_track_id,
    }


class MqttSubscriber:
    def __init__(
        self,
        settings: GatewaySettings,
        checkout_service: CheckoutService,
        status_service: DeviceStatusService,
        log: LogSink,
    ) -> None:
        self._settings = settings
        self._checkout_service = checkout_service
        self._status_service = status_service
        self._log = log
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
            protocol=mqtt.MQTTv311,
        )
        self._client.username_pw_set(
            settings.mqtt_username, settings.mqtt_password
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    def run_forever(self) -> None:
        self._client.connect_async(
            self._settings.mqtt_host,
            self._settings.mqtt_port,
            keepalive=self._settings.mqtt_keepalive,
        )
        self._client.loop_forever(retry_first_connection=True)

    def stop(self) -> None:
        self._client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code != 0:
            self._log(
                "MQTT_CONNECTION_FAILED",
                reason_code=str(reason_code),
            )
            return

        topics = [
            (self._settings.checkout_topic, 1),
            (self._settings.status_topic, 1),
        ]
        result, _message_id = client.subscribe(topics)
        if result != mqtt.MQTT_ERR_SUCCESS:
            self._log(
                "MQTT_SUBSCRIBE_FAILED",
                topics=[topic for topic, _qos in topics],
                error=mqtt.error_string(result),
            )
            return

        self._log(
            "MQTT_CONNECTED",
            host=self._settings.mqtt_host,
            port=self._settings.mqtt_port,
            client_id=self._settings.mqtt_client_id,
            topics=[topic for topic, _qos in topics],
        )

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        self._log("MQTT_DISCONNECTED", reason_code=str(reason_code))

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        try:
            if message.topic == self._settings.checkout_topic:
                self._handle_checkout_message(message)
            elif message.topic == self._settings.status_topic:
                self._handle_status_message(message)
        except Exception as exc:
            self._log(
                "MESSAGE_HANDLER_ERROR",
                topic=message.topic,
                error_type=type(exc).__name__,
            )

    @staticmethod
    def _message_fields(message: mqtt.MQTTMessage) -> dict[str, Any]:
        return {
            "topic": message.topic,
            "qos": message.qos,
            "retained": bool(message.retain),
            "payload_bytes": len(message.payload),
        }

    def _handle_checkout_message(self, message: mqtt.MQTTMessage) -> None:
        message_fields = self._message_fields(message)
        try:
            event = parse_checkout_message(message.payload)
        except MessageValidationError as exc:
            self._log("MESSAGE_RECEIVED", **message_fields)
            self._log(
                "MESSAGE_VALIDATION_FAILED",
                topic=message.topic,
                errors=exc.details,
            )
            return

        context = _event_context(event)
        self._log("MESSAGE_RECEIVED", **message_fields, **context)
        try:
            checkout = self._checkout_service.process(event)
        except DuplicateEventError:
            self._log("CHECKOUT_DUPLICATE_SKIPPED", **context)
            return
        except UnknownSkuError as exc:
            self._log("UNKNOWN_SKU", **context, unknown_skus=exc.skus)
            return
        except CheckoutProcessingError as exc:
            self._log(
                "MESSAGE_VALIDATION_FAILED",
                **context,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            return
        except mysql.connector.Error as exc:
            self._log(
                "DATABASE_ERROR",
                **context,
                error_type=type(exc).__name__,
                mysql_errno=exc.errno,
                sqlstate=exc.sqlstate,
            )
            return

        self._log(
            "CHECKOUT_PROCESSED",
            **context,
            total_item_count=checkout.total_item_count,
            total_amount=checkout.total_amount,
        )

    def _handle_status_message(self, message: mqtt.MQTTMessage) -> None:
        message_fields = self._message_fields(message)
        try:
            status = parse_status_message(message.payload)
        except MessageValidationError as exc:
            self._log("MESSAGE_RECEIVED", **message_fields)
            self._log(
                "MESSAGE_VALIDATION_FAILED",
                topic=message.topic,
                errors=exc.details,
            )
            return

        context = {
            "device_id": status.device_id,
            "tracking_session_id": status.tracking_session_id,
            "status": status.status,
        }
        self._log("MESSAGE_RECEIVED", **message_fields, **context)
        try:
            self._status_service.process(status)
        except mysql.connector.Error as exc:
            self._log(
                "DATABASE_ERROR",
                **context,
                error_type=type(exc).__name__,
                mysql_errno=exc.errno,
                sqlstate=exc.sqlstate,
            )
            return

        self._log("DEVICE_STATUS_UPDATED", **context)

