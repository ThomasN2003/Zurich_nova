package com.example.lifepricing.controller;

import com.example.lifepricing.dto.ClaimRequest;
import com.example.lifepricing.model.Claim;
import com.example.lifepricing.service.ClaimService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping
public class ClaimController {

    private final ClaimService service;

    public ClaimController(ClaimService service) {
        this.service = service;
    }

    @PostMapping("/policies/{policyId}/claims")
    @ResponseStatus(HttpStatus.CREATED)
    public Claim register(@PathVariable UUID policyId, @Valid @RequestBody ClaimRequest request) {
        return service.register(policyId, request);
    }

    @PatchMapping("/claims/{id}")
    public Claim updateStatus(@PathVariable UUID id, @RequestBody Map<String, String> body) {
        return service.updateStatus(id, body.get("status"));
    }
}
