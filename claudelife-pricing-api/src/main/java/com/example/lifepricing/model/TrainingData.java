package com.example.lifepricing.model;

import jakarta.persistence.*;
import java.math.BigDecimal;

/** One row of medical_insurance_processed.csv. Read only, never written by the app. */
@Entity
@Table(name = "training_data")
public class TrainingData {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Integer age;
    private String gender;
    private BigDecimal bmi;
    private Integer children;

    @Column(name = "discount_eligibility")      private String discountEligibility;
    private String region;
    private BigDecimal expenses;
    private BigDecimal premium;

    @Column(name = "discount_eligibility_flag") private Integer discountEligibilityFlag;
    @Column(name = "gender_flag")               private Integer genderFlag;
    @Column(name = "bmi_category")              private String bmiCategory;
    @Column(name = "age_group")                 private String ageGroup;
    @Column(name = "large_family")              private Integer largeFamily;
    @Column(name = "age_bmi_interaction")       private BigDecimal ageBmiInteraction;
    @Column(name = "expense_per_child")         private BigDecimal expensePerChild;
    @Column(name = "premium_expense_ratio")     private BigDecimal premiumExpenseRatio;
    @Column(name = "high_cost_customer")        private Integer highCostCustomer;

    public Long getId() { return id; }
    public Integer getAge() { return age; }
    public String getGender() { return gender; }
    public BigDecimal getBmi() { return bmi; }
    public Integer getChildren() { return children; }
    public String getDiscountEligibility() { return discountEligibility; }
    public String getRegion() { return region; }
    public BigDecimal getExpenses() { return expenses; }
    public BigDecimal getPremium() { return premium; }
    public Integer getDiscountEligibilityFlag() { return discountEligibilityFlag; }
    public Integer getGenderFlag() { return genderFlag; }
    public String getBmiCategory() { return bmiCategory; }
    public String getAgeGroup() { return ageGroup; }
    public Integer getLargeFamily() { return largeFamily; }
    public BigDecimal getAgeBmiInteraction() { return ageBmiInteraction; }
    public BigDecimal getExpensePerChild() { return expensePerChild; }
    public BigDecimal getPremiumExpenseRatio() { return premiumExpenseRatio; }
    public Integer getHighCostCustomer() { return highCostCustomer; }
}
