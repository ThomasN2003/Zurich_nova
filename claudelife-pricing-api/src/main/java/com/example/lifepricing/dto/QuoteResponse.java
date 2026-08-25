package com.example.lifepricing.dto;

import com.example.lifepricing.model.Quote;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record QuoteResponse(
        UUID quoteId,
        String status,
        BigDecimal annualPremium,
        BigDecimal monthlyPremium,
        LocalDate expiresAt
) {
    public static QuoteResponse from(Quote q) {
        return new QuoteResponse(q.getId(), q.getStatus(),
                q.getAnnualPremium(), q.getMonthlyPremium(), q.getExpiresAt());
    }
}
