#!/usr/bin/env bash
# Run from the project root (the folder with pom.xml).
# Adds JUnit 5 + Mockito unit tests for the pricing and quote services.
set -euo pipefail

[ -f pom.xml ] || { echo "No pom.xml here. cd into the project root first."; exit 1; }

TEST="src/test/java/com/example/lifepricing"
mkdir -p "$TEST/service"

# ============================================================================
# PricingServiceImpl — the formula and the underwriting limits.
# No database: the BaseRateRepository is mocked.
# ============================================================================

cat > "$TEST/service/PricingServiceImplTest.java" << 'EOF'
package com.example.lifepricing.service;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.exception.DeclinedQuoteException;
import com.example.lifepricing.exception.RateNotFoundException;
import com.example.lifepricing.model.BaseRate;
import com.example.lifepricing.repository.BaseRateRepository;
import com.example.lifepricing.service.impl.PricingServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.Mockito;

import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.when;

class PricingServiceImplTest {

    private BaseRateRepository baseRates;
    private PricingServiceImpl pricing;

    @BeforeEach
    void setUp() {
        baseRates = Mockito.mock(BaseRateRepository.class);
        pricing = new PricingServiceImpl(baseRates);
    }

    /** Stubs the repository to return a fixed rate for any lookup. */
    private void givenRate(String rate) {
        BaseRate row = Mockito.mock(BaseRate.class);
        when(row.getRate()).thenReturn(new BigDecimal(rate));
        when(baseRates.findByRateVersionAndAgeAndSexAndSmoker(
                anyString(), anyInt(), anyString(), anyBoolean()))
                .thenReturn(Optional.of(row));
    }

    private QuoteRequest request(int age, String sex, boolean smoker, String bmi,
                                 String sumAssured, int termYears) {
        return new QuoteRequest(age, sex, smoker, new BigDecimal(bmi),
                new BigDecimal(sumAssured), termYears);
    }

    // ------------------------------------------------------------ formula

    @Nested
    @DisplayName("annualPremium")
    class AnnualPremium {

        @Test
        @DisplayName("reproduces the worked example in the README")
        void readmeExample() {
            givenRate("0.00106590");

            BigDecimal annual = pricing.annualPremium(
                    request(35, "M", false, "26.0", "250000", 25));

            // 250000 * 0.0010659 * 1.0 / 0.70 + 12.00
            assertThat(annual).isEqualByComparingTo("392.68");
            assertThat(pricing.monthlyPremium(annual)).isEqualByComparingTo("32.72");
        }

        @Test
        @DisplayName("a smoker rate doubles the premium net of the fixed fee")
        void smokerCostsMore() {
            givenRate("0.00213180");

            assertThat(pricing.annualPremium(request(35, "M", true, "26.0", "250000", 25)))
                    .isEqualByComparingTo("773.36");
        }

        @Test
        @DisplayName("premium scales linearly with sum assured")
        void scalesWithSumAssured() {
            givenRate("0.00106590");

            BigDecimal small = pricing.annualPremium(request(35, "M", false, "26.0", "100000", 25));
            BigDecimal large = pricing.annualPremium(request(35, "M", false, "26.0", "200000", 25));

            // the fixed fee is flat, so double the cover is double the risk part only
            assertThat(large.subtract(new BigDecimal("12.00")))
                    .isEqualByComparingTo(small.subtract(new BigDecimal("12.00"))
                            .multiply(new BigDecimal("2")));
        }

        @Test
        @DisplayName("a BMI loading raises the premium")
        void bmiLoadingApplies() {
            givenRate("0.00106590");

            // BMI 32 falls in the 1.25 band
            assertThat(pricing.annualPremium(request(35, "M", false, "32.0", "250000", 25)))
                    .isEqualByComparingTo("487.85");

            // BMI 38 falls in the 1.6 band
            assertThat(pricing.annualPremium(request(35, "M", false, "38.0", "250000", 25)))
                    .isEqualByComparingTo("621.09");
        }

