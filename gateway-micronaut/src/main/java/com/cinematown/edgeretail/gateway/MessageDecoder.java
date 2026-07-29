package com.cinematown.edgeretail.gateway;

import io.micronaut.json.JsonMapper;
import jakarta.inject.Singleton;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;

import java.io.IOException;
import java.util.List;

@Singleton
public final class MessageDecoder {
    private final JsonMapper jsonMapper;
    private final Validator validator;

    MessageDecoder(JsonMapper jsonMapper, Validator validator) {
        this.jsonMapper = jsonMapper;
        this.validator = validator;
    }

    <T> T decode(byte[] payload, Class<T> type) {
        try {
            T message = jsonMapper.readValue(payload, type);
            List<String> errors = validator.validate(message).stream()
                    .map(MessageDecoder::formatViolation)
                    .sorted()
                    .toList();
            if (!errors.isEmpty()) {
                throw new MessageValidationException(errors);
            }
            return message;
        } catch (IOException | IllegalArgumentException exception) {
            throw new MessageValidationException(List.of("$: invalid JSON or field type"), exception);
        }
    }

    private static String formatViolation(ConstraintViolation<?> violation) {
        String path = violation.getPropertyPath().toString();
        return (path.isBlank() ? "$" : path) + ": " + violation.getMessage();
    }

    static final class MessageValidationException extends RuntimeException {
        private final List<String> errors;

        MessageValidationException(List<String> errors) {
            super("message validation failed");
            this.errors = List.copyOf(errors);
        }

        MessageValidationException(List<String> errors, Throwable cause) {
            super("message validation failed", cause);
            this.errors = List.copyOf(errors);
        }

        List<String> errors() {
            return errors;
        }
    }
}
