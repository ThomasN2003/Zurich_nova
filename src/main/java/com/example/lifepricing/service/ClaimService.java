package com.example.lifepricing.service;

import com.example.lifepricing.dto.ClaimRequest;
import com.example.lifepricing.model.Claim;
import java.util.List;
import java.util.UUID;

public interface ClaimService {

    Claim register(UUID policyId, ClaimRequest request);

    Claim updateStatus(UUID claimId, String status);

    List<Object[]> lossRatio();
}
