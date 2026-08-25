package com.example.lifepricing.model;

import jakarta.persistence.*;
import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Objects;

@Entity
@Table(name = "base_rates")
@IdClass(BaseRate.Key.class)
public class BaseRate {

    @Id @Column(name = "rate_version") private String rateVersion;
    @Id private Integer age;
    @Id private String sex;
    @Id private Boolean smoker;

    private BigDecimal rate;

    public String getRateVersion() { return rateVersion; }
    public Integer getAge() { return age; }
    public String getSex() { return sex; }
    public Boolean getSmoker() { return smoker; }
    public BigDecimal getRate() { return rate; }

    public static class Key implements Serializable {
        private String rateVersion;
        private Integer age;
        private String sex;
        private Boolean smoker;

        @Override public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof Key k)) return false;
            return Objects.equals(rateVersion, k.rateVersion) && Objects.equals(age, k.age)
                && Objects.equals(sex, k.sex) && Objects.equals(smoker, k.smoker);
        }
        @Override public int hashCode() { return Objects.hash(rateVersion, age, sex, smoker); }
    }
}
