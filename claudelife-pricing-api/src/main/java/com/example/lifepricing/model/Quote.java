package com.example.lifepricing.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "quotes")
public class Quote {

    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    private Integer age;
    private String sex;
    private Boolean smoker;
    private BigDecimal bmi;

    @Column(name = "sum_assured")     private BigDecimal sumAssured;
    @Column(name = "term_years")      private Integer termYears;
    @Column(name = "rate_version")    private String rateVersion;
    @Column(name = "annual_premium")  private BigDecimal annualPremium;
    @Column(name = "monthly_premium") private BigDecimal monthlyPremium;

    private String status;

    @Column(name = "expires_at") private LocalDate expiresAt;
    @Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;

    public UUID getId() { return id; }
    public Integer getAge() { return age; }
    public void setAge(Integer age) { this.age = age; }
    public String getSex() { return sex; }
    public void setSex(String sex) { this.sex = sex; }
    public Boolean getSmoker() { return smoker; }
    public void setSmoker(Boolean smoker) { this.smoker = smoker; }
    public BigDecimal getBmi() { return bmi; }
    public void setBmi(BigDecimal bmi) { this.bmi = bmi; }
    public BigDecimal getSumAssured() { return sumAssured; }
    public void setSumAssured(BigDecimal sumAssured) { this.sumAssured = sumAssured; }
    public Integer getTermYears() { return termYears; }
    public void setTermYears(Integer termYears) { this.termYears = termYears; }
    public String getRateVersion() { return rateVersion; }
    public void setRateVersion(String rateVersion) { this.rateVersion = rateVersion; }
    public BigDecimal getAnnualPremium() { return annualPremium; }
    public void setAnnualPremium(BigDecimal annualPremium) { this.annualPremium = annualPremium; }
    public BigDecimal getMonthlyPremium() { return monthlyPremium; }
    public void setMonthlyPremium(BigDecimal monthlyPremium) { this.monthlyPremium = monthlyPremium; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDate getExpiresAt() { return expiresAt; }
    public void setExpiresAt(LocalDate expiresAt) { this.expiresAt = expiresAt; }
    public Instant getCreatedAt() { return createdAt; }
}
