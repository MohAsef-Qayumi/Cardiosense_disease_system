"""Prediction, persistence, and feedback services."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import pandas as pd

from src.core.exceptions import CardioSenseError, IdempotencyConflictError, NotFoundError
from src.core.logging_utils import get_logger
from src.core.settings import Settings
from src.core.utils import (
    canonical_json_hash,
    pseudonymous_subject_hash,
    stable_document_id,
    utc_now,
)
from src.repositories.base import RepositoryBundle, RequestLogReservation
from src.schemas.api import (
    BatchPredictionResponse,
    FeedbackResponse,
    PredictionResponse,
    PredictionResult,
    StoredPredictionResult,
)
from src.schemas.documents import (
    APIRequestLogDocument,
    FeedbackLabelDocument,
    PredictionDocument,
    ProbabilityScores,
    RequestMetadata,
    SubjectDocument,
)
from src.services.drift import DriftMonitoringService
from src.services.model_registry import ModelRegistryService

LOGGER = get_logger(__name__)

RAW_FEATURE_COLUMNS = [
    "id",
    "age",
    "gender",
    "height",
    "weight",
    "ap_hi",
    "ap_lo",
    "cholesterol",
    "gluc",
    "smoke",
    "alco",
    "active",
]


@dataclass
class InferenceRequestContext:
    """Normalized request context used by the service layer."""

    request_id: str
    route: str
    method: str
    payload_hash: str
    idempotency_key: str | None
    client_ip: str | None
    user_agent: str | None
    content_length: int | None


class PredictionService:
    """Orchestrate serving, persistence, drift snapshots, and feedback."""

    def __init__(
        self,
        repositories: RepositoryBundle,
        settings: Settings,
        model_registry: ModelRegistryService,
        drift_service: DriftMonitoringService,
    ):
        self.repositories = repositories
        self.settings = settings
        self.model_registry = model_registry
        self.drift_service = drift_service
        self.logger = LOGGER

    async def predict_single(
        self,
        payload: dict[str, Any],
        context: InferenceRequestContext,
    ) -> PredictionResponse:
        return await self._execute_prediction(payloads=[payload], context=context, single=True)

    async def predict_batch(
        self,
        payloads: list[dict[str, Any]],
        context: InferenceRequestContext,
    ) -> BatchPredictionResponse:
        return await self._execute_prediction(payloads=payloads, context=context, single=False)

    async def attach_feedback(
        self,
        prediction_id: str,
        true_label: int,
        label_source: str,
        reviewer: str | None,
        notes: str | None,
        context: InferenceRequestContext,
    ) -> FeedbackResponse:
        started = perf_counter()
        feedback_payload = {
            "prediction_id": prediction_id,
            "true_label": true_label,
            "label_source": label_source,
            "reviewer": reviewer,
            "notes": notes,
        }
        reservation = await self._reserve_request(context)
        self._assert_reservation_matches_payload(reservation, context)
        if reservation.is_replay and reservation.document.response_payload is not None:
            return FeedbackResponse.model_validate(reservation.document.response_payload)

        try:
            prediction = await self.repositories.predictions.get_by_id(prediction_id)
            if prediction is None:
                raise NotFoundError(f"Prediction '{prediction_id}' was not found.")

            existing_feedback = await self.repositories.feedback_labels.get_by_prediction_id(prediction_id)
            feedback = FeedbackLabelDocument(
                id=existing_feedback.id
                if existing_feedback
                else stable_document_id("feedback", prediction_id),
                prediction_id=prediction_id,
                true_label=int(true_label),
                label_source=label_source,
                reviewer=reviewer,
                notes=notes,
                request_metadata=self._build_request_metadata(context, reservation.document.id),
                created_at=existing_feedback.created_at if existing_feedback else reservation.document.created_at,
            )
            stored_feedback, status = await self.repositories.feedback_labels.upsert(feedback)
            await self.repositories.predictions.attach_feedback(prediction_id, stored_feedback.id)

            response = FeedbackResponse(
                feedback_id=stored_feedback.id,
                prediction_id=prediction_id,
                true_label=int(true_label),
                created_at=stored_feedback.created_at,
                status="updated" if status == "updated" else "created",
            )
            await self._complete_request(
                reservation.document.id,
                status_code=200,
                latency_ms=(perf_counter() - started) * 1000,
                model_version=prediction.model_version,
                prediction_ids=[prediction_id],
                response_payload=response.model_dump(mode="python"),
            )
            return response
        except CardioSenseError as exc:
            await self._fail_request(
                reservation.document.id,
                status_code=exc.status_code,
                latency_ms=(perf_counter() - started) * 1000,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            await self._fail_request(
                reservation.document.id,
                status_code=500,
                latency_ms=(perf_counter() - started) * 1000,
                error_message=str(exc),
            )
            raise

    async def _execute_prediction(
        self,
        *,
        payloads: list[dict[str, Any]],
        context: InferenceRequestContext,
        single: bool,
    ) -> PredictionResponse | BatchPredictionResponse:
        started = perf_counter()
        reservation = await self._reserve_request(context)
        self._assert_reservation_matches_payload(reservation, context)
        if reservation.is_replay and reservation.document.response_payload is not None:
            if single:
                return PredictionResponse.model_validate(reservation.document.response_payload)
            return BatchPredictionResponse.model_validate(reservation.document.response_payload)

        try:
            response = await self._predict_records(
                payloads=payloads,
                context=context,
                operation_request_id=reservation.document.id,
                created_at=reservation.document.created_at,
            )
            await self._complete_request(
                reservation.document.id,
                status_code=200,
                latency_ms=(perf_counter() - started) * 1000,
                model_version=response.model_version,
                prediction_ids=self._prediction_ids_from_response(response),
                response_payload=response.model_dump(mode="python"),
            )
            return response
        except CardioSenseError as exc:
            await self._fail_request(
                reservation.document.id,
                status_code=exc.status_code,
                latency_ms=(perf_counter() - started) * 1000,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            await self._fail_request(
                reservation.document.id,
                status_code=500,
                latency_ms=(perf_counter() - started) * 1000,
                error_message=str(exc),
            )
            raise

    async def _predict_records(
        self,
        *,
        payloads: list[dict[str, Any]],
        context: InferenceRequestContext,
        operation_request_id: str,
        created_at,
    ) -> PredictionResponse | BatchPredictionResponse:
        runtime = await self.model_registry.get_active_runtime()
        raw_df = pd.DataFrame(payloads)
        if "id" not in raw_df.columns:
            raw_df["id"] = 0
        raw_df = raw_df[RAW_FEATURE_COLUMNS]

        transformed = runtime.preprocessing_pipeline.transform(raw_df)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        transformed_df = pd.DataFrame(transformed)
        prediction_frame = runtime.model_service.predict_with_confidence(transformed_df)

        prediction_documents: list[PredictionDocument] = []
        stored_results: list[StoredPredictionResult] = []

        for batch_index, (record, row) in enumerate(
            zip(raw_df.to_dict(orient="records"), prediction_frame.to_dict(orient="records"))
        ):
            subject = await self._upsert_subject(record, created_at)
            document = PredictionDocument(
                id=stable_document_id("prediction", operation_request_id, batch_index),
                request_id=operation_request_id,
                batch_index=batch_index,
                subject_id=subject.id,
                model_version=runtime.model_version.id,
                threshold_used=float(runtime.model_service.decision_threshold),
                prediction_label=int(row["prediction"]),
                probabilities=ProbabilityScores(
                    no_disease=float(row["prob_no_disease"]),
                    disease=float(row["prob_disease"]),
                ),
                confidence_score=float(row["confidence_score"]),
                confidence_tier=row["confidence_tier"],
                request_metadata=self._build_request_metadata(context, operation_request_id),
                input_features={key: self._json_safe_value(value) for key, value in record.items()},
                created_at=created_at,
            )
            prediction_documents.append(document)
            stored_results.append(
                StoredPredictionResult(
                    prediction_id=document.id,
                    subject_id=document.subject_id,
                    created_at=document.created_at,
                    prediction=document.prediction_label,
                    prob_no_disease=document.probabilities.no_disease,
                    prob_disease=document.probabilities.disease,
                    confidence_score=document.confidence_score,
                    confidence_tier=document.confidence_tier,
                )
            )

        await self.repositories.predictions.upsert_batch(prediction_documents)
        await self.drift_service.capture_inference_snapshot(
            runtime.model_version.id,
            operation_request_id,
            raw_df,
            prediction_frame,
            created_at,
        )

        if len(stored_results) == 1:
            result = stored_results[0]
            return PredictionResponse(
                request_id=operation_request_id,
                prediction_id=result.prediction_id,
                subject_id=result.subject_id,
                model_version=runtime.model_version.id,
                threshold_used=float(runtime.model_service.decision_threshold),
                created_at=result.created_at,
                result=PredictionResult(
                    prediction=result.prediction,
                    prob_no_disease=result.prob_no_disease,
                    prob_disease=result.prob_disease,
                    confidence_score=result.confidence_score,
                    confidence_tier=result.confidence_tier,
                ),
            )

        return BatchPredictionResponse(
            request_id=operation_request_id,
            count=len(stored_results),
            model_version=runtime.model_version.id,
            threshold_used=float(runtime.model_service.decision_threshold),
            results=stored_results,
        )

    async def _upsert_subject(self, record: dict[str, Any], timestamp) -> SubjectDocument:
        external_subject_id = record.get("id")
        stable_identifier = (
            str(external_subject_id)
            if external_subject_id not in (None, 0, "0")
            else canonical_json_hash(record)
        )
        subject_hash = pseudonymous_subject_hash(stable_identifier, self.settings.hash_salt)
        existing = await self.repositories.subjects.get_by_subject_hash(subject_hash)
        if existing is None:
            subject = SubjectDocument(
                id=stable_document_id("subject", subject_hash),
                external_subject_id=str(external_subject_id) if external_subject_id is not None else None,
                subject_hash=subject_hash,
                created_at=timestamp,
                last_seen_at=timestamp,
            )
        else:
            subject = existing.model_copy(update={"last_seen_at": timestamp})
        return await self.repositories.subjects.upsert(subject)

    def _build_request_metadata(
        self,
        context: InferenceRequestContext,
        operation_request_id: str,
    ) -> RequestMetadata:
        return RequestMetadata(
            request_id=operation_request_id,
            route=context.route,
            method=context.method,
            payload_hash=context.payload_hash,
            idempotency_key=context.idempotency_key,
            client_ip=context.client_ip,
            user_agent=context.user_agent,
            content_length=context.content_length,
        )

    async def _reserve_request(self, context: InferenceRequestContext) -> RequestLogReservation:
        operation_request_id = (
            stable_document_id("request", context.route, context.idempotency_key)
            if context.idempotency_key
            else context.request_id
        )
        timestamp = utc_now()
        request_log = APIRequestLogDocument(
            id=operation_request_id,
            request_metadata=self._build_request_metadata(context, operation_request_id),
            status="PENDING",
            status_code=None,
            latency_ms=None,
            model_version=None,
            prediction_ids=[],
            response_payload=None,
            error_message=None,
            created_at=timestamp,
            updated_at=timestamp,
            completed_at=None,
        )
        return await self.repositories.api_request_logs.reserve(request_log)

    def _assert_reservation_matches_payload(
        self,
        reservation: RequestLogReservation,
        context: InferenceRequestContext,
    ) -> None:
        if reservation.document.request_metadata.payload_hash != context.payload_hash:
            raise IdempotencyConflictError(
                "Idempotency key has already been used with a different payload."
            )

    async def _complete_request(
        self,
        request_id: str,
        *,
        status_code: int,
        latency_ms: float,
        model_version: str | None,
        prediction_ids: list[str],
        response_payload: dict[str, Any] | None,
    ) -> None:
        await self.repositories.api_request_logs.complete(
            request_id,
            status_code=status_code,
            latency_ms=latency_ms,
            model_version=model_version,
            prediction_ids=prediction_ids,
            response_payload=response_payload,
        )

    async def _fail_request(
        self,
        request_id: str,
        *,
        status_code: int,
        latency_ms: float,
        error_message: str,
    ) -> None:
        await self.repositories.api_request_logs.fail(
            request_id,
            status_code=status_code,
            latency_ms=latency_ms,
            error_message=error_message,
        )

    @staticmethod
    def _prediction_ids_from_response(
        response: PredictionResponse | BatchPredictionResponse,
    ) -> list[str]:
        if isinstance(response, PredictionResponse):
            return [response.prediction_id]
        return [item.prediction_id for item in response.results]

    @staticmethod
    def _json_safe_value(value: Any) -> Any:
        if hasattr(value, "item"):
            return value.item()
        return value
