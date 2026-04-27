"""Strict API request and response schemas."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


STRICT_CONFIG = ConfigDict(extra="forbid", strict=True)


class HeartDiseaseRequest(BaseModel):
    """Input schema for a single prediction request."""

    model_config = STRICT_CONFIG

    id: int = Field(0, ge=0, description="Optional patient identifier")
    age: int = Field(..., ge=3650, le=36500, description="Age in days")
    gender: int = Field(..., ge=1, le=2, description="Gender code: 1/2")
    height: int = Field(..., ge=120, le=220, description="Height in centimeters")
    weight: float = Field(..., ge=30, le=220, description="Weight in kilograms")
    ap_hi: int = Field(..., ge=80, le=240, description="Systolic blood pressure")
    ap_lo: int = Field(..., ge=40, le=160, description="Diastolic blood pressure")
    cholesterol: int = Field(..., ge=1, le=3, description="Cholesterol category: 1-3")
    gluc: int = Field(..., ge=1, le=3, description="Glucose category: 1-3")
    smoke: int = Field(..., ge=0, le=1, description="Smoking status: 0/1")
    alco: int = Field(..., ge=0, le=1, description="Alcohol intake flag: 0/1")
    active: int = Field(..., ge=0, le=1, description="Physical activity flag: 0/1")


class BatchHeartDiseaseRequest(BaseModel):
    """Input schema for batch prediction requests."""

    model_config = STRICT_CONFIG

    records: List[HeartDiseaseRequest] = Field(..., min_length=1, max_length=1000)


class PredictionResult(BaseModel):
    """Prediction payload preserved for backward compatibility."""

    model_config = STRICT_CONFIG

    prediction: int
    prob_no_disease: float
    prob_disease: float
    confidence_score: float
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW"]


class StoredPredictionResult(PredictionResult):
    """Prediction result enriched with persistence metadata."""

    prediction_id: str
    subject_id: str
    created_at: datetime


class PredictionResponse(BaseModel):
    """Single prediction response."""

    model_config = STRICT_CONFIG

    request_id: str
    prediction_id: str
    subject_id: str
    model_version: str
    threshold_used: float
    created_at: datetime
    result: PredictionResult


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""

    model_config = STRICT_CONFIG

    request_id: str
    count: int
    model_version: str
    threshold_used: float
    results: List[StoredPredictionResult]


class FeedbackRequest(BaseModel):
    """Attach a reviewed label to a persisted prediction."""

    model_config = STRICT_CONFIG

    prediction_id: str
    true_label: int = Field(..., ge=0, le=1)
    label_source: str = Field("human_review", min_length=3, max_length=50)
    reviewer: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    """Feedback persistence response."""

    model_config = STRICT_CONFIG

    feedback_id: str
    prediction_id: str
    true_label: int
    created_at: datetime
    status: Literal["created", "updated"]


class AnalyticsSummaryItem(BaseModel):
    """Grouped analytics row."""

    model_config = STRICT_CONFIG

    model_version: str
    date_bucket: str
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW"]
    total_predictions: int
    positive_predictions: int
    negative_predictions: int
    average_confidence_score: float
    average_probability: float


class AnalyticsSummaryResponse(BaseModel):
    """Analytics response grouped by model version, date bucket, and confidence tier."""

    model_config = STRICT_CONFIG

    bucket: Literal["hour", "day", "month"]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    model_version: Optional[str] = None
    groups: List[AnalyticsSummaryItem]


class SignupRequest(BaseModel):
    """Input payload for user registration."""

    model_config = STRICT_CONFIG

    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=160)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["student", "patient", "clinical"] = "student"


class LoginRequest(BaseModel):
    """Input payload for user login."""

    model_config = STRICT_CONFIG

    email: str = Field(..., min_length=5, max_length=160)
    password: str = Field(..., min_length=8, max_length=128)


class AuthUserProfile(BaseModel):
    """Authenticated user profile returned to clients."""

    model_config = STRICT_CONFIG

    user_id: str
    full_name: str
    email: str
    role: Literal["student", "patient", "clinical"]
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Signup/login response payload."""

    model_config = STRICT_CONFIG

    message: str
    access_token: str
    token_type: Literal["bearer"]
    user: AuthUserProfile


class RollbackRequest(BaseModel):
    """Rollback request for model registry management."""

    model_config = STRICT_CONFIG

    target_version: Optional[str] = None


class ModelVersionResponse(BaseModel):
    """Active model registry response."""

    model_config = STRICT_CONFIG

    model_version: str
    model_name: str
    is_active: bool
    threshold_used: float
    threshold_objective: str
    created_at: datetime
    activated_at: Optional[datetime] = None
    metrics: Dict[str, Any]


class HealthResponse(BaseModel):
    """Operational readiness response."""

    model_config = STRICT_CONFIG

    status: Literal["ready", "degraded", "loading"]
    db_backend: str
    db_ready: bool
    active_model_version: Optional[str] = None
    startup_warnings: List[str] = Field(default_factory=list)


class ModelStepMetricsItem(BaseModel):
    """Metrics for one trained model step in the ensemble pipeline."""

    model_config = STRICT_CONFIG

    key: str
    name: str
    full_name: str
    is_selected: bool
    threshold: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    fnr: float


class EnsembleTrainingConfig(BaseModel):
    """Subset of BestModelConfig exposed through the API."""

    model_config = STRICT_CONFIG

    calibration_method: str
    random_state: int
    target_recall: float
    target_accuracy: float
    precision_floor: float


class AllModelsMetricsResponse(BaseModel):
    """Full model metrics response for the dashboard."""

    model_config = STRICT_CONFIG

    selected_model: str
    selected_threshold: float
    config: EnsembleTrainingConfig
    models: List[ModelStepMetricsItem]
