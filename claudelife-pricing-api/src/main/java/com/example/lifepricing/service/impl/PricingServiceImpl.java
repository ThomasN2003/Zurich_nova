package com.example.lifepricing.service.impl;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.exception.DeclinedQuoteException;
import com.example.lifepricing.exception.RateNotFoundException;
import com.example.lifepricing.repository.BaseRateRepository;
import com.example.lifepricing.service.PricingService;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** The whole pricing formula lives here. No HTTP, no persistence. */
@Service
public class PricingServiceImpl implements PricingService {

    private static final BigDecimal LOADING   = new BigDecimal("0.30");
    private static final BigDecimal FIXED_FEE = new BigDecimal("12.00");
    private static final BigDecimal MAX_BMI   = new BigDecimal("45");
    private static final int MIN_AGE = 18;
    private static final int MAX_AGE = 70;
    private static final int MIN_TERM = 5;
    private static final int MAX_TERM = 40;
    private static final int MAX_EXPIRY_AGE = 75;
    private static final BigDecimal BMI_30    = new BigDecimal("30");
    private static final BigDecimal BMI_35    = new BigDecimal("35");
    private static final BigDecimal TWELVE    = new BigDecimal("12");

    private final BaseRateRepository baseRates;

    public PricingServiceImpl(BaseRateRepository baseRates) {
        this.baseRates = baseRates;
    }

    @Override
    public void checkEligible(QuoteRequest r) {
        if (r.age() < MIN_AGE || r.age() > MAX_AGE) {
            throw new DeclinedQuoteException("Age must be between " + MIN_AGE + " and " + MAX_AGE);
        }
        if (r.termYears() < MIN_TERM || r.termYears() > MAX_TERM) {
            throw new DeclinedQuoteException("Term must be between " + MIN_TERM + " and " + MAX_TERM + " years");
        }
        if (r.bmi().compareTo(MAX_BMI) >= 0) {
            throw new DeclinedQuoteException("BMI of 45 or above");
        }
        if (r.age() + r.termYears() > MAX_EXPIRY_AGE) {
            throw new DeclinedQuoteException("Cover would run past age " + MAX_EXPIRY_AGE);
        }
    }

    /** under 30 = 1.0, 30 to 34.9 = 1.25, 35 and over = 1.6 */
    @Override
    public BigDecimal bmiMultiplier(BigDecimal bmi) {
        if (bmi.compareTo(BMI_30) < 0) return BigDecimal.ONE;
        if (bmi.compareTo(BMI_35) < 0) return new BigDecimal("1.25");
        return new BigDecimal("1.6");
    }

    /** sumAssured * baseRate * bmiMultiplier / (1 - loading) + fixedFee */
    @Override
    public BigDecimal annualPremium(QuoteRequest r) {
        BigDecimal baseRate = baseRates
                .findByRateVersionAndAgeAndSexAndSmoker(RATE_VERSION, r.age(), r.sex(), r.smoker())
                .orElseThrow(() -> new RateNotFoundException(
                        "No base rate for age " + r.age() + ", sex " + r.sex() + ", smoker " + r.smoker()))
                .getRate();

        return r.sumAssured()
                .multiply(baseRate)
                .multiply(bmiMultiplier(r.bmi()))
                .divide(BigDecimal.ONE.subtract(LOADING), 10, RoundingMode.HALF_UP)
                .add(FIXED_FEE)
                .setScale(2, RoundingMode.HALF_UP);
    }

    @Override
    public BigDecimal monthlyPremium(BigDecimal annual) {
        return annual.divide(TWELVE, 2, RoundingMode.HALF_UP);
    }
}
