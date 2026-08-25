package com.example.lifepricing.exception;

/** A business decline, not a bad request. The payload was fine, we just will not cover them. */
public class DeclinedQuoteException extends RuntimeException {
    public DeclinedQuoteException(String reason) {
        super(reason);
    }
}
