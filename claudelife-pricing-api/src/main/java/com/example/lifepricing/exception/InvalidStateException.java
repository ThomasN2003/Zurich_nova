package com.example.lifepricing.exception;

/** The record exists but is in the wrong state for what you asked. Handled as 409. */
public class InvalidStateException extends RuntimeException {
    public InvalidStateException(String message) {
        super(message);
    }
}
