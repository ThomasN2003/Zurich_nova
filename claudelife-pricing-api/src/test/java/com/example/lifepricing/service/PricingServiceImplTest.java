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
