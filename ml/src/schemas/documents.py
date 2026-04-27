"""Validated persistence models for MongoDB-backed operational data."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


STRICT_DOC_CONFIG = ConfigDict(extra="forbid", strict=True)


class ProbabilityScores(BaseModel):
    """Class probability scores."""

    model_config = STRICT_DOC_CONFIG

    no_disease: float = Field(..., ge=0.0, le=1.0)
    disease: float = Field(..., ge=0.0, le=1.0)


class RequestMetadata(BaseModel):
    """Normalized request context stored with predictions and logs."""

    model_config = STRICT_DOC_CONFIG

    request_id: str
    route: str
    method: str
    payload_hash: str
    idempotency_key: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    content_length: Optional[int] = None


class SubjectDocument(BaseModel):
    """Pseudonymous subject profile."""

    model_config = STRICT_DOC_CONFIG

    id: str
    external_subject_id: Optional[str] = None
    subject_hash: str
    created_at: datetime
    last_seen_at: datetime


class UserAccountDocument(BaseModel):
    """Persisted user account profile for authentication."""

    model_config = STRICT_DOC_CONFIG

    id: str
    full_name: str
    email: str
    role: Literal["student", "patient", "clinical"]
    password_salt: str
    password_hash: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class PredictionDocument(BaseModel):
    """Persisted prediction event."""

    model_config = STRICT_DOC_CONFIG

    id: str
    request_id: str
    batch_index: int = Field(..., ge=0)
    subject_id: str
    model_version: str
    threshold_used: float = Field(..., ge=0.0, le=1.0)
    prediction_label: int = Field(..., ge=0, le=1)
    probabilities: ProbabilityScores
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW"]
    request_metadata: RequestMetadata
    input_features: Dict[str, Any]
    created_at: datetime
    feedback_label_id: Optional[str] = None


class PerClassMetrics(BaseModel):
    """Per-class metrics for evaluation artifacts."""

    model_config = STRICT_DOC_CONFIG

    precision: float
    recall: float
    f1: float
    support: int


class ThresholdOptimizationSummary(BaseModel):
    """Chosen validation threshold details."""

    model_config = STRICT_DOC_CONFIG

    objective: str
    threshold: float = Field(..., ge=0.0, le=1.0)
    score: float
    evaluated_thresholds: int


class EvaluationSummary(BaseModel):
    """Structured evaluation summary stored with model versions."""

    model_config = STRICT_DOC_CONFIG

    split: str
    accuracy: float
    precision: float
    recall: float
    specificity: float
    f1: float
    roc_auc: float
    pr_auc: float
    balanced_accuracy: float
    mcc: float
    brier: float
    per_class: Dict[str, PerClassMetrics]


class FeatureDistributionStats(BaseModel):
    """Feature distribution summary for drift monitoring."""

    model_config = STRICT_DOC_CONFIG

    feature_type: Literal["numeric", "categorical"]
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    quantiles: Optional[Dict[str, float]] = None
    bin_edges: Optional[List[float]] = None
    bin_distribution: Optional[Dict[str, float]] = None
    category_distribution: Optional[Dict[str, float]] = None
    psi_vs_baseline: Optional[float] = None


class PredictionDistributionStats(BaseModel):
    """Prediction distribution summary for drift monitoring."""

    model_config = STRICT_DOC_CONFIG

    positive_rate: float
    mean_probability: float
    std_probability: float
    mean_confidence: float
    tier_distribution: Dict[str, float]
    label_distribution: Dict[str, float]


class DriftAlert(BaseModel):
    """Alert flag generated during drift analysis."""

    model_config = STRICT_DOC_CONFIG

    name: str
    triggered: bool
    observed_value: float
    threshold: float
    message: str


class DriftMonitoringSnapshotDocument(BaseModel):
    """Persisted drift monitoring snapshot."""

    model_config = STRICT_DOC_CONFIG

    id: str
    model_version: str
    source: Literal["training_baseline", "inference_request"]
    request_id: Optional[str] = None
    sample_size: int = Field(..., ge=1)
    feature_stats: Dict[str, FeatureDistributionStats]
    prediction_distribution: PredictionDistributionStats
    alerts: List[DriftAlert]
    reference_snapshot_id: Optional[str] = None
    created_at: datetime


class ModelVersionDocument(BaseModel):
    """Registered model metadata for serving and rollback."""

    model_config = STRICT_DOC_CONFIG

    id: str
    model_name: str
    artifact_path: str
    preprocessing_path: str
    artifact_sha256: Optional[str] = None
    preprocessing_sha256: Optional[str] = None
    threshold_used: float = Field(..., ge=0.0, le=1.0)
    threshold_objective: str
    threshold_summary: ThresholdOptimizationSummary
    validation_metrics: EvaluationSummary
    test_metrics: EvaluationSummary
    class_balance: Dict[str, float]
    feature_names: List[str]
    training_parameters: Dict[str, Any]
    baseline_snapshot_id: Optional[str] = None
    metrics_path: Optional[str] = None
    is_active: bool = False
    created_at: datetime
    activated_at: Optional[datetime] = None
    notes: Optional[str] = None


class FeedbackLabelDocument(BaseModel):
    """Reviewed label attached to a prediction."""

    model_config = STRICT_DOC_CONFIG

    id: str
    prediction_id: str
    true_label: int = Field(..., ge=0, le=1)
    label_source: str
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    request_metadata: RequestMetadata
    created_at: datetime


class APIRequestLogDocument(BaseModel):
    """Request/response audit log."""

    model_config = STRICT_DOC_CONFIG

    id: str
    request_metadata: RequestMetadata
    status: Literal["PENDING", "COMPLETED", "FAILED"]
    status_code: Optional[int] = None
    latency_ms: Optional[float] = Field(default=None, ge=0.0)
    model_version: Optional[str] = None
    prediction_ids: List[str] = Field(default_factory=list)
    response_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
