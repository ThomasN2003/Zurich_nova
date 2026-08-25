package com.example.lifepricing.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "policies")
public class Policy {

    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "quote_id")       private UUID quoteId;
    @Column(name = "policy_number")  private String policyNumber;
    @Column(name = "start_date")     private LocalDate startDate;
    @Column(name = "end_date")       private LocalDate endDate;
    @Column(name = "annual_premium") private BigDecimal annualPremium;

    private String status;

    public UUID getId() { return id; }
    public UUID getQuoteId() { return quoteId; }
    public void setQuoteId(UUID quoteId) { this.quoteId = quoteId; }
    public String getPolicyNumber() { return policyNumber; }
    public void setPolicyNumber(String policyNumber) { this.policyNumber = policyNumber; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public BigDecimal getAnnualPremium() { return annualPremium; }
    public void setAnnualPremium(BigDecimal annualPremium) { this.annualPremium = annualPremium; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
