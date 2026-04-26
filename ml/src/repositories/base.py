"""Repository interfaces for operational persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from src.schemas.documents import (
    APIRequestLogDocument,
    DriftMonitoringSnapshotDocument,
    FeedbackLabelDocument,
    ModelVersionDocument,
    PredictionDocument,
    SubjectDocument,
    UserAccountDocument,
)


@dataclass(frozen=True)
class RequestLogReservation:
    """Reservation outcome for an idempotent request."""

    document: APIRequestLogDocument
    is_replay: bool = False


@dataclass(frozen=True)
class PredictionAnalyticsRecord:
    """Aggregated prediction analytics row."""

    model_version: str
    date_bucket: str
    confidence_tier: str
    total_predictions: int
    positive_predictions: int
    negative_predictions: int
    average_confidence_score: float
    average_probability: float


class SubjectRepository(ABC):
    @abstractmethod
    async def get_by_subject_hash(self, subject_hash: str) -> SubjectDocument | None:
        """Return a subject by its pseudonymous hash."""

    @abstractmethod
    async def upsert(self, document: SubjectDocument) -> SubjectDocument:
        """Create or replace a subject."""


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> UserAccountDocument | None:
        """Return a user by normalized email."""

    @abstractmethod
    async def create(self, document: UserAccountDocument) -> UserAccountDocument:
        """Persist a new user account."""

    @abstractmethod
    async def update_last_login(self, user_id: str, last_login_at: datetime) -> UserAccountDocument:
        """Update and return the user's last login timestamp."""


class PredictionRepository(ABC):
    @abstractmethod
    async def upsert_batch(self, documents: list[PredictionDocument]) -> list[PredictionDocument]:
        """Persist a deterministic batch of prediction events."""

    @abstractmethod
    async def get_by_id(self, prediction_id: str) -> PredictionDocument | None:
        """Return a prediction by id."""

    @abstractmethod
    async def attach_feedback(self, prediction_id: str, feedback_label_id: str) -> None:
        """Attach a feedback label reference to a prediction."""

    @abstractmethod
    async def summarize(
        self,
        *,
        bucket: Literal["hour", "day", "month"],
        start_date: datetime | None,
        end_date: datetime | None,
        model_version: str | None,
    ) -> list[PredictionAnalyticsRecord]:
        """Return grouped analytics for prediction history."""


class ModelVersionRepository(ABC):
    @abstractmethod
    async def create(self, document: ModelVersionDocument) -> ModelVersionDocument:
        """Persist a model version."""

    @abstractmethod
    async def get_by_id(self, version_id: str) -> ModelVersionDocument | None:
        """Return a model version by id."""

    @abstractmethod
    async def get_active(self) -> ModelVersionDocument | None:
        """Return the active model version."""

    @abstractmethod
    async def list_versions(self) -> list[ModelVersionDocument]:
        """Return model versions ordered by recency."""

    @abstractmethod
    async def activate(self, version_id: str, activated_at: datetime) -> ModelVersionDocument:
        """Mark a model version as active and deactivate others."""

    @abstractmethod
    async def get_previous_active(self, current_version_id: str) -> ModelVersionDocument | None:
        """Return the previous model version eligible for rollback."""


class FeedbackRepository(ABC):
    @abstractmethod
    async def get_by_prediction_id(self, prediction_id: str) -> FeedbackLabelDocument | None:
        """Return feedback for a prediction."""

    @abstractmethod
    async def upsert(self, document: FeedbackLabelDocument) -> tuple[FeedbackLabelDocument, str]:
        """Create or replace feedback for a prediction and return status."""


class DriftSnapshotRepository(ABC):
    @abstractmethod
    async def upsert(
        self,
        document: DriftMonitoringSnapshotDocument,
    ) -> DriftMonitoringSnapshotDocument:
        """Create or replace a drift snapshot."""

    @abstractmethod
    async def get_by_id(self, snapshot_id: str) -> DriftMonitoringSnapshotDocument | None:
        """Return a drift snapshot by id."""

    @abstractmethod
    async def get_baseline_for_model(
        self,
        model_version: str,
    ) -> DriftMonitoringSnapshotDocument | None:
        """Return the baseline drift snapshot for a model version."""


class APIRequestLogRepository(ABC):
    @abstractmethod
    async def reserve(self, document: APIRequestLogDocument) -> RequestLogReservation:
        """Reserve request execution or replay an existing completed response."""

    @abstractmethod
    async def complete(
        self,
        request_log_id: str,
        *,
        status_code: int,
        latency_ms: float,
        model_version: str | None,
        prediction_ids: list[str],
        response_payload: dict[str, Any] | None,
    ) -> APIRequestLogDocument:
        """Finalize a successful request log."""

    @abstractmethod
    async def fail(
        self,
        request_log_id: str,
        *,
        status_code: int,
        latency_ms: float,
        error_message: str,
    ) -> APIRequestLogDocument:
        """Finalize a failed request log."""

    @abstractmethod
    async def get_by_id(self, request_log_id: str) -> APIRequestLogDocument | None:
        """Return an API request log entry."""

    @abstractmethod
    async def get_by_route_and_idempotency(
        self,
        route: str,
        idempotency_key: str,
    ) -> APIRequestLogDocument | None:
        """Return a previously logged request by route and idempotency key."""


@dataclass
class RepositoryBundle:
    """Aggregated repositories used by the application."""

    backend_name: str
    subjects: SubjectRepository
    users: UserRepository
    predictions: PredictionRepository
    model_versions: ModelVersionRepository
    feedback_labels: FeedbackRepository
    drift_snapshots: DriftSnapshotRepository
    api_request_logs: APIRequestLogRepository
    startup_warnings: list[str] = field(default_factory=list)

    async def initialize(self) -> None:
        """Initialize underlying resources when needed."""

    async def ping(self) -> bool:
        """Return whether the repository backend is reachable."""
        return True

    async def close(self) -> None:
        """Close underlying resources when needed."""
