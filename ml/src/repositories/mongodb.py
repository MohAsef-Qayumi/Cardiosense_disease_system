"""Async MongoDB repository implementation for CardioSense."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import quote_plus

from src.core.exceptions import (
    ConfigurationError,
    DependencyUnavailableError,
    NotFoundError,
    PersistenceError,
)
from src.core.logging_utils import get_logger
from src.core.settings import Settings
from src.core.utils import utc_now
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

try:
    from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel, ReplaceOne
    from pymongo.errors import ConnectionFailure, DuplicateKeyError, OperationFailure, PyMongoError
except Exception:  # pragma: no cover - exercised indirectly when dependency is absent
    class ConnectionFailure(Exception):
        """Fallback connection failure used in tests when pymongo is absent."""

    class DuplicateKeyError(Exception):
        """Fallback duplicate key error used in tests when pymongo is absent."""

    class OperationFailure(Exception):
        """Fallback operation failure used in tests when pymongo is absent."""

    class PyMongoError(Exception):
        """Fallback base mongo error used in tests when pymongo is absent."""

    class IndexModel:  # type: ignore[override]
        def __init__(self, keys, **kwargs):
            self.keys = keys
            self.document = {"key": keys, **kwargs}

    class ReplaceOne:  # type: ignore[override]
        def __init__(self, filter, replacement, upsert=False):
            self._filter = filter
            self._replacement = replacement
            self._upsert = upsert

    ASCENDING = 1
    DESCENDING = -1
    AsyncMongoClient = None

LOGGER = get_logger(__name__)

COLLECTION_SUBJECTS = "pseudonymous_subjects"
COLLECTION_USERS = "users"
COLLECTION_PREDICTIONS = "prediction_records"
COLLECTION_MODEL_REGISTRY = "model_registry"
COLLECTION_FEEDBACK = "feedback_ground_truth"
COLLECTION_DRIFT = "drift_reports"
COLLECTION_REQUEST_LOGS = "request_logs"


def _resolve_mongodb_uri(settings: Settings) -> str:
    uri = settings.mongodb_uri
    placeholder = "<db_password>"
    if placeholder not in uri:
        return uri
    if not settings.mongodb_password:
        raise ConfigurationError(
            "CARDIOSENSE_MONGODB_URI contains <db_password>. "
            "Set CARDIOSENSE_MONGODB_PASSWORD to continue."
        )
    return uri.replace(placeholder, quote_plus(settings.mongodb_password))


def _serialize(document) -> dict[str, Any]:
    data = document.model_dump(mode="python")
    data["_id"] = data.pop("id")
    return data


def _inflate(model_cls, data: dict[str, Any] | None):
    if data is None:
        return None
    payload = dict(data)
    payload["id"] = str(payload.pop("_id"))
    return model_cls.model_validate(payload)


def _request_metadata_validator() -> dict[str, Any]:
    return {
        "bsonType": "object",
        "required": ["request_id", "route", "method", "payload_hash"],
        "properties": {
            "request_id": {"bsonType": "string"},
            "route": {"bsonType": "string"},
            "method": {"bsonType": "string"},
            "payload_hash": {"bsonType": "string"},
            "idempotency_key": {"bsonType": ["string", "null"]},
            "client_ip": {"bsonType": ["string", "null"]},
            "user_agent": {"bsonType": ["string", "null"]},
            "content_length": {"bsonType": ["int", "long", "null"]},
        },
    }


def _json_schema(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {"$jsonSchema": {"bsonType": "object", "required": required, "properties": properties}}


def _collection_validators() -> dict[str, dict[str, Any]]:
    return {
        COLLECTION_SUBJECTS: _json_schema(
            ["_id", "subject_hash", "created_at", "last_seen_at"],
            {
                "_id": {"bsonType": "string"},
                "external_subject_id": {"bsonType": ["string", "null"]},
                "subject_hash": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
                "last_seen_at": {"bsonType": "date"},
            },
        ),
        COLLECTION_USERS: _json_schema(
            ["_id", "full_name", "email", "role", "password_salt", "password_hash", "created_at"],
            {
                "_id": {"bsonType": "string"},
                "full_name": {"bsonType": "string"},
                "email": {"bsonType": "string"},
                "role": {"enum": ["student", "patient", "clinical"]},
                "password_salt": {"bsonType": "string"},
                "password_hash": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
                "last_login_at": {"bsonType": ["date", "null"]},
            },
        ),
        COLLECTION_PREDICTIONS: _json_schema(
            [
                "_id",
                "request_id",
                "batch_index",
                "subject_id",
                "model_version",
                "threshold_used",
                "prediction_label",
                "confidence_score",
                "confidence_tier",
                "request_metadata",
                "input_features",
                "created_at",
            ],
            {
                "_id": {"bsonType": "string"},
                "request_id": {"bsonType": "string"},
                "batch_index": {"bsonType": ["int", "long"]},
                "subject_id": {"bsonType": "string"},
                "model_version": {"bsonType": "string"},
                "threshold_used": {"bsonType": ["double", "int", "long"]},
                "prediction_label": {"bsonType": ["int", "long"]},
                "probabilities": {"bsonType": "object"},
                "confidence_score": {"bsonType": ["double", "int", "long"]},
                "confidence_tier": {"enum": ["HIGH", "MEDIUM", "LOW"]},
                "request_metadata": _request_metadata_validator(),
                "input_features": {"bsonType": "object"},
                "created_at": {"bsonType": "date"},
                "feedback_label_id": {"bsonType": ["string", "null"]},
            },
        ),
        COLLECTION_MODEL_REGISTRY: _json_schema(
            [
                "_id",
                "model_name",
                "artifact_path",
                "preprocessing_path",
                "threshold_used",
                "threshold_objective",
                "threshold_summary",
                "validation_metrics",
                "test_metrics",
                "class_balance",
                "feature_names",
                "training_parameters",
                "is_active",
                "created_at",
            ],
            {
                "_id": {"bsonType": "string"},
                "model_name": {"bsonType": "string"},
                "artifact_path": {"bsonType": "string"},
                "preprocessing_path": {"bsonType": "string"},
                "artifact_sha256": {"bsonType": ["string", "null"]},
                "preprocessing_sha256": {"bsonType": ["string", "null"]},
                "threshold_used": {"bsonType": ["double", "int", "long"]},
                "threshold_objective": {"bsonType": "string"},
                "threshold_summary": {"bsonType": "object"},
                "validation_metrics": {"bsonType": "object"},
                "test_metrics": {"bsonType": "object"},
                "class_balance": {"bsonType": "object"},
                "feature_names": {"bsonType": "array"},
                "training_parameters": {"bsonType": "object"},
                "baseline_snapshot_id": {"bsonType": ["string", "null"]},
                "metrics_path": {"bsonType": ["string", "null"]},
                "is_active": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
                "activated_at": {"bsonType": ["date", "null"]},
                "notes": {"bsonType": ["string", "null"]},
            },
        ),
        COLLECTION_FEEDBACK: _json_schema(
            [
                "_id",
                "prediction_id",
                "true_label",
                "label_source",
                "request_metadata",
                "created_at",
            ],
            {
                "_id": {"bsonType": "string"},
                "prediction_id": {"bsonType": "string"},
                "true_label": {"bsonType": ["int", "long"]},
                "label_source": {"bsonType": "string"},
                "reviewer": {"bsonType": ["string", "null"]},
                "notes": {"bsonType": ["string", "null"]},
                "request_metadata": _request_metadata_validator(),
                "created_at": {"bsonType": "date"},
            },
        ),
        COLLECTION_DRIFT: _json_schema(
            [
                "_id",
                "model_version",
                "source",
                "sample_size",
                "feature_stats",
                "prediction_distribution",
                "alerts",
                "created_at",
            ],
            {
                "_id": {"bsonType": "string"},
                "model_version": {"bsonType": "string"},
                "source": {"enum": ["training_baseline", "inference_request"]},
                "request_id": {"bsonType": ["string", "null"]},
                "sample_size": {"bsonType": ["int", "long"]},
                "feature_stats": {"bsonType": "object"},
                "prediction_distribution": {"bsonType": "object"},
                "alerts": {"bsonType": "array"},
                "reference_snapshot_id": {"bsonType": ["string", "null"]},
                "created_at": {"bsonType": "date"},
            },
        ),
        COLLECTION_REQUEST_LOGS: _json_schema(
            ["_id", "request_metadata", "status", "created_at", "updated_at"],
            {
                "_id": {"bsonType": "string"},
                "request_metadata": _request_metadata_validator(),
                "status": {"enum": ["PENDING", "COMPLETED", "FAILED"]},
                "status_code": {"bsonType": ["int", "long", "null"]},
                "latency_ms": {"bsonType": ["double", "int", "long", "null"]},
                "model_version": {"bsonType": ["string", "null"]},
                "prediction_ids": {"bsonType": "array"},
                "response_payload": {"bsonType": ["object", "null"]},
                "error_message": {"bsonType": ["string", "null"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "completed_at": {"bsonType": ["date", "null"]},
            },
        ),
    }


def _collection_indexes() -> dict[str, list[IndexModel]]:
    return {
        COLLECTION_SUBJECTS: [
            IndexModel([("subject_hash", ASCENDING)], name="uq_subject_hash", unique=True),
            IndexModel([("created_at", DESCENDING)], name="ix_subject_created_at"),
        ],
        COLLECTION_USERS: [
            IndexModel([("email", ASCENDING)], name="uq_user_email", unique=True),
            IndexModel([("created_at", DESCENDING)], name="ix_user_created_at"),
        ],
        COLLECTION_PREDICTIONS: [
            IndexModel([("created_at", DESCENDING)], name="ix_predictions_created_at"),
            IndexModel([("model_version", ASCENDING)], name="ix_predictions_model_version"),
            IndexModel([("prediction_label", ASCENDING)], name="ix_predictions_prediction_label"),
            IndexModel([("confidence_tier", ASCENDING)], name="ix_predictions_confidence_tier"),
            IndexModel([("request_id", ASCENDING)], name="ix_predictions_request_id"),
            IndexModel(
                [("request_id", ASCENDING), ("batch_index", ASCENDING)],
                name="uq_predictions_request_batch",
                unique=True,
            ),
        ],
        COLLECTION_MODEL_REGISTRY: [
            IndexModel([("created_at", DESCENDING)], name="ix_model_registry_created_at"),
            IndexModel(
                [("is_active", ASCENDING), ("activated_at", DESCENDING)],
                name="ix_model_registry_active",
            ),
        ],
        COLLECTION_FEEDBACK: [
            IndexModel([("created_at", DESCENDING)], name="ix_feedback_created_at"),
            IndexModel([("prediction_id", ASCENDING)], name="uq_feedback_prediction", unique=True),
        ],
        COLLECTION_DRIFT: [
            IndexModel([("created_at", DESCENDING)], name="ix_drift_created_at"),
            IndexModel(
                [("model_version", ASCENDING), ("created_at", DESCENDING)],
                name="ix_drift_model_version_created_at",
            ),
            IndexModel([("request_id", ASCENDING)], name="ix_drift_request_id", sparse=True),
        ],
        COLLECTION_REQUEST_LOGS: [
            IndexModel([("created_at", DESCENDING)], name="ix_request_logs_created_at"),
            IndexModel(
                [("request_metadata.request_id", ASCENDING)],
                name="uq_request_logs_request_id",
                unique=True,
            ),
            # Partial index: only enforces uniqueness when idempotency_key is explicitly set.
            # A sparse compound index in MongoDB includes docs where ANY indexed field is
            # non-null, which would incorrectly conflict on plain null idempotency keys.
            IndexModel(
                [
                    ("request_metadata.route", ASCENDING),
                    ("request_metadata.idempotency_key", ASCENDING),
                ],
                name="uq_request_logs_route_idempotency",
                unique=True,
                partialFilterExpression={
                    "request_metadata.idempotency_key": {"$type": "string"},
                },
            ),
        ],
    }


def _date_bucket_expression(bucket: Literal["hour", "day", "month"]) -> dict[str, Any]:
    formats = {
        "hour": "%Y-%m-%dT%H:00:00Z",
        "day": "%Y-%m-%d",
        "month": "%Y-%m-01",
    }
    return {"$dateToString": {"format": formats[bucket], "date": "$created_at", "timezone": "UTC"}}


def _normalize_index_key(index_key: Any) -> tuple[tuple[str, Any], ...]:
    """Return a comparable, ordered key signature for index definitions."""

    items = index_key.items() if hasattr(index_key, "items") else index_key
    normalized: list[tuple[str, Any]] = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        field_name, direction = item
        try:
            direction_value: Any = int(direction)
        except Exception:
            direction_value = str(direction)
        normalized.append((str(field_name), direction_value))
    return tuple(normalized)


class BaseMongoRepository:
    """Common helpers for MongoDB repositories."""

    def __init__(self, collection: Any):
        self.collection = collection

    async def _replace_by_id(self, document) -> None:
        payload = _serialize(document)
        await self.collection.replace_one({"_id": payload["_id"]}, payload, upsert=True)


class MongoSubjectRepository(BaseMongoRepository, SubjectRepository):
    async def get_by_subject_hash(self, subject_hash: str) -> SubjectDocument | None:
        return _inflate(
            SubjectDocument,
            await self.collection.find_one({"subject_hash": subject_hash}),
        )

    async def upsert(self, document: SubjectDocument) -> SubjectDocument:
        await self._replace_by_id(document)
        return document


class MongoUserRepository(BaseMongoRepository, UserRepository):
    async def get_by_email(self, email: str) -> UserAccountDocument | None:
        return _inflate(UserAccountDocument, await self.collection.find_one({"email": email}))

    async def create(self, document: UserAccountDocument) -> UserAccountDocument:
        try:
            await self.collection.insert_one(_serialize(document))
        except Exception as exc:  # pragma: no cover - depends on driver/runtime
            raise PersistenceError(f"Could not persist user '{document.email}': {exc}") from exc
        return document

    async def update_last_login(self, user_id: str, last_login_at) -> UserAccountDocument:
        result = await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"last_login_at": last_login_at}},
        )
        if result.matched_count == 0:
            raise NotFoundError(f"User '{user_id}' was not found.")
        return await self.get_by_id(user_id)

    async def get_by_id(self, user_id: str) -> UserAccountDocument | None:
        return _inflate(UserAccountDocument, await self.collection.find_one({"_id": user_id}))


class MongoPredictionRepository(BaseMongoRepository, PredictionRepository):
    async def upsert_batch(self, documents: list[PredictionDocument]) -> list[PredictionDocument]:
        if not documents:
            return documents
        operations = [
            ReplaceOne({"_id": document.id}, _serialize(document), upsert=True)
            for document in documents
        ]
        try:
            await self.collection.bulk_write(operations, ordered=True)
        except Exception as exc:  # pragma: no cover - depends on driver/runtime
            raise PersistenceError(f"Could not persist prediction batch: {exc}") from exc
        return documents

    async def get_by_id(self, prediction_id: str) -> PredictionDocument | None:
        return _inflate(PredictionDocument, await self.collection.find_one({"_id": prediction_id}))

    async def attach_feedback(self, prediction_id: str, feedback_label_id: str) -> None:
        result = await self.collection.update_one(
            {"_id": prediction_id},
            {"$set": {"feedback_label_id": feedback_label_id}},
        )
        if result.matched_count == 0:
            raise NotFoundError(f"Prediction '{prediction_id}' was not found.")

    async def summarize(
        self,
        *,
        bucket: Literal["hour", "day", "month"],
        start_date: datetime | None,
        end_date: datetime | None,
        model_version: str | None,
    ) -> list[PredictionAnalyticsRecord]:
        match_stage: dict[str, Any] = {}
        if start_date or end_date:
            match_stage["created_at"] = {}
            if start_date:
                match_stage["created_at"]["$gte"] = start_date
            if end_date:
                match_stage["created_at"]["$lt"] = end_date
        if model_version:
            match_stage["model_version"] = model_version

        pipeline: list[dict[str, Any]] = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": {
                            "model_version": "$model_version",
                            "date_bucket": _date_bucket_expression(bucket),
                            "confidence_tier": "$confidence_tier",
                        },
                        "total_predictions": {"$sum": 1},
                        "positive_predictions": {"$sum": "$prediction_label"},
                        "average_confidence_score": {"$avg": "$confidence_score"},
                        "average_probability": {"$avg": "$probabilities.disease"},
                    }
                },
                {
                    "$sort": {
                        "_id.date_bucket": 1,
                        "_id.model_version": 1,
                        "_id.confidence_tier": 1,
                    }
                },
            ]
        )

        records: list[PredictionAnalyticsRecord] = []
        cursor = await self.collection.aggregate(pipeline)
        async for item in cursor:
            total_predictions = int(item["total_predictions"])
            positive_predictions = int(item["positive_predictions"])
            records.append(
                PredictionAnalyticsRecord(
                    model_version=str(item["_id"]["model_version"]),
                    date_bucket=str(item["_id"]["date_bucket"]),
                    confidence_tier=str(item["_id"]["confidence_tier"]),
                    total_predictions=total_predictions,
                    positive_predictions=positive_predictions,
                    negative_predictions=total_predictions - positive_predictions,
                    average_confidence_score=float(item["average_confidence_score"]),
                    average_probability=float(item["average_probability"]),
                )
            )
        return records


class MongoModelVersionRepository(BaseMongoRepository, ModelVersionRepository):
    async def create(self, document: ModelVersionDocument) -> ModelVersionDocument:
        await self._replace_by_id(document)
        return document

    async def get_by_id(self, version_id: str) -> ModelVersionDocument | None:
        return _inflate(ModelVersionDocument, await self.collection.find_one({"_id": version_id}))

    async def get_active(self) -> ModelVersionDocument | None:
        return _inflate(
            ModelVersionDocument,
            await self.collection.find_one(
                {"is_active": True},
                sort=[("activated_at", DESCENDING)],
            ),
        )

    async def list_versions(self) -> list[ModelVersionDocument]:
        items: list[ModelVersionDocument] = []
        async for item in self.collection.find().sort(
            [("activated_at", DESCENDING), ("created_at", DESCENDING)]
        ):
            items.append(_inflate(ModelVersionDocument, item))
        return items

    async def activate(self, version_id: str, activated_at) -> ModelVersionDocument:
        await self.collection.update_many({"is_active": True}, {"$set": {"is_active": False}})
        result = await self.collection.update_one(
            {"_id": version_id},
            {"$set": {"is_active": True, "activated_at": activated_at}},
        )
        if result.matched_count == 0:
            raise NotFoundError(f"Model version '{version_id}' was not found.")
        return await self.get_by_id(version_id)

    async def get_previous_active(self, current_version_id: str) -> ModelVersionDocument | None:
        data = await self.collection.find_one(
            {"_id": {"$ne": current_version_id}},
            sort=[("activated_at", DESCENDING), ("created_at", DESCENDING)],
        )
        return _inflate(ModelVersionDocument, data)


class MongoFeedbackRepository(BaseMongoRepository, FeedbackRepository):
    async def get_by_prediction_id(self, prediction_id: str) -> FeedbackLabelDocument | None:
        return _inflate(
            FeedbackLabelDocument,
            await self.collection.find_one({"prediction_id": prediction_id}),
        )

    async def upsert(self, document: FeedbackLabelDocument) -> tuple[FeedbackLabelDocument, str]:
        existing = await self.get_by_prediction_id(document.prediction_id)
        status = "created"
        if existing is not None:
            document = document.model_copy(
                update={"id": existing.id, "created_at": existing.created_at}
            )
            status = "updated"
        await self._replace_by_id(document)
        return document, status


class MongoDriftSnapshotRepository(BaseMongoRepository, DriftSnapshotRepository):
    async def upsert(
        self,
        document: DriftMonitoringSnapshotDocument,
    ) -> DriftMonitoringSnapshotDocument:
        await self._replace_by_id(document)
        return document

    async def get_by_id(self, snapshot_id: str) -> DriftMonitoringSnapshotDocument | None:
        return _inflate(
            DriftMonitoringSnapshotDocument,
            await self.collection.find_one({"_id": snapshot_id}),
        )

    async def get_baseline_for_model(
        self,
        model_version: str,
    ) -> DriftMonitoringSnapshotDocument | None:
        return _inflate(
            DriftMonitoringSnapshotDocument,
            await self.collection.find_one(
                {"model_version": model_version, "source": "training_baseline"},
                sort=[("created_at", DESCENDING)],
            ),
        )


class MongoAPIRequestLogRepository(BaseMongoRepository, APIRequestLogRepository):
    async def reserve(self, document: APIRequestLogDocument) -> RequestLogReservation:
        existing = await self._find_existing(document)
        if existing is None:
            try:
                await self.collection.insert_one(_serialize(document))
                return RequestLogReservation(document=document, is_replay=False)
            except DuplicateKeyError:
                existing = await self._find_existing(document)
            except Exception as exc:  # pragma: no cover - depends on driver/runtime
                raise PersistenceError(f"Could not reserve request log '{document.id}': {exc}") from exc

        if existing is None:
            raise PersistenceError(f"Could not resolve request log reservation for '{document.id}'.")

        if existing.status == "COMPLETED" and existing.response_payload is not None:
            return RequestLogReservation(document=existing, is_replay=True)

        updated_payload = existing.model_copy(
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
        await self._replace_by_id(updated_payload)
        return RequestLogReservation(document=updated_payload, is_replay=False)

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
        completed_at = utc_now()
        result = await self.collection.update_one(
            {"_id": request_log_id},
            {
                "$set": {
                    "status": "COMPLETED",
                    "status_code": status_code,
                    "latency_ms": float(latency_ms),
                    "model_version": model_version,
                    "prediction_ids": prediction_ids,
                    "response_payload": response_payload,
                    "error_message": None,
                    "updated_at": completed_at,
                    "completed_at": completed_at,
                }
            },
        )
        if result.matched_count == 0:
            raise NotFoundError(f"Request log '{request_log_id}' was not found.")
        return await self.get_by_id(request_log_id)

    async def fail(
        self,
        request_log_id: str,
        *,
        status_code: int,
        latency_ms: float,
        error_message: str,
    ) -> APIRequestLogDocument:
        completed_at = utc_now()
        result = await self.collection.update_one(
            {"_id": request_log_id},
            {
                "$set": {
                    "status": "FAILED",
                    "status_code": status_code,
                    "latency_ms": float(latency_ms),
                    "model_version": None,
                    "prediction_ids": [],
                    "response_payload": None,
                    "error_message": error_message,
                    "updated_at": completed_at,
                    "completed_at": completed_at,
                }
            },
        )
        if result.matched_count == 0:
            raise NotFoundError(f"Request log '{request_log_id}' was not found.")
        return await self.get_by_id(request_log_id)

    async def get_by_id(self, request_log_id: str) -> APIRequestLogDocument | None:
        return _inflate(APIRequestLogDocument, await self.collection.find_one({"_id": request_log_id}))

    async def get_by_route_and_idempotency(
        self,
        route: str,
        idempotency_key: str,
    ) -> APIRequestLogDocument | None:
        return _inflate(
            APIRequestLogDocument,
            await self.collection.find_one(
                {
                    "request_metadata.route": route,
                    "request_metadata.idempotency_key": idempotency_key,
                }
            ),
        )

    async def _find_existing(self, document: APIRequestLogDocument) -> APIRequestLogDocument | None:
        if document.request_metadata.idempotency_key:
            existing = await self.get_by_route_and_idempotency(
                document.request_metadata.route,
                document.request_metadata.idempotency_key,
            )
            if existing is not None:
                return existing
        return await self.get_by_id(document.id)


class MongoRepositoryBundle(RepositoryBundle):
    """MongoDB repository bundle with connection lifecycle helpers."""

    def __init__(self, settings: Settings, client_factory=AsyncMongoClient):
        if client_factory is None:
            raise DependencyUnavailableError(
                "Async MongoDB support requires pymongo>=4.11.0. Install requirements.txt first."
            )

        self.settings = settings
        _timeout_kwargs: dict = {}
        if settings.mongodb_connect_timeout_ms is not None:
            _timeout_kwargs["connectTimeoutMS"] = settings.mongodb_connect_timeout_ms
        if settings.mongodb_server_selection_timeout_ms is not None:
            _timeout_kwargs["serverSelectionTimeoutMS"] = settings.mongodb_server_selection_timeout_ms
        if settings.mongodb_socket_timeout_ms is not None:
            _timeout_kwargs["socketTimeoutMS"] = settings.mongodb_socket_timeout_ms
        if settings.mongodb_wait_queue_timeout_ms is not None:
            _timeout_kwargs["waitQueueTimeoutMS"] = settings.mongodb_wait_queue_timeout_ms
        self.client = client_factory(
            _resolve_mongodb_uri(settings),
            minPoolSize=settings.mongodb_min_pool_size,
            maxPoolSize=settings.mongodb_max_pool_size,
            maxIdleTimeMS=settings.mongodb_max_idle_time_ms,
            **_timeout_kwargs,
        )
        self.db = self.client[settings.mongodb_database]
        self._validators = _collection_validators()
        self._indexes = _collection_indexes()

        super().__init__(
            backend_name="mongodb",
            subjects=MongoSubjectRepository(self.db[COLLECTION_SUBJECTS]),
            users=MongoUserRepository(self.db[COLLECTION_USERS]),
            predictions=MongoPredictionRepository(self.db[COLLECTION_PREDICTIONS]),
            model_versions=MongoModelVersionRepository(self.db[COLLECTION_MODEL_REGISTRY]),
            feedback_labels=MongoFeedbackRepository(self.db[COLLECTION_FEEDBACK]),
            drift_snapshots=MongoDriftSnapshotRepository(self.db[COLLECTION_DRIFT]),
            api_request_logs=MongoAPIRequestLogRepository(self.db[COLLECTION_REQUEST_LOGS]),
        )

    async def initialize(self) -> None:
        await self._assert_connectivity()
        await self._ensure_collection_validators()
        await self._ensure_indexes()
        await self._verify_index_presence()
        await self._verify_validator_readiness()

    async def ping(self) -> bool:
        try:
            await self.client.admin.command("ping")
            return True
        except Exception as exc:  # pragma: no cover - depends on runtime service availability
            LOGGER.warning("MongoDB ping failed: %s", exc)
            return False

    async def close(self) -> None:
        self.client.close()

    async def _assert_connectivity(self) -> None:
        try:
            await self.client.admin.command("ping")
        except Exception as exc:
            raise ConfigurationError(f"MongoDB connectivity check failed: {exc}") from exc

    async def _ensure_collection_validators(self) -> None:
        existing_names = {
            name for name in await self.db.list_collection_names()
        }
        for name, validator in self._validators.items():
            try:
                if name not in existing_names:
                    await self.db.create_collection(
                        name,
                        validator=validator,
                        validationLevel="moderate",
                    )
                else:
                    await self.db.command(
                        {
                            "collMod": name,
                            "validator": validator,
                            "validationLevel": "moderate",
                        }
                    )
            except OperationFailure as exc:
                raise ConfigurationError(
                    f"MongoDB validator setup failed for collection '{name}': {exc}"
                ) from exc

    async def _ensure_indexes(self) -> None:
        for name, indexes in self._indexes.items():
            for index in indexes:
                try:
                    await self.db[name].create_indexes([index])
                except OperationFailure as exc:
                    error_code = getattr(exc, "code", None)
                    # Code 85 = IndexOptionsConflict: same name, different options.
                    # Code 86 = IndexKeySpecsConflict: same name, different key spec / filter.
                    # Drop and recreate so the correct definition is enforced.
                    if error_code in (85, 86):
                        index_name = index.document.get("name")
                        try:
                            await self.db[name].drop_index(index_name)
                            await self.db[name].create_indexes([index])
                            LOGGER.info(
                                "Re-created index '%s' on '%s' with updated options.",
                                index_name, name,
                            )
                        except Exception as redrop_exc:
                            self._add_startup_warning(
                                f"Could not recreate index '{index_name}' on '{name}': {redrop_exc}"
                            )
                        continue
                    raise ConfigurationError(f"MongoDB index setup failed for '{name}': {exc}") from exc
                except ConnectionFailure as exc:
                    # Transient network issue during index creation.
                    # Indexes from a prior run likely already exist — log a warning and continue.
                    index_name = index.document.get("name", "<unknown>")
                    self._add_startup_warning(
                        f"Network error verifying index '{index_name}' on '{name}' "
                        f"(will proceed; index may already exist): {exc}"
                    )
                except PyMongoError as exc:
                    raise ConfigurationError(f"MongoDB index setup failed for '{name}': {exc}") from exc

    async def _verify_index_presence(self) -> None:
        for name, indexes in self._indexes.items():
            response = await self.db.command({"listIndexes": name, "cursor": {}})
            existing_entries = response.get("cursor", {}).get("firstBatch", [])
            existing_by_key: dict[tuple[tuple[str, Any], ...], list[dict[str, Any]]] = {}
            for entry in existing_entries:
                signature = _normalize_index_key(entry.get("key", {}))
                existing_by_key.setdefault(signature, []).append(entry)

            missing: list[str] = []
            incompatible: list[str] = []

            for expected in indexes:
                expected_doc = expected.document
                expected_name = expected_doc.get("name", "<unnamed>")
                expected_signature = _normalize_index_key(expected_doc.get("key", {}))
                candidates = existing_by_key.get(expected_signature, [])
                if not candidates:
                    missing.append(expected_name)
                    continue

                expected_unique = bool(expected_doc.get("unique", False))
                expected_sparse = bool(expected_doc.get("sparse", False))
                compatible = [
                    item
                    for item in candidates
                    if bool(item.get("unique", False)) == expected_unique
                    and bool(item.get("sparse", False)) == expected_sparse
                ]
                if not compatible:
                    incompatible.append(expected_name)
                    continue

                if not any(item.get("name") == expected_name for item in compatible):
                    existing_names = ", ".join(sorted(str(item.get("name")) for item in compatible))
                    self._add_startup_warning(
                        "Index name differs for "
                        f"'{name}.{expected_name}' (existing: {existing_names})."
                    )

            if missing:
                raise ConfigurationError(
                    f"MongoDB startup check failed: missing indexes for '{name}': {sorted(missing)}"
                )

            if incompatible:
                raise ConfigurationError(
                    "MongoDB startup check failed: incompatible index options for "
                    f"'{name}': {sorted(incompatible)}"
                )

    async def _verify_validator_readiness(self) -> None:
        for name in self._validators:
            response = await self.db.command({"listCollections": 1, "filter": {"name": name}})
            collections = response.get("cursor", {}).get("firstBatch", [])
            if not collections:
                raise ConfigurationError(
                    f"MongoDB startup check failed: collection '{name}' is missing."
                )
            validator = collections[0].get("options", {}).get("validator")
            if not validator:
                raise ConfigurationError(
                    f"MongoDB startup check failed: validator missing for '{name}'."
                )

    def _add_startup_warning(self, message: str) -> None:
        if message not in self.startup_warnings:
            self.startup_warnings.append(message)


def build_mongodb_repository_bundle(
    settings: Settings,
    client_factory=AsyncMongoClient,
) -> MongoRepositoryBundle:
    """Create a MongoDB-backed repository bundle."""
    return MongoRepositoryBundle(settings, client_factory=client_factory)
