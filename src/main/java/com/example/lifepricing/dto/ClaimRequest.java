package com.example.lifepricing.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.time.LocalDate;

public record ClaimRequest(
        @NotNull @PastOrPresent LocalDate eventDate,
        @NotNull @DecimalMin("0.01") BigDecimal amount
) {}
