package com.cinematown.edgeretail.gateway;

import io.micronaut.data.exceptions.DataAccessException;
import io.micronaut.mqtt.annotation.MqttSubscriber;
import io.micronaut.mqtt.annotation.Topic;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@MqttSubscriber
public class GatewaySubscriber {
    private static final Logger LOG = LoggerFactory.getLogger(GatewaySubscriber.class);

    private final MessageDecoder decoder;
    private final CheckoutService checkoutService;
    private final DeviceStatusService statusService;

    GatewaySubscriber(
            MessageDecoder decoder,
            CheckoutService checkoutService,
            DeviceStatusService statusService
    ) {
        this.decoder = decoder;
        this.checkoutService = checkoutService;
        this.statusService = statusService;
    }

    @Topic(value = Topics.CHECKOUT_COMPLETED, qos = 1)
    public void receiveCheckout(byte[] payload) {
        LOG.atInfo()
                .addKeyValue("event", "MESSAGE_RECEIVED")
                .addKeyValue("topic", Topics.CHECKOUT_COMPLETED)
                .addKeyValue("payload_bytes", payload.length)
                .log("MQTT message received");

        Messages.CheckoutCompleted event;
        try {
            event = decoder.decode(payload, Messages.CheckoutCompleted.class);
        } catch (MessageDecoder.MessageValidationException exception) {
            LOG.atWarn()
                    .addKeyValue("event", "MESSAGE_VALIDATION_FAILED")
                    .addKeyValue("topic", Topics.CHECKOUT_COMPLETED)
                    .addKeyValue("errors", exception.errors())
                    .log("Checkout message rejected");
            return;
        }

        try {
            var checkout = checkoutService.process(event);
            LOG.atInfo()
                    .addKeyValue("event", "CHECKOUT_PROCESSED")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("checkout_id", event.checkoutId())
                    .addKeyValue("device_id", event.deviceId())
                    .addKeyValue("tracking_session_id", event.trackingSessionId())
                    .addKeyValue("cart_track_id", event.cartTrackId())
                    .addKeyValue("payer_track_id", event.payerTrackId())
                    .addKeyValue("total_item_count", checkout.totalItemCount())
                    .addKeyValue("total_amount", checkout.totalAmount())
                    .log("Checkout persisted");
        } catch (CheckoutService.DuplicateEventException exception) {
            LOG.atWarn()
                    .addKeyValue("event", "CHECKOUT_DUPLICATE_SKIPPED")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("checkout_id", event.checkoutId())
                    .log("Duplicate checkout skipped");
        } catch (CheckoutService.UnknownSkuException exception) {
            LOG.atWarn()
                    .addKeyValue("event", "UNKNOWN_SKU")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("unknown_skus", exception.skus())
                    .log("Checkout contains unknown or inactive SKU");
        } catch (CheckoutService.CheckoutProcessingException exception) {
            LOG.atWarn()
                    .addKeyValue("event", "MESSAGE_VALIDATION_FAILED")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("error_type", exception.getClass().getSimpleName())
                    .log("Checkout business validation failed");
        } catch (DataAccessException exception) {
            LOG.atError()
                    .addKeyValue("event", "DATABASE_ERROR")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("error_type", exception.getClass().getSimpleName())
                    .log("Checkout persistence failed");
        } catch (RuntimeException exception) {
            LOG.atError()
                    .addKeyValue("event", "MESSAGE_HANDLER_ERROR")
                    .addKeyValue("event_id", event.eventId())
                    .addKeyValue("error_type", exception.getClass().getSimpleName())
                    .log("Unexpected checkout handler failure");
        }
    }

    @Topic(value = Topics.DEVICE_STATUS, qos = 1)
    public void receiveStatus(byte[] payload) {
        LOG.atInfo()
                .addKeyValue("event", "MESSAGE_RECEIVED")
                .addKeyValue("topic", Topics.DEVICE_STATUS)
                .addKeyValue("payload_bytes", payload.length)
                .log("MQTT message received");

        Messages.DeviceStatus status;
        try {
            status = decoder.decode(payload, Messages.DeviceStatus.class);
        } catch (MessageDecoder.MessageValidationException exception) {
            LOG.atWarn()
                    .addKeyValue("event", "MESSAGE_VALIDATION_FAILED")
                    .addKeyValue("topic", Topics.DEVICE_STATUS)
                    .addKeyValue("errors", exception.errors())
                    .log("Device status message rejected");
            return;
        }

        try {
            statusService.process(status);
            LOG.atInfo()
                    .addKeyValue("event", "DEVICE_STATUS_UPDATED")
                    .addKeyValue("device_id", status.deviceId())
                    .addKeyValue("tracking_session_id", status.trackingSessionId())
                    .addKeyValue("status", status.status())
                    .log("Device status persisted");
        } catch (DataAccessException exception) {
            LOG.atError()
                    .addKeyValue("event", "DATABASE_ERROR")
                    .addKeyValue("device_id", status.deviceId())
                    .addKeyValue("error_type", exception.getClass().getSimpleName())
                    .log("Device status persistence failed");
        } catch (RuntimeException exception) {
            LOG.atError()
                    .addKeyValue("event", "MESSAGE_HANDLER_ERROR")
                    .addKeyValue("device_id", status.deviceId())
                    .addKeyValue("error_type", exception.getClass().getSimpleName())
                    .log("Unexpected device status handler failure");
        }
    }
}
