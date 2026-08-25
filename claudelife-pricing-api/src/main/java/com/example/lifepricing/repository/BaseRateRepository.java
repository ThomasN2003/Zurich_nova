package com.example.lifepricing.repository;

import com.example.lifepricing.model.BaseRate;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface BaseRateRepository extends JpaRepository<BaseRate, BaseRate.Key> {
    Optional<BaseRate> findByRateVersionAndAgeAndSexAndSmoker(
            String rateVersion, Integer age, String sex, Boolean smoker);
}
