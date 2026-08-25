package com.example.lifepricing.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

/**
 * Shape only. Anything here failing is a malformed request (422).
 * The underwriting limits (age, term, BMI) are decline decisions and live in PricingService.
 */
public record QuoteRequest(
        @NotNull @Positive Integer age,
        @NotNull @Pattern(regexp = "M|F", message = "must be M or F") String sex,
        @NotNull Boolean smoker,
        @NotNull @Positive BigDecimal bmi,
        @NotNull @DecimalMin("10000") @DecimalMax("2000000") BigDecimal sumAssured,
        @NotNull @Positive Integer termYears
) {}
