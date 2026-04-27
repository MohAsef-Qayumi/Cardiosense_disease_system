"""Model registry and runtime loading services."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import joblib

from src.core.exceptions import ModelNotReadyError, NotFoundError
from src.core.logging_utils import get_logger
from src.core.settings import Settings
from src.core.utils import file_sha256, new_document_id, utc_now
from src.repositories.base import ModelVersionRepository
from src.schemas.documents import (
    EvaluationSummary,
    ModelVersionDocument,
    PerClassMetrics,
    ThresholdOptimizationSummary,
)

LOGGER = get_logger(__name__)


def _placeholder_per_class() -> dict[str, PerClassMetrics]:
    return {
        "No Disease": PerClassMetrics(precision=0.0, recall=0.0, f1=0.0, support=0),
        "Disease": PerClassMetrics(precision=0.0, recall=0.0, f1=0.0, support=0),
    }


def evaluation_summary_from_flat_metrics(split: str, metrics: dict[str, Any]) -> EvaluationSummary:
    """Build a structured evaluation summary from flat metrics."""
    per_class = metrics.get("per_class") or _placeholder_per_class()
    return EvaluationSummary(
        split=split,
        accuracy=float(metrics.get("accuracy", 0.0)),
        precision=float(metrics.get("precision", 0.0)),
        recall=float(metrics.get("recall", 0.0)),
        specificity=float(metrics.get("specificity", 0.0)),
        f1=float(metrics.get("f1", 0.0)),
        roc_auc=float(metrics.get("roc_auc", 0.0)),
        pr_auc=float(metrics.get("pr_auc", 0.0)),
        balanced_accuracy=float(metrics.get("balanced_accuracy", 0.0)),
        mcc=float(metrics.get("mcc", 0.0)),
        brier=float(metrics.get("brier", 0.0)),
        per_class={
            label: value if isinstance(value, PerClassMetrics) else PerClassMetrics(**value)
            for label, value in per_class.items()
        },
    )


@dataclass
class LoadedModelRuntime:
    """Resolved serving runtime for the active model version."""

    model_version: ModelVersionDocument
    preprocessing_pipeline: Any
    model_service: Any


class ModelRegistryService:
    """Manage active model versions and runtime artifact loading."""

    def __init__(self, repository: ModelVersionRepository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self.logger = LOGGER
        self._runtime_cache: LoadedModelRuntime | None = None

    async def get_active_runtime(self) -> LoadedModelRuntime:
        if self._runtime_cache is not None:
            return self._runtime_cache

        active = await self.repository.get_active()
        if active is None:
            active = await self._bootstrap_local_model()
        self._runtime_cache = self._load_runtime(active)
        return self._runtime_cache

    async def get_active_model_version(self) -> ModelVersionDocument:
        return (await self.get_active_runtime()).model_version

    async def register_model_version(
        self,
        *,
        model_name: str,
        artifact_path: Path,
        preprocessing_path: Path,
        threshold_used: float,
        threshold_objective: str,
        threshold_score: float,
        validation_metrics: dict[str, Any],
        test_metrics: dict[str, Any],
        class_balance: dict[str, float],
        feature_names: list[str],
        training_parameters: dict[str, Any],
        baseline_snapshot_id: str | None,
        metrics_path: Path | None = None,
        notes: str | None = None,
        preloaded_model_service: Any | None = None,
        preloaded_preprocessing_pipeline: Any | None = None,
    ) -> ModelVersionDocument:
        version_id = new_document_id("model")
        timestamp = utc_now()
        document = ModelVersionDocument(
            id=version_id,
            model_name=model_name,
            artifact_path=str(artifact_path),
            preprocessing_path=str(preprocessing_path),
            artifact_sha256=file_sha256(artifact_path),
            preprocessing_sha256=file_sha256(preprocessing_path),
            threshold_used=float(threshold_used),
            threshold_objective=threshold_objective,
            threshold_summary=ThresholdOptimizationSummary(
                objective=threshold_objective,
                threshold=float(threshold_used),
                score=float(threshold_score),
                evaluated_thresholds=int(validation_metrics.get("threshold_candidates_evaluated", 0)),
            ),
            validation_metrics=evaluation_summary_from_flat_metrics("validation", validation_metrics),
            test_metrics=evaluation_summary_from_flat_metrics("test", test_metrics),
            class_balance=class_balance,
            feature_names=feature_names,
            training_parameters=training_parameters,
            baseline_snapshot_id=baseline_snapshot_id,
            metrics_path=str(metrics_path) if metrics_path else None,
            is_active=True,
            created_at=timestamp,
            activated_at=timestamp,
            notes=notes,
        )
        await self.repository.create(document)
        active = await self.repository.activate(document.id, timestamp)
        self._runtime_cache = LoadedModelRuntime(
            model_version=active,
            model_service=preloaded_model_service
            if preloaded_model_service is not None
            else joblib.load(str(artifact_path)),
            preprocessing_pipeline=preloaded_preprocessing_pipeline
            if preloaded_preprocessing_pipeline is not None
            else joblib.load(str(preprocessing_path)),
        )
        self.logger.info("Registered and activated model_version=%s", active.id)
        return active

    async def rollback(self, target_version: str | None = None) -> ModelVersionDocument:
        current = await self.repository.get_active()
        if current is None:
            raise ModelNotReadyError("No active model version exists for rollback.")

        target = (
            await self.repository.get_by_id(target_version)
            if target_version
            else await self.repository.get_previous_active(current.id)
        )
        if target is None:
            raise NotFoundError("No rollback target model version is available.")

        activated = await self.repository.activate(target.id, utc_now())
        self._runtime_cache = self._load_runtime(activated)
        self.logger.warning("Rolled back active model to model_version=%s", activated.id)
        return activated

    async def attach_baseline_snapshot(
        self,
        model_version_id: str,
        baseline_snapshot_id: str,
    ) -> ModelVersionDocument:
        document = await self.repository.get_by_id(model_version_id)
        if document is None:
            raise NotFoundError(f"Model version '{model_version_id}' was not found.")

        updated = document.model_copy(update={"baseline_snapshot_id": baseline_snapshot_id})
        await self.repository.create(updated)
        if self._runtime_cache is not None and self._runtime_cache.model_version.id == model_version_id:
            self._runtime_cache = LoadedModelRuntime(
                model_version=updated,
                preprocessing_pipeline=self._runtime_cache.preprocessing_pipeline,
                model_service=self._runtime_cache.model_service,
            )
        return updated

    def _load_runtime(self, document: ModelVersionDocument) -> LoadedModelRuntime:
        artifact_path = Path(document.artifact_path)
        preprocessing_path = Path(document.preprocessing_path)
        if not artifact_path.exists() or not preprocessing_path.exists():
            raise ModelNotReadyError(
                f"Artifacts for model_version '{document.id}' are missing on disk."
            )

        return LoadedModelRuntime(
            model_version=document,
            model_service=joblib.load(str(artifact_path)),
            preprocessing_pipeline=joblib.load(str(preprocessing_path)),
        )

    async def _bootstrap_local_model(self) -> ModelVersionDocument:
        if not self.settings.bootstrap_local_model:
            raise ModelNotReadyError("No active model version exists in the registry.")
        if not (
            self.settings.artifact_model_path.exists()
            and self.settings.artifact_preprocessing_path.exists()
        ):
            raise ModelNotReadyError(
                "No active model version exists and local bootstrap artifacts are missing."
            )

        timestamp = utc_now()
        metrics_payload = {}
        if self.settings.artifact_metrics_path.exists():
            with open(self.settings.artifact_metrics_path, "r", encoding="utf-8") as handle:
                raw_metrics = json.load(handle)
            if isinstance(raw_metrics, list) and raw_metrics:
                metrics_payload = raw_metrics[0]
            elif isinstance(raw_metrics, dict):
                metrics_payload = {
                    "val_accuracy": raw_metrics.get("validation", {}).get("accuracy", 0.0),
                    "val_precision": raw_metrics.get("validation", {}).get("precision", 0.0),
                    "val_recall": raw_metrics.get("validation", {}).get("recall", 0.0),
                    "val_specificity": raw_metrics.get("validation", {}).get("specificity", 0.0),
                    "val_f1": raw_metrics.get("validation", {}).get("f1", 0.0),
                    "val_roc_auc": raw_metrics.get("validation", {}).get("roc_auc", 0.0),
                    "val_pr_auc": raw_metrics.get("validation", {}).get("pr_auc", 0.0),
                    "val_balanced_accuracy": raw_metrics.get("validation", {}).get(
                        "balanced_accuracy",
                        0.0,
                    ),
                    "val_mcc": raw_metrics.get("validation", {}).get("mcc", 0.0),
                    "val_brier": raw_metrics.get("validation", {}).get("brier", 0.0),
                    "test_accuracy": raw_metrics.get("test", {}).get("accuracy", 0.0),
                    "test_precision": raw_metrics.get("test", {}).get("precision", 0.0),
                    "test_recall": raw_metrics.get("test", {}).get("recall", 0.0),
                    "test_specificity": raw_metrics.get("test", {}).get("specificity", 0.0),
                    "test_f1": raw_metrics.get("test", {}).get("f1", 0.0),
                    "test_roc_auc": raw_metrics.get("test", {}).get("roc_auc", 0.0),
                    "test_pr_auc": raw_metrics.get("test", {}).get("pr_auc", 0.0),
                    "test_balanced_accuracy": raw_metrics.get("test", {}).get(
                        "balanced_accuracy",
                        0.0,
                    ),
                    "test_mcc": raw_metrics.get("test", {}).get("mcc", 0.0),
                    "test_brier": raw_metrics.get("test", {}).get("brier", 0.0),
                }

        loaded_model = joblib.load(str(self.settings.artifact_model_path))
        decision_threshold = float(getattr(loaded_model, "decision_threshold", 0.5))

        document = ModelVersionDocument(
            id=new_document_id("model"),
            model_name="XGBoost",
            artifact_path=str(self.settings.artifact_model_path),
            preprocessing_path=str(self.settings.artifact_preprocessing_path),
            artifact_sha256=file_sha256(self.settings.artifact_model_path),
            preprocessing_sha256=file_sha256(self.settings.artifact_preprocessing_path),
            threshold_used=decision_threshold,
            threshold_objective="bootstrap_existing_artifact",
            threshold_summary=ThresholdOptimizationSummary(
                objective="bootstrap_existing_artifact",
                threshold=decision_threshold,
                score=float(metrics_payload.get("test_balanced_accuracy", 0.0)),
                evaluated_thresholds=0,
            ),
            validation_metrics=evaluation_summary_from_flat_metrics(
                "validation",
                {
                    "accuracy": metrics_payload.get("val_accuracy", 0.0),
                    "precision": metrics_payload.get("val_precision", 0.0),
                    "recall": metrics_payload.get("val_recall", 0.0),
                    "specificity": metrics_payload.get("val_specificity", 0.0),
                    "f1": metrics_payload.get("val_f1", 0.0),
                    "roc_auc": metrics_payload.get("val_roc_auc", 0.0),
                    "pr_auc": metrics_payload.get("val_pr_auc", 0.0),
                    "balanced_accuracy": metrics_payload.get("val_balanced_accuracy", 0.0),
                    "mcc": metrics_payload.get("val_mcc", 0.0),
                    "brier": metrics_payload.get("val_brier", 0.0),
                },
            ),
            test_metrics=evaluation_summary_from_flat_metrics(
                "test",
                {
                    "accuracy": metrics_payload.get("test_accuracy", 0.0),
                    "precision": metrics_payload.get("test_precision", 0.0),
                    "recall": metrics_payload.get("test_recall", 0.0),
                    "specificity": metrics_payload.get("test_specificity", 0.0),
                    "f1": metrics_payload.get("test_f1", 0.0),
                    "roc_auc": metrics_payload.get("test_roc_auc", 0.0),
                    "pr_auc": metrics_payload.get("test_pr_auc", 0.0),
                    "balanced_accuracy": metrics_payload.get("test_balanced_accuracy", 0.0),
                    "mcc": metrics_payload.get("test_mcc", 0.0),
                    "brier": metrics_payload.get("test_brier", 0.0),
                },
            ),
            class_balance={},
            feature_names=[],
            training_parameters={},
            baseline_snapshot_id=None,
            metrics_path=str(self.settings.artifact_metrics_path)
            if self.settings.artifact_metrics_path.exists()
            else None,
            is_active=True,
            created_at=timestamp,
            activated_at=timestamp,
            notes="Bootstrapped from local artifacts for migration compatibility.",
        )
        await self.repository.create(document)
        await self.repository.activate(document.id, timestamp)
        self.logger.warning("Bootstrapped active model version from local artifacts.")
        return document
