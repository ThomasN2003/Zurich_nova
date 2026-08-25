package com.example.lifepricing.controller;

import com.example.lifepricing.dto.QuoteRequest;
import com.example.lifepricing.dto.QuoteResponse;
import com.example.lifepricing.model.Policy;
import com.example.lifepricing.service.QuoteService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/quotes")
public class QuoteController {

    private final QuoteService service;

    public QuoteController(QuoteService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public QuoteResponse create(@Valid @RequestBody QuoteRequest request) {
        return QuoteResponse.from(service.create(request));
    }

    @GetMapping("/{id}")
    public QuoteResponse get(@PathVariable UUID id) {
        return QuoteResponse.from(service.get(id));
    }

    @PostMapping("/{id}/accept")
    @ResponseStatus(HttpStatus.CREATED)
    public Policy accept(@PathVariable UUID id) {
        return service.accept(id);
    }
}
