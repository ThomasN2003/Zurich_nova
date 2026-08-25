package com.example.lifepricing.service.impl;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.exception.DeclinedQuoteException;
import com.example.lifepricing.exception.InvalidStateException;
import com.example.lifepricing.exception.QuoteNotFoundException;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.model.Quote;
import com.example.lifepricing.repository.PolicyRepository;
import com.example.lifepricing.repository.QuoteRepository;
import com.example.lifepricing.service.PricingService;
import com.example.lifepricing.service.QuoteService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

@Service
public class QuoteServiceImpl implements QuoteService {

    private static final int VALID_FOR_DAYS = 30;

    private final QuoteRepository quotes;
    private final PolicyRepository policies;
    private final PricingService pricing;

    public QuoteServiceImpl(QuoteRepository quotes, PolicyRepository policies, PricingService pricing) {
        this.quotes = quotes;
        this.policies = policies;
        this.pricing = pricing;
    }

    /**
     * FR-3: every quote is stored, declines included.
     * noRollbackFor keeps the DECLINED row when the exception propagates.
     */
    @Override
    @Transactional(noRollbackFor = DeclinedQuoteException.class)
    public Quote create(QuoteRequest r) {
        Quote q = newQuote(r);

        try {
            pricing.checkEligible(r);
        } catch (DeclinedQuoteException e) {
            q.setStatus("DECLINED");
            quotes.save(q);
            throw e;
        }

        BigDecimal annual = pricing.annualPremium(r);
        q.setAnnualPremium(annual);
        q.setMonthlyPremium(pricing.monthlyPremium(annual));
        q.setStatus("QUOTED");
        return quotes.save(q);
    }

    @Override
    public Quote get(UUID id) {
        return quotes.findById(id)
                .orElseThrow(() -> new QuoteNotFoundException("Quote " + id + " not found"));
    }

    @Override
    @Transactional
    public Policy accept(UUID quoteId) {
        Quote q = get(quoteId);

        if (!"QUOTED".equals(q.getStatus())) {
            throw new InvalidStateException("Quote is " + q.getStatus());
        }
        if (q.getExpiresAt().isBefore(LocalDate.now())) {
            q.setStatus("EXPIRED");
            throw new InvalidStateException("Quote has expired");
        }

        q.setStatus("ACCEPTED");

        Policy p = new Policy();
        p.setQuoteId(q.getId());
        p.setPolicyNumber("POL-" + System.currentTimeMillis());
        p.setStartDate(LocalDate.now());
        p.setEndDate(LocalDate.now().plusYears(q.getTermYears()));
        p.setAnnualPremium(q.getAnnualPremium());
        p.setStatus("ACTIVE");
        return policies.save(p);
    }

    private Quote newQuote(QuoteRequest r) {
        Quote q = new Quote();
        q.setAge(r.age());
        q.setSex(r.sex());
        q.setSmoker(r.smoker());
        q.setBmi(r.bmi());
        q.setSumAssured(r.sumAssured());
        q.setTermYears(r.termYears());
        q.setRateVersion(PricingService.RATE_VERSION);
        q.setExpiresAt(LocalDate.now().plusDays(VALID_FOR_DAYS));
        return q;
    }
}
