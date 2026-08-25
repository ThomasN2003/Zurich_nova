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