        @Test
        @DisplayName("is rounded to two decimal places")
        void roundsToPence() {
            givenRate("0.00106590");

            assertThat(pricing.annualPremium(request(35, "M", false, "26.0", "250000", 25)).scale())
                    .isEqualTo(2);
        }

        @Test
        @DisplayName("throws when no base rate exists for the applicant")
        void missingRate() {
            when(baseRates.findByRateVersionAndAgeAndSexAndSmoker(
                    anyString(), anyInt(), anyString(), anyBoolean()))
                    .thenReturn(Optional.empty());

            assertThatThrownBy(() -> pricing.annualPremium(
                    request(35, "M", false, "26.0", "250000", 25)))
                    .isInstanceOf(RateNotFoundException.class);
        }
    }

    // --------------------------------------------------------- multipliers

    @ParameterizedTest(name = "BMI {0} -> multiplier {1}")
    @CsvSource({
            "18.0, 1.0",
            "29.9, 1.0",
            "30.0, 1.25",
            "34.9, 1.25",
            "35.0, 1.6",
            "44.9, 1.6"
    })
    @DisplayName("BMI bands map to the documented multipliers, boundaries included")
    void bmiMultiplierBands(String bmi, String expected) {
        assertThat(pricing.bmiMultiplier(new BigDecimal(bmi)))
                .isEqualByComparingTo(expected);
    }

    // ------------------------------------------------------ underwriting

    @Nested
    @DisplayName("checkEligible")
    class CheckEligible {

        @Test
        @DisplayName("accepts an applicant inside every limit")
        void acceptsGoodRisk() {
            pricing.checkEligible(request(35, "M", false, "26.0", "250000", 25));
            // no exception is the assertion
        }

        @ParameterizedTest(name = "age {0} is declined")
        @CsvSource({"17", "71"})
        void declinesAgeOutsideRange(int age) {
            assertThatThrownBy(() -> pricing.checkEligible(
                    request(age, "M", false, "26.0", "250000", 5)))
                    .isInstanceOf(DeclinedQuoteException.class)
                    .hasMessageContaining("Age");
        }

        @ParameterizedTest(name = "term {0} is declined")
        @CsvSource({"4", "41"})
        void declinesTermOutsideRange(int term) {
            assertThatThrownBy(() -> pricing.checkEligible(
                    request(25, "M", false, "26.0", "250000", term)))
                    .isInstanceOf(DeclinedQuoteException.class)
                    .hasMessageContaining("Term");
        }

        @Test
        @DisplayName("declines BMI of 45 or above")
        void declinesHighBmi() {
            assertThatThrownBy(() -> pricing.checkEligible(
                    request(35, "M", false, "45.0", "250000", 25)))
                    .isInstanceOf(DeclinedQuoteException.class)
                    .hasMessageContaining("BMI");
        }

        @Test
        @DisplayName("accepts BMI just under the limit")
        void acceptsBmiJustUnder() {
            pricing.checkEligible(request(35, "M", false, "44.9", "250000", 25));
        }

        @Test
        @DisplayName("declines when cover would run past age 75")
        void declinesLateExpiry() {
            // 55 + 25 = 80
            assertThatThrownBy(() -> pricing.checkEligible(
                    request(55, "M", false, "26.0", "250000", 25)))
                    .isInstanceOf(DeclinedQuoteException.class)
                    .hasMessageContaining("75");
        }

        @Test
        @DisplayName("accepts when cover ends exactly at 75")
        void acceptsExpiryAtSeventyFive() {
            pricing.checkEligible(request(50, "M", false, "26.0", "250000", 25));
        }
    }
}
EOF

# ============================================================================
# QuoteServiceImpl — persistence, declines, accept, expiry.
# Repositories and PricingService are all mocked.
# ============================================================================

