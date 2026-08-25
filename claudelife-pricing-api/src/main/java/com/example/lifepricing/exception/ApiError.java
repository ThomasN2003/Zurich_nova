package com.example.lifepricing.exception;

import java.time.Instant;
import java.util.Map;

public record ApiError(
        Instant timestamp,
        int status,
        String code,
        String message,
        Map<String, String> fields
) {
    public static ApiError of(int status, String code, String message) {
        return new ApiError(Instant.now(), status, code, message, null);
    }

    public static ApiError of(int status, String code, String message, Map<String, String> fields) {
        return new ApiError(Instant.now(), status, code, message, fields);
    }
}
