# AI Training & Fine-Tuning Architecture

This directory defines the lifecycle and dataset schemas for training, fine-tuning, and evaluating specialized AI models for **AI Opportunity Assistant**.

## Lifecycle Pipeline

```text
Raw Datasets & Feedback
          ↓
     Data Cleaning
          ↓
      Annotation
          ↓
  Task-Specific Split
          ↓
Training / Fine-Tuning
          ↓
      Validation
          ↓
Grounding & Accuracy Eval
          ↓
 Model Registry & Deploy
          ↓
 Production Monitoring
```

## Structure
- `datasets/`: Schemas and dataset definitions (JSONL format) for query intent, extraction, eligibility, and ranking.
- `pipelines/`: Pipeline specifications for cleaning, synthetic generation, validation, and benchmarking.
