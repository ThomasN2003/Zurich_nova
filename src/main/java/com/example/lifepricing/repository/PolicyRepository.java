package com.example.lifepricing.repository;

import com.example.lifepricing.model.Policy;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface PolicyRepository extends JpaRepository<Policy, UUID> {}
