"""In-memory repository implementation for tests and local fallback."""

from collections import defaultdict
from datetime import datetime
from typing import Literal

from src.core.exceptions import NotFoundError
from src.repositories.base import (
    APIRequestLogRepository,
    DriftSnapshotRepository,
    FeedbackRepository,
    ModelVersionRepository,
    PredictionAnalyticsRecord,
    PredictionRepository,
    RepositoryBundle,
    RequestLogReservation,
    SubjectRepository,
    UserRepository,
)
from src.schemas.documents import (
    APIRequestLogDocument,
    DriftMonitoringSnapshotDocument,
    FeedbackLabelDocument,
    ModelVersionDocument,
    PredictionDocument,
    SubjectDocument,
    UserAccountDocument,
)


def _bucket_value(timestamp: datetime, bucket: Literal["hour", "day", "month"]) -> str:
    if bucket == "hour":
        return timestamp.strftime("%Y-%m-%dT%H:00:00Z")
    if bucket == "month":
        return timestamp.strftime("%Y-%m-01")
    return timestamp.strftime("%Y-%m-%d")


class InMemorySubjectRepository(SubjectRepository):
    def __init__(self):
        self._by_id: dict[str, SubjectDocument] = {}
        self._by_hash: dict[str, str] = {}

    async def get_by_subject_hash(self, subject_hash: str) -> SubjectDocument | None:
        subject_id = self._by_hash.get(subject_hash)
        return self._by_id.get(subject_id) if subject_id else None

    async def upsert(self, document: SubjectDocument) -> SubjectDocument:
        self._by_id[document.id] = document
        self._by_hash[document.subject_hash] = document.id
        return document


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self._by_id: dict[str, UserAccountDocument] = {}
        self._by_email: dict[str, str] = {}

    async def get_by_email(self, email: str) -> UserAccountDocument | None:
        user_id = self._by_email.get(email)
        return self._by_id.get(user_id) if user_id else None

    async def create(self, document: UserAccountDocument) -> UserAccountDocument:
        self._by_id[document.id] = document
        self._by_email[document.email] = document.id
        return document

    async def update_last_login(self, user_id: str, last_login_at) -> UserAccountDocument:
        existing = self._by_id.get(user_id)
        if existing is None:
            raise NotFoundError(f"User '{user_id}' was not found.")
        updated = existing.model_copy(update={"last_login_at": last_login_at})
        self._by_id[user_id] = updated
        return updated


class InMemoryPredictionRepository(PredictionRepository):
    def __init__(self):
        self._items: dict[str, PredictionDocument] = {}

    async def upsert_batch(self, documents: list[PredictionDocument]) -> list[PredictionDocument]:
        for document in documents:
            self._items[document.id] = document
        return documents

    async def get_by_id(self, prediction_id: str) -> PredictionDocument | None:
        return self._items.get(prediction_id)

    async def attach_feedback(self, prediction_id: str, feedback_label_id: str) -> None:
        existing = self._items.get(prediction_id)
        if existing is None:
            raise NotFoundError(f"Prediction '{prediction_id}' was not found.")
        self._items[prediction_id] = existing.model_copy(
            update={"feedback_label_id": feedback_label_id}
        )

    async def summarize(
        self,
        *,
        bucket: Literal["hour", "day", "month"],
        start_date: datetime | None,
        end_date: datetime | None,
        model_version: str | None,
    ) -> list[PredictionAnalyticsRecord]:
        grouped: dict[tuple[str, str, str], list[PredictionDocument]] = defaultdict(list)
        for document in self._items.values():
            if model_version and document.model_version != model_version:
                continue
            if start_date and document.created_at < start_date:
                continue
            if end_date and document.created_at >= end_date:
                continue
            key = (
                document.model_version,
                _bucket_value(document.created_at, bucket),
                document.confidence_tier,
            )
            grouped[key].append(document)

        results: list[PredictionAnalyticsRecord] = []
        for key in sorted(grouped):
            rows = grouped[key]
            positive_predictions = sum(item.prediction_label for item in rows)
            total_predictions = len(rows)
            results.append(
                PredictionAnalyticsRecord(
                    model_version=key[0],
                    date_bucket=key[1],
                    confidence_tier=key[2],
                    total_predictions=total_predictions,
                    positive_predictions=positive_predictions,
                    negative_predictions=total_predictions - positive_predictions,
                    average_confidence_score=sum(item.confidence_score for item in rows)
                    / total_predictions,
                    average_probability=sum(item.probabilities.disease for item in rows)
                    / total_predictions,
                )
            )
        return results