cat > "$TEST/service/QuoteServiceImplTest.java" << 'EOF'
package com.example.lifepricing.service;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.exception.DeclinedQuoteException;
import com.example.lifepricing.exception.InvalidStateException;
import com.example.lifepricing.exception.QuoteNotFoundException;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.model.Quote;
import com.example.lifepricing.repository.PolicyRepository;
import com.example.lifepricing.repository.QuoteRepository;
import com.example.lifepricing.service.impl.QuoteServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class QuoteServiceImplTest {

    private QuoteRepository quotes;
    private PolicyRepository policies;
    private PricingService pricing;
    private QuoteServiceImpl service;

    @BeforeEach
    void setUp() {
        quotes = mock(QuoteRepository.class);
        policies = mock(PolicyRepository.class);
        pricing = mock(PricingService.class);
        service = new QuoteServiceImpl(quotes, policies, pricing);

        // save() returns whatever it was given
        when(quotes.save(any(Quote.class))).thenAnswer(i -> i.getArgument(0));
        when(policies.save(any(Policy.class))).thenAnswer(i -> i.getArgument(0));
    }

    private QuoteRequest request() {
        return new QuoteRequest(35, "M", false, new BigDecimal("26.0"),
                new BigDecimal("250000"), 25);
    }

    // -------------------------------------------------------------- create

    @Test
    @DisplayName("a priced quote is saved as QUOTED with both premiums")
    void savesQuotedQuote() {
        when(pricing.annualPremium(any())).thenReturn(new BigDecimal("392.68"));
        when(pricing.monthlyPremium(any())).thenReturn(new BigDecimal("32.72"));

        Quote saved = service.create(request());

        assertThat(saved.getStatus()).isEqualTo("QUOTED");
        assertThat(saved.getAnnualPremium()).isEqualByComparingTo("392.68");
        assertThat(saved.getMonthlyPremium()).isEqualByComparingTo("32.72");
        assertThat(saved.getRateVersion()).isEqualTo(PricingService.RATE_VERSION);
        verify(quotes).save(any(Quote.class));
    }

    @Test
    @DisplayName("the applicant's inputs are stored so the quote can be reproduced (FR-3)")
    void storesInputs() {
        when(pricing.annualPremium(any())).thenReturn(new BigDecimal("392.68"));
        when(pricing.monthlyPremium(any())).thenReturn(new BigDecimal("32.72"));

        Quote saved = service.create(request());

        assertThat(saved.getAge()).isEqualTo(35);
        assertThat(saved.getSex()).isEqualTo("M");
        assertThat(saved.getSmoker()).isFalse();
        assertThat(saved.getBmi()).isEqualByComparingTo("26.0");
        assertThat(saved.getSumAssured()).isEqualByComparingTo("250000");
        assertThat(saved.getTermYears()).isEqualTo(25);
    }

    @Test
    @DisplayName("a quote expires 30 days out (FR-4)")
    void expiresInThirtyDays() {
        when(pricing.annualPremium(any())).thenReturn(new BigDecimal("392.68"));
        when(pricing.monthlyPremium(any())).thenReturn(new BigDecimal("32.72"));

        assertThat(service.create(request()).getExpiresAt())
                .isEqualTo(LocalDate.now().plusDays(30));
    }

    @Test
    @DisplayName("a declined quote is still stored, as DECLINED with no premium (FR-3)")
    void storesDeclinedQuote() {
        doThrow(new DeclinedQuoteException("BMI of 45 or above"))
                .when(pricing).checkEligible(any());

        assertThatThrownBy(() -> service.create(request()))
                .isInstanceOf(DeclinedQuoteException.class);

        ArgumentCaptor<Quote> captor = ArgumentCaptor.forClass(Quote.class);
        verify(quotes).save(captor.capture());

        Quote declined = captor.getValue();
        assertThat(declined.getStatus()).isEqualTo("DECLINED");
        assertThat(declined.getAnnualPremium()).isNull();
        assertThat(declined.getMonthlyPremium()).isNull();
    }

    @Test
    @DisplayName("a declined applicant is never priced")
    void declinedIsNotPriced() {
        doThrow(new DeclinedQuoteException("Age must be between 18 and 70"))
                .when(pricing).checkEligible(any());

        assertThatThrownBy(() -> service.create(request()))
                .isInstanceOf(DeclinedQuoteException.class);

        verify(pricing, never()).annualPremium(any());
    }

    // ----------------------------------------------------------------- get

    @Test
    @DisplayName("an unknown id is a 404")
    void getUnknownId() {
        UUID id = UUID.randomUUID();
        when(quotes.findById(id)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.get(id))
                .isInstanceOf(QuoteNotFoundException.class);
    }

    // -------------------------------------------------------------- accept

    private Quote quotedQuote(UUID id, LocalDate expiresAt) {
        Quote q = new Quote();
        q.setAge(35);
        q.setSex("M");
        q.setSmoker(false);
        q.setBmi(new BigDecimal("26.0"));
        q.setSumAssured(new BigDecimal("250000"));
        q.setTermYears(25);
        q.setAnnualPremium(new BigDecimal("392.68"));
        q.setStatus("QUOTED");
        q.setExpiresAt(expiresAt);
        when(quotes.findById(id)).thenReturn(Optional.of(q));
        return q;
    }

    @Test
    @DisplayName("accepting a live quote creates an ACTIVE policy for the full term")
    void acceptCreatesPolicy() {
        UUID id = UUID.randomUUID();
        Quote q = quotedQuote(id, LocalDate.now().plusDays(10));

        Policy p = service.accept(id);

        assertThat(p.getStatus()).isEqualTo("ACTIVE");
        assertThat(p.getAnnualPremium()).isEqualByComparingTo("392.68");
        assertThat(p.getStartDate()).isEqualTo(LocalDate.now());
        assertThat(p.getEndDate()).isEqualTo(LocalDate.now().plusYears(25));
        assertThat(p.getPolicyNumber()).startsWith("POL-");
        assertThat(q.getStatus()).isEqualTo("ACCEPTED");
    }

    @Test
    @DisplayName("an expired quote cannot be accepted")
    void cannotAcceptExpired() {
        UUID id = UUID.randomUUID();
        quotedQuote(id, LocalDate.now().minusDays(1));

        assertThatThrownBy(() -> service.accept(id))
                .isInstanceOf(InvalidStateException.class)
                .hasMessageContaining("expired");

        verify(policies, never()).save(any());
    }

    @Test
    @DisplayName("a quote cannot be accepted twice")
    void cannotAcceptTwice() {
        UUID id = UUID.randomUUID();
        Quote q = quotedQuote(id, LocalDate.now().plusDays(10));
        q.setStatus("ACCEPTED");

        assertThatThrownBy(() -> service.accept(id))
                .isInstanceOf(InvalidStateException.class);
    }

    @Test
    @DisplayName("a declined quote cannot be accepted")
    void cannotAcceptDeclined() {
        UUID id = UUID.randomUUID();
        Quote q = quotedQuote(id, LocalDate.now().plusDays(10));
        q.setStatus("DECLINED");

        assertThatThrownBy(() -> service.accept(id))
                .isInstanceOf(InvalidStateException.class);
    }
}
EOF

