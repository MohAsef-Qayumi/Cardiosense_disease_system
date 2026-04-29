# CardioSense Production Upgrade Plan

## Folder-level changes

```
heart-disease-inference/
|- api.py
|- .env.example
|- docs/
|  |- architecture_plan.md
|  \- runbook.md
|- src/
|  |- core/
|  |  |- settings.py
|  |  |- logging_utils.py
|  |  |- exceptions.py
|  |  \- utils.py
|  |- schemas/
|  |  |- api.py
|  |  \- documents.py
|  |- repositories/
|  |  |- base.py
|  |  |- inmemory.py
|  |  \- mongodb.py
|  |- services/
|  |  |- container.py
|  |  |- model_registry.py
|  |  |- prediction_service.py
|  |  \- drift.py
|  \- existing ML modules...
|- tests/
|  |- test_api.py
|  |- test_prediction_service.py
|  |- test_mongo_repositories.py
|  \- existing ML tests...
```

## Collection strategy

`pseudonymous_subjects`
- `_id`: `subject_<uuid>`
- `external_subject_id`
- `subject_hash`
- `created_at`
- `last_seen_at`

`predictions`
- `_id`: `prediction_<uuid>`
- `subject_id`
- `model_version`
- `threshold_used`
- `prediction`
- `probabilities`
- `confidence_score`
- `confidence_tier`
- `request_metadata`
- `input_features`
- `created_at`
- `feedback_label_id`

`model_versions`
- `_id`: `model_<uuid>`
- `model_name`
- `artifact_path`
- `preprocessing_path`
- `artifact_sha256`
- `preprocessing_sha256`
- `threshold_used`
- `threshold_objective`
- `threshold_summary`
- `validation_metrics`
- `test_metrics`
- `class_balance`
- `feature_names`
- `training_parameters`
- `baseline_snapshot_id`
- `metrics_path`
- `is_active`
- `created_at`
- `activated_at`
- `notes`

`feedback_labels`
- `_id`: `feedback_<uuid>`
- `prediction_id`
- `true_label`
- `label_source`
- `reviewer`
- `notes`
- `request_metadata`
- `created_at`

`drift_monitoring_snapshots`
- `_id`: `drift_<uuid>`
- `model_version`
- `source`
- `sample_size`
- `feature_stats`
- `prediction_distribution`
- `alerts`
- `reference_snapshot_id`
- `created_at`

`api_request_logs`
- `_id`: request id
- `request_metadata`
- `status_code`
- `latency_ms`
- `model_version`
- `prediction_ids`
- `response_payload`
- `error_message`
- `created_at`

## Serving design

- `api.py` is now a thin transport layer with strict schemas, request IDs, and error handlers.
- `PredictionService` owns prediction persistence, subject upserts, drift snapshots, feedback handling, and idempotency behavior.
- `ModelRegistryService` loads the active model version from the repository, supports rollback, and can bootstrap from local artifacts during migration.
- `DriftMonitoringService` stores training baselines and inference snapshots, including feature PSI and prediction-rate shift alerts.
- Repository implementations are split between `mongodb` for production and `inmemory` for tests and local validation.

## Migration path

- Existing `/predict` and `/predict/batch` routes are preserved.
- Response bodies are backward-compatible around `result` and `results` while adding metadata such as `prediction_id`, `model_version`, and `threshold_used`.
- Existing local artifact serving still works through registry bootstrap while MongoDB is being initialized.
