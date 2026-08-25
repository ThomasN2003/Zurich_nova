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