# ============================================================================
# ClaimServiceImpl — registration and the status transitions.
# ============================================================================

cat > "$TEST/service/ClaimServiceImplTest.java" << 'EOF'
package com.example.lifepricing.service;

import com.example.lifepricing.dto.ClaimRequest;
import com.example.lifepricing.exception.ClaimNotFoundException;
import com.example.lifepricing.exception.InvalidStateException;
import com.example.lifepricing.exception.PolicyNotFoundException;
import com.example.lifepricing.model.Claim;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.repository.ClaimRepository;
import com.example.lifepricing.repository.PolicyRepository;
import com.example.lifepricing.service.impl.ClaimServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class ClaimServiceImplTest {

    private ClaimRepository claims;
    private PolicyRepository policies;
    private ClaimServiceImpl service;

    @BeforeEach
    void setUp() {
        claims = mock(ClaimRepository.class);
        policies = mock(PolicyRepository.class);
        service = new ClaimServiceImpl(claims, policies);

        when(claims.save(any(Claim.class))).thenAnswer(i -> i.getArgument(0));
    }

    private ClaimRequest request() {
        return new ClaimRequest(LocalDate.now().minusDays(1), new BigDecimal("250000"));
    }

    private Policy policy(UUID id, String status) {
        Policy p = new Policy();
        p.setStatus(status);
        when(policies.findById(id)).thenReturn(Optional.of(p));
        return p;
    }

    // ------------------------------------------------------------ register

    @Test
    @DisplayName("a claim against an active policy is registered as OPEN (FR-5)")
    void registersClaim() {
        UUID policyId = UUID.randomUUID();
        policy(policyId, "ACTIVE");

        Claim c = service.register(policyId, request());

        assertThat(c.getStatus()).isEqualTo("OPEN");
        assertThat(c.getAmount()).isEqualByComparingTo("250000");
        assertThat(c.getEventDate()).isEqualTo(LocalDate.now().minusDays(1));
    }

    @Test
    @DisplayName("an unknown policy is a 404")
    void unknownPolicy() {
        UUID policyId = UUID.randomUUID();
        when(policies.findById(policyId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.register(policyId, request()))
                .isInstanceOf(PolicyNotFoundException.class);
    }

    @ParameterizedTest(name = "a {0} policy cannot be claimed against")
    @ValueSource(strings = {"CLAIMED", "EXPIRED", "CANCELLED"})
    void policyMustBeActive(String status) {
        UUID policyId = UUID.randomUUID();
        policy(policyId, status);

        assertThatThrownBy(() -> service.register(policyId, request()))
                .isInstanceOf(InvalidStateException.class);

        verify(claims, never()).save(any());
    }

    // ------------------------------------------------------- updateStatus

    private Claim openClaim(UUID claimId, UUID policyId) {
        Claim c = new Claim();
        c.setPolicyId(policyId);
        c.setAmount(new BigDecimal("250000"));
        c.setStatus("OPEN");
        when(claims.findById(claimId)).thenReturn(Optional.of(c));
        return c;
    }

    @Test
    @DisplayName("paying a claim marks the policy CLAIMED")
    void payingClaimUpdatesPolicy() {
        UUID claimId = UUID.randomUUID();
        UUID policyId = UUID.randomUUID();
        openClaim(claimId, policyId);
        Policy p = policy(policyId, "ACTIVE");

        Claim c = service.updateStatus(claimId, "PAID");

        assertThat(c.getStatus()).isEqualTo("PAID");
        assertThat(p.getStatus()).isEqualTo("CLAIMED");
    }

    @Test
    @DisplayName("rejecting a claim leaves the policy ACTIVE")
    void rejectingClaimLeavesPolicyActive() {
        UUID claimId = UUID.randomUUID();
        UUID policyId = UUID.randomUUID();
        openClaim(claimId, policyId);
        Policy p = policy(policyId, "ACTIVE");

        Claim c = service.updateStatus(claimId, "REJECTED");

        assertThat(c.getStatus()).isEqualTo("REJECTED");
        assertThat(p.getStatus()).isEqualTo("ACTIVE");
    }

    @ParameterizedTest(name = "status {0} is refused")
    @ValueSource(strings = {"OPEN", "SETTLED", "paid", ""})
    void onlyPaidOrRejectedAllowed(String status) {
        assertThatThrownBy(() -> service.updateStatus(UUID.randomUUID(), status))
                .isInstanceOf(InvalidStateException.class);
    }

    @Test
    @DisplayName("a null status is refused")
    void nullStatusRefused() {
        assertThatThrownBy(() -> service.updateStatus(UUID.randomUUID(), null))
                .isInstanceOf(InvalidStateException.class);
    }

    @Test
    @DisplayName("an already settled claim cannot be settled again")
    void cannotSettleTwice() {
        UUID claimId = UUID.randomUUID();
        Claim c = openClaim(claimId, UUID.randomUUID());
        c.setStatus("PAID");

        assertThatThrownBy(() -> service.updateStatus(claimId, "REJECTED"))
                .isInstanceOf(InvalidStateException.class)
                .hasMessageContaining("already");
    }

    @Test
    @DisplayName("an unknown claim is a 404")
    void unknownClaim() {
        UUID claimId = UUID.randomUUID();
        when(claims.findById(claimId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.updateStatus(claimId, "PAID"))
                .isInstanceOf(ClaimNotFoundException.class);
    }
}
EOF

echo "Done. Now run: mvn test"