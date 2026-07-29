package com.cinematown.edgeretail.gateway;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

final class CheckoutPricingTest {
    @Test
    void pricingContractMatchesExistingGateway() {
        var event = event(List.of(
                new Messages.CheckoutItem("cola_can", 2, new BigDecimal("0.9300")),
                new Messages.CheckoutItem("snack_red", 1, new BigDecimal("0.8900"))
        ));

        var priced = CheckoutService.price(event, Map.of("cola_can", 1500L, "snack_red", 2000L));

        assertEquals(3, priced.totalItemCount());
        assertEquals(5000, priced.totalAmount());
    }

    @Test
    void unknownSkuIsRejected() {
        var event = event(List.of(
                new Messages.CheckoutItem("unknown_product", 1, new BigDecimal("0.9000"))
        ));

        assertThrows(
                CheckoutService.UnknownSkuException.class,
                () -> CheckoutService.price(event, Map.of())
        );
    }

    private static Messages.CheckoutCompleted event(List<Messages.CheckoutItem> items) {
        return new Messages.CheckoutCompleted(
                1,
                "evt-test",
                "checkout-test",
                "jetson-01",
                "run-test",
                12,
                7,
                items,
                OffsetDateTime.parse("2026-07-26T14:20:42.456+09:00")
        );
    }
}
