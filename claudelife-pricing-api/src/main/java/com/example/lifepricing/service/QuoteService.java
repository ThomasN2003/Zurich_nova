package com.example.lifepricing.service;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.model.Quote;
import java.util.UUID;

public interface QuoteService {

    Quote create(QuoteRequest request);

    Quote get(UUID id);

    Policy accept(UUID quoteId);
}