class InMemoryModelVersionRepository(ModelVersionRepository):
    def __init__(self):
        self._items: dict[str, ModelVersionDocument] = {}

    async def create(self, document: ModelVersionDocument) -> ModelVersionDocument:
        self._items[document.id] = document
        return document

    async def get_by_id(self, version_id: str) -> ModelVersionDocument | None:
        return self._items.get(version_id)

    async def get_active(self) -> ModelVersionDocument | None:
        active = [doc for doc in self._items.values() if doc.is_active]
        if not active:
            return None
        active.sort(key=lambda doc: doc.activated_at or doc.created_at, reverse=True)
        return active[0]

    async def list_versions(self) -> list[ModelVersionDocument]:
        return sorted(
            self._items.values(),
            key=lambda doc: doc.activated_at or doc.created_at,
            reverse=True,
        )

    async def activate(self, version_id: str, activated_at) -> ModelVersionDocument:
        target = self._items.get(version_id)
        if target is None:
            raise NotFoundError(f"Model version '{version_id}' was not found.")
        for doc_id, doc in list(self._items.items()):
            self._items[doc_id] = doc.model_copy(
                update={"is_active": doc_id == version_id}
            )
        target = self._items[version_id].model_copy(
            update={"is_active": True, "activated_at": activated_at}
        )
        self._items[version_id] = target
        return target

    async def get_previous_active(self, current_version_id: str) -> ModelVersionDocument | None:
        versions = [doc for doc in await self.list_versions() if doc.id != current_version_id]
        return versions[0] if versions else None


class InMemoryFeedbackRepository(FeedbackRepository):
    def __init__(self):
        self._items: dict[str, FeedbackLabelDocument] = {}
        self._by_prediction: dict[str, str] = {}

    async def get_by_prediction_id(self, prediction_id: str) -> FeedbackLabelDocument | None:
        feedback_id = self._by_prediction.get(prediction_id)
        return self._items.get(feedback_id) if feedback_id else None

    async def upsert(self, document: FeedbackLabelDocument) -> tuple[FeedbackLabelDocument, str]:
        existing = await self.get_by_prediction_id(document.prediction_id)
        status = "created"
        if existing is not None:
            document = document.model_copy(
                update={"id": existing.id, "created_at": existing.created_at}
            )
            status = "updated"
        self._items[document.id] = document
        self._by_prediction[document.prediction_id] = document.id
        return document, status


class InMemoryDriftSnapshotRepository(DriftSnapshotRepository):
    def __init__(self):
        self._items: dict[str, DriftMonitoringSnapshotDocument] = {}

    async def upsert(
        self,
        document: DriftMonitoringSnapshotDocument,
    ) -> DriftMonitoringSnapshotDocument:
        self._items[document.id] = document
        return document

    async def get_by_id(self, snapshot_id: str) -> DriftMonitoringSnapshotDocument | None:
        return self._items.get(snapshot_id)

    async def get_baseline_for_model(
        self,
        model_version: str,
    ) -> DriftMonitoringSnapshotDocument | None:
        snapshots = [
            doc
            for doc in self._items.values()
            if doc.model_version == model_version and doc.source == "training_baseline"
        ]
        snapshots.sort(key=lambda doc: doc.created_at, reverse=True)
        return snapshots[0] if snapshots else None


