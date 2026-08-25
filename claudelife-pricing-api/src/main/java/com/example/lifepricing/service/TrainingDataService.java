package com.example.lifepricing.service;

import com.example.lifepricing.model.TrainingData;
import java.util.List;

public interface TrainingDataService {

    TrainingData get(Long id);

    List<TrainingData> list(int limit);

    long count();
}
