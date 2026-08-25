package com.example.lifepricing.controller;

import com.example.lifepricing.model.TrainingData;
import com.example.lifepricing.service.TrainingDataService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/training-data")
public class TrainingDataController {

    private final TrainingDataService service;

    public TrainingDataController(TrainingDataService service) {
        this.service = service;
    }

    @GetMapping("/{id}")
    public TrainingData get(@PathVariable Long id) {
        return service.get(id);
    }

    @GetMapping
    public List<TrainingData> list(@RequestParam(defaultValue = "20") int limit) {
        return service.list(limit);
    }

    @GetMapping("/count")
    public Map<String, Long> count() {
        return Map.of("count", service.count());
    }
}