class InMemoryAPIRequestLogRepository(APIRequestLogRepository):
    def __init__(self):
        self._items: dict[str, APIRequestLogDocument] = {}
        self._by_idempotency: dict[tuple[str, str], str] = {}

    async def reserve(self, document: APIRequestLogDocument) -> RequestLogReservation:
        request_log = self._items.get(document.id)
        if request_log is None and document.request_metadata.idempotency_key:
            route_key = (
                document.request_metadata.route,
                document.request_metadata.idempotency_key,
            )
            existing_id = self._by_idempotency.get(route_key)
            if existing_id:
                request_log = self._items.get(existing_id)

        if request_log is None:
            self._items[document.id] = document
            if document.request_metadata.idempotency_key:
                self._by_idempotency[
                    (
                        document.request_metadata.route,
                        document.request_metadata.idempotency_key,
                    )
                ] = document.id
            return RequestLogReservation(document=document, is_replay=False)

        if request_log.request_metadata.payload_hash != document.request_metadata.payload_hash:
            return RequestLogReservation(document=request_log, is_replay=False)

        if request_log.status == "COMPLETED" and request_log.response_payload is not None:
            return RequestLogReservation(document=request_log, is_replay=True)

        updated = request_log.model_copy(
            update={
                "status": "PENDING",
                "status_code": None,
                "latency_ms": None,
                "model_version": None,
                "prediction_ids": [],
                "response_payload": None,
                "error_message": None,
                "updated_at": document.updated_at,
                "completed_at": None,
                "request_metadata": document.request_metadata,
            }
        )
        self._items[request_log.id] = updated
        return RequestLogReservation(document=updated, is_replay=False)

    async def complete(
        self,
        request_log_id: str,
        *,
        status_code: int,
        latency_ms: float,
        model_version: str | None,
        prediction_ids: list[str],
        response_payload: dict | None,
    ) -> APIRequestLogDocument:
        request_log = self._items.get(request_log_id)
        if request_log is None:
            raise NotFoundError(f"Request log '{request_log_id}' was not found.")
        updated = request_log.model_copy(
            update={
                "status": "COMPLETED",
                "status_code": status_code,
                "latency_ms": latency_ms,
                "model_version": model_version,
                "prediction_ids": prediction_ids,
                "response_payload": response_payload,
                "error_message": None,
                "updated_at": request_log.updated_at,
                "completed_at": request_log.updated_at,
            }
        )
        self._items[request_log_id] = updated
        return updated

    async def fail(
        self,
        request_log_id: str,
        *,
        status_code: int,
        latency_ms: float,
        error_message: str,
    ) -> APIRequestLogDocument:
        request_log = self._items.get(request_log_id)
        if request_log is None:
            raise NotFoundError(f"Request log '{request_log_id}' was not found.")
        updated = request_log.model_copy(
            update={
                "status": "FAILED",
                "status_code": status_code,
                "latency_ms": latency_ms,
                "model_version": None,
                "prediction_ids": [],
                "response_payload": None,
                "error_message": error_message,
                "updated_at": request_log.updated_at,
                "completed_at": request_log.updated_at,
            }
        )
        self._items[request_log_id] = updated
        return updated

    async def get_by_id(self, request_log_id: str) -> APIRequestLogDocument | None:
        return self._items.get(request_log_id)

    async def get_by_route_and_idempotency(
        self,
        route: str,
        idempotency_key: str,
    ) -> APIRequestLogDocument | None:
        request_log_id = self._by_idempotency.get((route, idempotency_key))
        return self._items.get(request_log_id) if request_log_id else None


def build_inmemory_repository_bundle() -> RepositoryBundle:
    """Return an in-memory repository bundle."""
    return RepositoryBundle(
        backend_name="inmemory",
        subjects=InMemorySubjectRepository(),
        users=InMemoryUserRepository(),
        predictions=InMemoryPredictionRepository(),
        model_versions=InMemoryModelVersionRepository(),
        feedback_labels=InMemoryFeedbackRepository(),
        drift_snapshots=InMemoryDriftSnapshotRepository(),
        api_request_logs=InMemoryAPIRequestLogRepository(),
    )
