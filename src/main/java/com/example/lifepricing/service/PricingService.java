package com.example.lifepricing.service;

import com.example.lifepricing.dto.QuoteRequest;
import java.math.BigDecimal;

public interface PricingService {

    String RATE_VERSION = "2026-08";

    /** Throws DeclinedQuoteException if the applicant falls outside the underwriting limits. */
    void checkEligible(QuoteRequest request);

    BigDecimal bmiMultiplier(BigDecimal bmi);

    BigDecimal annualPremium(QuoteRequest request);

    BigDecimal monthlyPremium(BigDecimal annualPremium);
}
