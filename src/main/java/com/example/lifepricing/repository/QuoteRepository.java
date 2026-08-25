package com.example.lifepricing.repository;

import com.example.lifepricing.model.Quote;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface QuoteRepository extends JpaRepository<Quote, UUID> {}
