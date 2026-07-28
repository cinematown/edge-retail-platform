package com.cinematown.edgeretail.gateway;

import io.micronaut.data.exceptions.DataAccessException;
import jakarta.inject.Singleton;
import jakarta.transaction.Transactional;

import java.sql.SQLException;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Singleton
public class CheckoutService {
    private static final long MYSQL_UNSIGNED_INT_MAX = 4_294_967_295L;

    private final GatewayRepository repository;

    CheckoutService(GatewayRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public Messages.PricedCheckout process(Messages.CheckoutCompleted event) {
        if (repository.eventExists(event.eventId())) {
            throw new DuplicateEventException(event.eventId());
        }

        var prices = repository.findUnitPrices(
                event.items().stream().map(Messages.CheckoutItem::sku).toList()
        );
        var checkout = price(event, prices);

        try {
            repository.insertCheckout(checkout);
        } catch (DataAccessException exception) {
            if (isDuplicateKey(exception)) {
                throw new DuplicateEventException(event.eventId(), exception);
            }
            throw exception;
        }
        return checkout;
    }

    static Messages.PricedCheckout price(
            Messages.CheckoutCompleted event,
            Map<String, Long> prices
    ) {
        var unknownSkus = event.items().stream()
                .map(Messages.CheckoutItem::sku)
                .filter(sku -> !prices.containsKey(sku))
                .distinct()
                .sorted()
                .toList();
        if (!unknownSkus.isEmpty()) {
            throw new UnknownSkuException(unknownSkus);
        }

        List<Messages.PricedItem> pricedItems = new ArrayList<>();
        long totalItems = 0;
        long totalAmount = 0;
        try {
            for (var item : event.items()) {
                long unitPrice = prices.get(item.sku());
                long subtotal = Math.multiplyExact(unitPrice, item.quantity());
                totalItems = Math.addExact(totalItems, item.quantity());
                totalAmount = Math.addExact(totalAmount, subtotal);
                if (subtotal > MYSQL_UNSIGNED_INT_MAX) {
                    throw new ArithmeticException("subtotal exceeds MySQL INT UNSIGNED");
                }
                pricedItems.add(new Messages.PricedItem(
                        item.sku(), item.quantity(), unitPrice, subtotal, item.confidence()
                ));
            }
            if (totalItems > MYSQL_UNSIGNED_INT_MAX || totalAmount > MYSQL_UNSIGNED_INT_MAX) {
                throw new ArithmeticException("checkout total exceeds MySQL INT UNSIGNED");
            }
        } catch (ArithmeticException exception) {
            throw new CheckoutAmountOverflowException(exception.getMessage(), exception);
        }

        return new Messages.PricedCheckout(
                event,
                List.copyOf(pricedItems),
                totalItems,
                totalAmount,
                event.completedAt().withOffsetSameInstant(ZoneOffset.UTC).toLocalDateTime()
        );
    }

    private static boolean isDuplicateKey(Throwable throwable) {
        for (Throwable current = throwable; current != null; current = current.getCause()) {
            if (current instanceof SQLException sqlException
                    && (sqlException.getErrorCode() == 1062 || "23000".equals(sqlException.getSQLState()))) {
                return true;
            }
        }
        return false;
    }

    static class CheckoutProcessingException extends RuntimeException {
        CheckoutProcessingException(String message) {
            super(message);
        }

        CheckoutProcessingException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    static final class DuplicateEventException extends CheckoutProcessingException {
        DuplicateEventException(String eventId) {
            super("event already processed: " + eventId);
        }

        DuplicateEventException(String eventId, Throwable cause) {
            super("event already processed: " + eventId, cause);
        }
    }

    static final class UnknownSkuException extends CheckoutProcessingException {
        private final List<String> skus;

        UnknownSkuException(List<String> skus) {
            super("unknown SKU: " + String.join(", ", skus));
            this.skus = List.copyOf(skus);
        }

        List<String> skus() {
            return skus;
        }
    }

    static final class CheckoutAmountOverflowException extends CheckoutProcessingException {
        CheckoutAmountOverflowException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
