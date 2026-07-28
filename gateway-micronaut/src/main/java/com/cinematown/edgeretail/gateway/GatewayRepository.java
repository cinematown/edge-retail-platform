package com.cinematown.edgeretail.gateway;

import io.micronaut.data.jdbc.runtime.JdbcOperations;
import jakarta.inject.Singleton;

import java.sql.Timestamp;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

@Singleton
public final class GatewayRepository {
    private static final String INSERT_CHECKOUT = """
            INSERT INTO checkouts (
                checkout_id, event_id, device_id, tracking_session_id,
                cart_track_id, payer_track_id, total_item_count,
                total_amount, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;
    private static final String INSERT_ITEM = """
            INSERT INTO checkout_items (
                checkout_id, sku, quantity, unit_price,
                subtotal_amount, confidence
            ) VALUES (?, ?, ?, ?, ?, ?)
            """;
    private static final String UPSERT_STATUS = """
            INSERT INTO device_status (
                device_id, status, model_version, tracking_session_id, last_seen_at
            ) VALUES (?, ?, ?, ?, ?) AS incoming
            ON DUPLICATE KEY UPDATE
                status = incoming.status,
                model_version = incoming.model_version,
                tracking_session_id = incoming.tracking_session_id,
                last_seen_at = incoming.last_seen_at
            """;

    private final JdbcOperations jdbc;

    GatewayRepository(JdbcOperations jdbc) {
        this.jdbc = jdbc;
    }

    boolean eventExists(String eventId) {
        return jdbc.prepareStatement(
                "SELECT 1 FROM checkouts WHERE event_id = ? LIMIT 1",
                statement -> {
                    statement.setString(1, eventId);
                    try (var result = statement.executeQuery()) {
                        return result.next();
                    }
                }
        );
    }

    Map<String, Long> findUnitPrices(Collection<String> skus) {
        var uniqueSkus = skus.stream().distinct().sorted().toList();
        if (uniqueSkus.isEmpty()) {
            return Map.of();
        }
        String placeholders = String.join(",", java.util.Collections.nCopies(uniqueSkus.size(), "?"));
        String sql = "SELECT sku, unit_price FROM products WHERE is_active = TRUE AND sku IN (" + placeholders + ")";
        return jdbc.prepareStatement(sql, statement -> {
            for (int index = 0; index < uniqueSkus.size(); index++) {
                statement.setString(index + 1, uniqueSkus.get(index));
            }
            Map<String, Long> prices = new HashMap<>();
            try (var result = statement.executeQuery()) {
                while (result.next()) {
                    prices.put(result.getString("sku"), result.getLong("unit_price"));
                }
            }
            return Map.copyOf(prices);
        });
    }

    void insertCheckout(Messages.PricedCheckout checkout) {
        var event = checkout.event();
        jdbc.prepareStatement(INSERT_CHECKOUT, statement -> {
            statement.setString(1, event.checkoutId());
            statement.setString(2, event.eventId());
            statement.setString(3, event.deviceId());
            statement.setString(4, event.trackingSessionId());
            statement.setLong(5, event.cartTrackId());
            statement.setLong(6, event.payerTrackId());
            statement.setLong(7, checkout.totalItemCount());
            statement.setLong(8, checkout.totalAmount());
            statement.setTimestamp(9, Timestamp.valueOf(checkout.completedAtUtc()));
            statement.executeUpdate();
            return null;
        });

        jdbc.prepareStatement(INSERT_ITEM, statement -> {
            for (var item : checkout.items()) {
                statement.setString(1, event.checkoutId());
                statement.setString(2, item.sku());
                statement.setLong(3, item.quantity());
                statement.setLong(4, item.unitPrice());
                statement.setLong(5, item.subtotalAmount());
                statement.setBigDecimal(6, item.confidence());
                statement.addBatch();
            }
            statement.executeBatch();
            return null;
        });
    }

    void upsertStatus(Messages.DeviceStatus status) {
        jdbc.prepareStatement(UPSERT_STATUS, statement -> {
            statement.setString(1, status.deviceId());
            statement.setString(2, status.status().name());
            statement.setString(3, status.modelVersion());
            statement.setString(4, status.trackingSessionId());
            statement.setTimestamp(
                    5,
                    Timestamp.valueOf(status.observedAt().withOffsetSameInstant(java.time.ZoneOffset.UTC).toLocalDateTime())
            );
            statement.executeUpdate();
            return null;
        });
    }
}
