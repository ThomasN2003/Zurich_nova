package com.example.lifepricing.service.impl;

import com.example.lifepricing.dto.ClaimRequest;
import com.example.lifepricing.exception.ClaimNotFoundException;
import com.example.lifepricing.exception.InvalidStateException;
import com.example.lifepricing.exception.PolicyNotFoundException;
import com.example.lifepricing.model.Claim;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.repository.ClaimRepository;
import com.example.lifepricing.repository.PolicyRepository;
import com.example.lifepricing.service.ClaimService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Set;
import java.util.UUID;

@Service
public class ClaimServiceImpl implements ClaimService {

    private static final Set<String> ALLOWED = Set.of("PAID", "REJECTED");

    private final ClaimRepository claims;
    private final PolicyRepository policies;

    public ClaimServiceImpl(ClaimRepository claims, PolicyRepository policies) {
        this.claims = claims;
        this.policies = policies;
    }

    @Override
    @Transactional
    public Claim register(UUID policyId, ClaimRequest r) {
        Policy p = policies.findById(policyId)
                .orElseThrow(() -> new PolicyNotFoundException("Policy " + policyId + " not found"));

        if (!"ACTIVE".equals(p.getStatus())) {
            throw new InvalidStateException("Policy is " + p.getStatus());
        }

        Claim c = new Claim();
        c.setPolicyId(p.getId());
        c.setEventDate(r.eventDate());
        c.setAmount(r.amount());
        c.setStatus("OPEN");
        return claims.save(c);
    }

    @Override
    @Transactional
    public Claim updateStatus(UUID claimId, String status) {
        if (status == null || !ALLOWED.contains(status)) {
            throw new InvalidStateException("Status must be PAID or REJECTED");
        }

        Claim c = claims.findById(claimId)
                .orElseThrow(() -> new ClaimNotFoundException("Claim " + claimId + " not found"));

        if (!"OPEN".equals(c.getStatus())) {
            throw new InvalidStateException("Claim is already " + c.getStatus());
        }

        c.setStatus(status);

        if ("PAID".equals(status)) {
            policies.findById(c.getPolicyId()).ifPresent(p -> p.setStatus("CLAIMED"));
        }
        return c;
    }

    @Override
    public List<Object[]> lossRatio() {
        return claims.lossRatio();
    }
}
