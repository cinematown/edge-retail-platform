"""MQTT payload validation."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .models import CheckoutCompleted, DeviceStatus

MessageModel = TypeVar("MessageModel", bound=BaseModel)



class MessageValidationError(ValueError):
    """Validation failure without retaining or logging the raw payload."""

    def __init__(self, details: list[dict[str, str]]) -> None:
        super().__init__("message validation failed")
        self.details = details


def _parse_message(payload: bytes, model: type[MessageModel]) -> MessageModel:
    try:
        return model.model_validate_json(payload)
    except ValidationError as exc:
        details: list[dict[str, str]] = []
        for error in exc.errors(include_input=False, include_url=False):
            location = ".".join(str(part) for part in error["loc"]) or "$"
            details.append(
                {
                    "field": location,
                    "type": str(error["type"]),
                }
            )
        raise MessageValidationError(details) from exc


def parse_checkout_message(payload: bytes) -> CheckoutCompleted:
    return _parse_message(payload, CheckoutCompleted)


def parse_status_message(payload: bytes) -> DeviceStatus:
    return _parse_message(payload, DeviceStatus)

