"""Drift monitoring services for CardioSense."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.logging_utils import get_logger
from src.core.settings import Settings
from src.core.utils import new_document_id, stable_document_id, utc_now
from src.repositories.base import DriftSnapshotRepository
from src.schemas.documents import (
    DriftAlert,
    DriftMonitoringSnapshotDocument,
    FeatureDistributionStats,
    PredictionDistributionStats,
)

LOGGER = get_logger(__name__)


def _normalize_distribution(distribution: dict[str, float]) -> dict[str, float]:
    total = sum(distribution.values())
    if total <= 0:
        return distribution
    return {key: value / total for key, value in distribution.items()}


def _psi(expected: dict[str, float], actual: dict[str, float]) -> float:
    epsilon = 1e-6
    keys = sorted(set(expected) | set(actual))
    score = 0.0
    for key in keys:
        expected_value = max(expected.get(key, 0.0), epsilon)
        actual_value = max(actual.get(key, 0.0), epsilon)
        score += (actual_value - expected_value) * np.log(actual_value / expected_value)
    return float(score)


@dataclass
class DriftMonitoringService:
    """Build and persist drift monitoring snapshots."""

    repository: DriftSnapshotRepository
    settings: Settings

    def __post_init__(self) -> None:
        self.logger = LOGGER

    async def capture_training_baseline(
        self,
        model_version: str,
        feature_frame: pd.DataFrame,
        prediction_frame: pd.DataFrame,
    ) -> DriftMonitoringSnapshotDocument:
        snapshot = self._build_snapshot(
            snapshot_id=new_document_id("drift"),
            model_version=model_version,
            source="training_baseline",
            request_id=None,
            feature_frame=feature_frame,
            prediction_frame=prediction_frame,
            baseline_snapshot=None,
            created_at=utc_now(),
        )
        return await self.repository.upsert(snapshot)

    async def capture_inference_snapshot(
        self,
        model_version: str,
        request_id: str,
        feature_frame: pd.DataFrame,
        prediction_frame: pd.DataFrame,
        created_at,
    ) -> DriftMonitoringSnapshotDocument:
        baseline = await self.repository.get_baseline_for_model(model_version)
        snapshot = self._build_snapshot(
            snapshot_id=stable_document_id("drift", request_id, "inference"),
            model_version=model_version,
            source="inference_request",
            request_id=request_id,
            feature_frame=feature_frame,
            prediction_frame=prediction_frame,
            baseline_snapshot=baseline,
            created_at=created_at,
        )
        return await self.repository.upsert(snapshot)

    def _build_snapshot(
        self,
        *,
        snapshot_id: str,
        model_version: str,
        source: str,
        request_id: str | None,
        feature_frame: pd.DataFrame,
        prediction_frame: pd.DataFrame,
        baseline_snapshot: DriftMonitoringSnapshotDocument | None,
        created_at,
    ) -> DriftMonitoringSnapshotDocument:
        feature_stats = self._build_feature_stats(feature_frame, baseline_snapshot)
        prediction_distribution = self._build_prediction_distribution(prediction_frame)
        alerts = self._build_alerts(
            feature_stats,
            prediction_distribution,
            baseline_snapshot,
            sample_size=int(len(feature_frame)),
        )

        snapshot = DriftMonitoringSnapshotDocument(
            id=snapshot_id,
            model_version=model_version,
            source=source,
            request_id=request_id,
            sample_size=int(len(feature_frame)),
            feature_stats=feature_stats,
            prediction_distribution=prediction_distribution,
            alerts=alerts,
            reference_snapshot_id=baseline_snapshot.id if baseline_snapshot else None,
            created_at=created_at,
        )
        self.logger.info(
            "Captured %s drift snapshot for model_version=%s sample_size=%s",
            source,
            model_version,
            len(feature_frame),
        )
        return snapshot

    def _build_feature_stats(
        self,
        feature_frame: pd.DataFrame,
        baseline_snapshot: DriftMonitoringSnapshotDocument | None,
    ) -> dict[str, FeatureDistributionStats]:
        stats: dict[str, FeatureDistributionStats] = {}

        for column in feature_frame.columns:
            series = feature_frame[column].dropna()
            baseline_feature = (
                baseline_snapshot.feature_stats.get(column) if baseline_snapshot else None
            )

            if pd.api.types.is_numeric_dtype(series):
                stats[column] = self._numeric_stats(series.astype(float), baseline_feature)
            else:
                stats[column] = self._categorical_stats(series.astype(str), baseline_feature)

        return stats

    def _numeric_stats(
        self,
        series: pd.Series,
        baseline_feature: FeatureDistributionStats | None,
    ) -> FeatureDistributionStats:
        quantiles = {
            "q05": float(series.quantile(0.05)),
            "q25": float(series.quantile(0.25)),
            "q50": float(series.quantile(0.50)),
            "q75": float(series.quantile(0.75)),
            "q95": float(series.quantile(0.95)),
        }

        if baseline_feature and baseline_feature.bin_edges:
            bin_edges = baseline_feature.bin_edges
        else:
            candidate_edges = sorted(
                {
                    float(series.min()),
                    quantiles["q05"],
                    quantiles["q25"],
                    quantiles["q50"],
                    quantiles["q75"],
                    quantiles["q95"],
                    float(series.max()),
                }
            )
            if len(candidate_edges) == 1:
                candidate_edges = [candidate_edges[0], candidate_edges[0] + 1.0]
            bin_edges = candidate_edges

        counts, edges = np.histogram(series, bins=bin_edges)
        distribution = _normalize_distribution(
            {f"bin_{idx}": float(count) for idx, count in enumerate(counts.tolist())}
        )
        psi_value = None
        if baseline_feature and baseline_feature.bin_distribution:
            psi_value = _psi(baseline_feature.bin_distribution, distribution)

        return FeatureDistributionStats(
            feature_type="numeric",
            mean=float(series.mean()),
            std=float(series.std(ddof=0)),
            min=float(series.min()),
            max=float(series.max()),
            quantiles=quantiles,
            bin_edges=[float(edge) for edge in edges.tolist()],
            bin_distribution=distribution,
            psi_vs_baseline=psi_value,
        )

    def _categorical_stats(
        self,
        series: pd.Series,
        baseline_feature: FeatureDistributionStats | None,
    ) -> FeatureDistributionStats:
        distribution = _normalize_distribution(
            {str(key): float(value) for key, value in series.value_counts(dropna=False).items()}
        )
        psi_value = None
        if baseline_feature and baseline_feature.category_distribution:
            psi_value = _psi(baseline_feature.category_distribution, distribution)

        return FeatureDistributionStats(
            feature_type="categorical",
            category_distribution=distribution,
            psi_vs_baseline=psi_value,
        )

    def _build_prediction_distribution(
        self,
        prediction_frame: pd.DataFrame,
    ) -> PredictionDistributionStats:
        probability_series = prediction_frame["prob_disease"].astype(float)
        tier_distribution = _normalize_distribution(
            {
                str(key): float(value)
                for key, value in prediction_frame["confidence_tier"].value_counts().items()
            }
        )
        label_distribution = _normalize_distribution(
            {
                str(key): float(value)
                for key, value in prediction_frame["prediction"].value_counts().items()
            }
        )
        return PredictionDistributionStats(
            positive_rate=float((prediction_frame["prediction"] == 1).mean()),
            mean_probability=float(probability_series.mean()),
            std_probability=float(probability_series.std(ddof=0)),
            mean_confidence=float(prediction_frame["confidence_score"].astype(float).mean()),
            tier_distribution=tier_distribution,
            label_distribution=label_distribution,
        )

    def _build_alerts(
        self,
        feature_stats: dict[str, FeatureDistributionStats],
        prediction_distribution: PredictionDistributionStats,
        baseline_snapshot: DriftMonitoringSnapshotDocument | None,
        sample_size: int,
    ) -> list[DriftAlert]:
        alerts: list[DriftAlert] = []

        if baseline_snapshot is None:
            return alerts

        if sample_size < self.settings.drift_min_sample_size:
            return [
                DriftAlert(
                    name="insufficient_sample_size",
                    triggered=False,
                    observed_value=float(sample_size),
                    threshold=float(self.settings.drift_min_sample_size),
                    message="Snapshot stored without drift alerting because the sample is too small.",
                )
            ]

        for feature_name, stats in feature_stats.items():
            if stats.psi_vs_baseline is None:
                continue
            alerts.append(
                DriftAlert(
                    name=f"feature_psi::{feature_name}",
                    triggered=stats.psi_vs_baseline >= self.settings.drift_feature_psi_threshold,
                    observed_value=float(stats.psi_vs_baseline),
                    threshold=self.settings.drift_feature_psi_threshold,
                    message=f"Feature PSI drift for {feature_name}",
                )
            )

        baseline_positive_rate = baseline_snapshot.prediction_distribution.positive_rate
        prediction_shift = abs(prediction_distribution.positive_rate - baseline_positive_rate)
        alerts.append(
            DriftAlert(
                name="prediction_positive_rate_shift",
                triggered=prediction_shift >= self.settings.drift_prediction_shift_threshold,
                observed_value=float(prediction_shift),
                threshold=self.settings.drift_prediction_shift_threshold,
                message="Prediction positive-rate shift versus baseline",
            )
        )

        return alerts
