"""Analytics service for grouped prediction summaries."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from src.repositories.base import PredictionRepository
from src.schemas.api import AnalyticsSummaryItem, AnalyticsSummaryResponse


def _normalize_start_date(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _normalize_end_date(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)


class AnalyticsService:
    """Build grouped analytics payloads for API consumers."""

    def __init__(self, predictions: PredictionRepository):
        self.predictions = predictions

    async def summarize_predictions(
        self,
        *,
        bucket: Literal["hour", "day", "month"],
        start_date: date | None,
        end_date: date | None,
        model_version: str | None,
    ) -> AnalyticsSummaryResponse:
        rows = await self.predictions.summarize(
            bucket=bucket,
            start_date=_normalize_start_date(start_date),
            end_date=_normalize_end_date(end_date),
            model_version=model_version,
        )
        return AnalyticsSummaryResponse(
            bucket=bucket,
            start_date=start_date,
            end_date=end_date,
            model_version=model_version,
            groups=[
                AnalyticsSummaryItem(
                    model_version=row.model_version,
                    date_bucket=row.date_bucket,
                    confidence_tier=row.confidence_tier,
                    total_predictions=row.total_predictions,
                    positive_predictions=row.positive_predictions,
                    negative_predictions=row.negative_predictions,
                    average_confidence_score=row.average_confidence_score,
                    average_probability=row.average_probability,
                )
                for row in rows
            ],
        )
