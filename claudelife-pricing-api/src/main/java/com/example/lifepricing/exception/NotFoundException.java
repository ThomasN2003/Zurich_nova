package com.example.lifepricing.exception;

/** Parent of every "we looked and it is not there" case. Handled as 404. */
public class NotFoundException extends RuntimeException {
    public NotFoundException(String message) {
        super(message);
    }
}
