package com.cinematown.edgeretail.gateway;

import io.micronaut.serde.annotation.Serdeable;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.List;

final class Messages {
    private Messages() {
    }

    @Serdeable
    record CheckoutItem(
            @NotBlank @Size(max = 50) String sku,
            @Min(1) @Max(4_294_967_295L) long quantity,
            @NotNull @DecimalMin("0.0") @DecimalMax("1.0")
            @Digits(integer = 1, fraction = 4) BigDecimal confidence
    ) {
    }

    @Serdeable
    record CheckoutCompleted(
            @Min(1) @Max(1) int schemaVersion,
            @NotBlank @Size(max = 100) String eventId,
            @NotBlank @Size(max = 100) String checkoutId,
            @NotBlank @Size(max = 50) String deviceId,
            @NotBlank @Size(max = 100) String trackingSessionId,
            @PositiveOrZero long cartTrackId,
            @PositiveOrZero long payerTrackId,
            @NotEmpty List<@Valid CheckoutItem> items,
            @NotNull OffsetDateTime completedAt
    ) {
    }

    enum DeviceState {
        ONLINE,
        OFFLINE,
        ERROR
    }

    @Serdeable
    record DeviceStatus(
            @Min(1) @Max(1) int schemaVersion,
            @NotBlank @Size(max = 50) String deviceId,
            @NotNull DeviceState status,
            @Size(max = 100) String modelVersion,
            @Size(max = 100) String trackingSessionId,
            @NotNull OffsetDateTime observedAt
    ) {
    }

    record PricedItem(
            String sku,
            long quantity,
            long unitPrice,
            long subtotalAmount,
            BigDecimal confidence
    ) {
    }

    record PricedCheckout(
            CheckoutCompleted event,
            List<PricedItem> items,
            long totalItemCount,
            long totalAmount,
            LocalDateTime completedAtUtc
    ) {
    }
}
