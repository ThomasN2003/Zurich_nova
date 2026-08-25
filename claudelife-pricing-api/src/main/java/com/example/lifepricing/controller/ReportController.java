package com.example.lifepricing.controller;

import com.example.lifepricing.service.ClaimService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/reports")
public class ReportController {

    private final ClaimService service;

    public ReportController(ClaimService service) {
        this.service = service;
    }

    @GetMapping("/loss-ratio")
    public List<Map<String, Object>> lossRatio() {
        return service.lossRatio().stream().map(row -> {
            BigDecimal premium = (BigDecimal) row[2];
            BigDecimal paid    = (BigDecimal) row[3];
            BigDecimal ratio   = premium.signum() == 0
                    ? BigDecimal.ZERO
                    : paid.divide(premium, 4, RoundingMode.HALF_UP);
            return Map.<String, Object>of(
                    "segment", row[0],
                    "ageBand", row[1],
                    "premium", premium,
                    "paidClaims", paid,
                    "lossRatio", ratio);
        }).toList();
    }
}
