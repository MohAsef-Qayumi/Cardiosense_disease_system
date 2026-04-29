import asyncio

from src.core.settings import get_settings
from src.core.utils import canonical_json_hash, utc_now
from src.repositories.inmemory import build_inmemory_repository_bundle
from src.services.drift import DriftMonitoringService
from src.services.model_registry import ModelRegistryService
from src.services.prediction_service import InferenceRequestContext, PredictionService


def _payload(weight: float = 62.0, patient_id: int = 101):
    return {
        "id": patient_id,
        "age": 18393,
        "gender": 2,
        "height": 168,
        "weight": weight,
        "ap_hi": 120,
        "ap_lo": 80,
        "cholesterol": 1,
        "gluc": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
    }


def _context(payload, route="/predict", idempotency_key=None):
    return InferenceRequestContext(
        request_id="request_service_test",
        route=route,
        method="POST",
        payload_hash=canonical_json_hash(payload),
        idempotency_key=idempotency_key,
        client_ip="127.0.0.1",
        user_agent="pytest",
        content_length=123,
    )


def _build_service():
    settings = get_settings()
    repositories = build_inmemory_repository_bundle()
    registry = ModelRegistryService(repositories.model_versions, settings)
    drift = DriftMonitoringService(repositories.drift_snapshots, settings)
    return PredictionService(repositories, settings, registry, drift), repositories, registry


def test_feedback_attach_updates_prediction_reference():
    async def scenario():
        service, repositories, _ = _build_service()
        payload = _payload()
        prediction_response = await service.predict_single(
            payload,
            _context(payload, idempotency_key="svc-predict"),
        )

        feedback_payload = {
            "prediction_id": prediction_response.prediction_id,
            "true_label": 1,
            "label_source": "human_review",
        }
        feedback_response = await service.attach_feedback(
            prediction_id=prediction_response.prediction_id,
            true_label=1,
            label_source="human_review",
            reviewer="qa",
            notes=None,
            context=_context(feedback_payload, route="/feedback"),
        )

        stored_prediction = await repositories.predictions.get_by_id(prediction_response.prediction_id)
        assert feedback_response.prediction_id == prediction_response.prediction_id
        assert stored_prediction.feedback_label_id == feedback_response.feedback_id

    asyncio.run(scenario())


def test_model_registry_rollback_switches_active_model_version():
    async def scenario():
        settings = get_settings()
        repositories = build_inmemory_repository_bundle()
        registry = ModelRegistryService(repositories.model_versions, settings)
        timestamp = utc_now()

        first = await registry._bootstrap_local_model()
        second = first.model_copy(
            update={
                "id": "model_manual_second",
                "is_active": False,
                "created_at": timestamp,
                "activated_at": timestamp,
            }
        )
        await repositories.model_versions.create(second)
        await repositories.model_versions.activate(second.id, timestamp)

        rolled_back = await registry.rollback(first.id)
        assert rolled_back.id == first.id

    asyncio.run(scenario())


def test_batch_prediction_idempotency_is_safe_under_concurrency():
    async def scenario():
        service, repositories, _ = _build_service()
        batch_payload = [_payload(patient_id=201), _payload(weight=72.0, patient_id=202)]
        context = _context(batch_payload, route="/predict/batch", idempotency_key="batch-concurrency")

        first, second = await asyncio.gather(
            service.predict_batch(batch_payload, context),
            service.predict_batch(batch_payload, context),
        )

        assert [item.prediction_id for item in first.results] == [
            item.prediction_id for item in second.results
        ]

        stored_predictions = [
            await repositories.predictions.get_by_id(item.prediction_id) for item in first.results
        ]
        assert all(document is not None for document in stored_predictions)
        assert len(
            {
                document.id
                for document in stored_predictions
                if document is not None
            }
        ) == len(first.results)

    asyncio.run(scenario())
