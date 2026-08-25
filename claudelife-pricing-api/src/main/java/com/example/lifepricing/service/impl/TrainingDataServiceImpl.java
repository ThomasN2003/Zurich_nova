package com.example.lifepricing.service.impl;

import com.example.lifepricing.exception.NotFoundException;
import com.example.lifepricing.model.TrainingData;
import com.example.lifepricing.repository.TrainingDataRepository;
import com.example.lifepricing.service.TrainingDataService;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TrainingDataServiceImpl implements TrainingDataService {

    private static final int MAX_LIMIT = 200;

    private final TrainingDataRepository rows;

    public TrainingDataServiceImpl(TrainingDataRepository rows) {
        this.rows = rows;
    }

    @Override
    public TrainingData get(Long id) {
        return rows.findById(id)
                .orElseThrow(() -> new NotFoundException("Training row " + id + " not found"));
    }

    @Override
    public List<TrainingData> list(int limit) {
        int safe = Math.min(Math.max(limit, 1), MAX_LIMIT);
        return rows.findAll(PageRequest.of(0, safe)).getContent();
    }

    @Override
    public long count() {
        return rows.count();
    }
}
