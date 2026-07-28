"""MQTT contract and internal checkout records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


Sku = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=50),
]
Identifier100 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=100),
]
DeviceIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1, max_length=50),
]
TrackIdentifier = Annotated[int, Field(strict=True, ge=0)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=4_294_967_295)]
Confidence = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("1"), max_digits=5, decimal_places=4),
]


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    quantity: Quantity
    confidence: Confidence

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_must_be_numeric(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("confidence must be a JSON number")
        return value


class CheckoutCompleted(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schemaVersion")
    event_id: Identifier100 = Field(alias="eventId")
    checkout_id: Identifier100 = Field(alias="checkoutId")
    device_id: DeviceIdentifier = Field(alias="deviceId")
    tracking_session_id: Identifier100 = Field(alias="trackingSessionId")
    cart_track_id: TrackIdentifier = Field(alias="cartTrackId")
    payer_track_id: TrackIdentifier = Field(alias="payerTrackId")
    items: Annotated[list[CheckoutItem], Field(min_length=1)]
    completed_at: datetime = Field(alias="completedAt")

    @field_validator("completed_at")
    @classmethod
    def completed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("completedAt must include a UTC offset")
        return value


class DeviceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schemaVersion")
    device_id: DeviceIdentifier = Field(alias="deviceId")
    status: Literal["ONLINE", "OFFLINE", "ERROR"]
    model_version: Identifier100 | None = Field(
        default=None, alias="modelVersion"
    )
    tracking_session_id: Identifier100 | None = Field(
        default=None, alias="trackingSessionId"
    )
    observed_at: datetime = Field(alias="observedAt")

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observedAt must include a UTC offset")
        return value



@dataclass(frozen=True)
class PricedCheckoutItem:
    sku: str
    quantity: int
    unit_price: int
    subtotal_amount: int
    confidence: Decimal


@dataclass(frozen=True)
class PricedCheckout:
    event: CheckoutCompleted
    items: tuple[PricedCheckoutItem, ...]
    total_item_count: int
    total_amount: int
    completed_at_utc: datetime

