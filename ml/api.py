"""FastAPI application for production-grade CardioSense inference."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.exceptions import CardioSenseError
from src.core.logging_utils import REQUEST_ID_CTX, configure_logging, get_logger
from src.core.settings import get_settings
from src.core.utils import canonical_json_hash, new_document_id
from src.schemas.api import (
    AllModelsMetricsResponse,
    AnalyticsSummaryResponse,
    AuthResponse,
    AuthUserProfile,
    BatchHeartDiseaseRequest,
    BatchPredictionResponse,
    EnsembleTrainingConfig,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    HeartDiseaseRequest,
    LoginRequest,
    ModelStepMetricsItem,
    ModelVersionResponse,
    PredictionResponse,
    RollbackRequest,
    SignupRequest,
)
from src.services.analytics_service import AnalyticsService
from src.services.auth_service import AuthService
from src.services.container import ApplicationContainer, build_container
from src.services.model_registry import ModelRegistryService
from src.services.prediction_service import InferenceRequestContext, PredictionService

LOGGER = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helper: step-key → display names
# ---------------------------------------------------------------------------
_STEP_NAME_MAP: dict[str, tuple[str, str]] = {
    # current best_model.py naming
    "step1_xgb_calibrated": ("XGBoost", "XGBoost Calibrated"),
    "step1_lgbm_calibrated": ("LightGBM", "LightGBM Calibrated"),
    "step1_rf_calibrated": ("Random Forest", "Random Forest Calibrated"),
    "step2_soft_voting_calibrated": ("Soft Voting", "Soft Voting Ensemble"),
    "step3_stacking_calibrated": ("Stacking", "Stacking Ensemble"),
    # legacy naming found in older saved JSON files
    "xgb_cal": ("XGBoost", "XGBoost Calibrated"),
    "lgbm_cal": ("LightGBM", "LightGBM Calibrated"),
    "rf_cal": ("Random Forest", "Random Forest Calibrated"),
    "soft_voting": ("Soft Voting", "Soft Voting Ensemble"),
    "stacking": ("Stacking", "Stacking Ensemble"),
}

_DISPLAY_ORDER = [
    "XGBoost",
    "LightGBM",
    "Random Forest",
    "Soft Voting",
    "Stacking",
]


def _build_all_models_metrics() -> AllModelsMetricsResponse:
    """Read best_ensemble_metrics.json + best_ensemble_summary.json and build response."""
    from config import RESULTS_DIR  # local import to avoid circular deps at module load

    metrics_path: Path = RESULTS_DIR / "best_ensemble_metrics.json"
    summary_path: Path = RESULTS_DIR / "best_ensemble_summary.json"

    if not metrics_path.exists():
        raise FileNotFoundError(f"Model metrics file not found: {metrics_path}")

    with open(metrics_path, "r", encoding="utf-8") as fh:
        metrics_raw: dict[str, Any] = json.load(fh)

    selected_model_key: str = ""
    selected_threshold: float = 0.5
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as fh:
            summary_raw: dict[str, Any] = json.load(fh)
        selected_model_key = str(summary_raw.get("selected_model", ""))
        selected_threshold = float(
            summary_raw.get("selected_threshold", summary_raw.get("best_metrics", {}).get("threshold", 0.5))
        )

    cfg_raw: dict[str, Any] = metrics_raw.get("config", {})
    config = EnsembleTrainingConfig(
        calibration_method=str(cfg_raw.get("calibration_method", "sigmoid")),
        random_state=int(cfg_raw.get("random_state", 42)),
        target_recall=float(cfg_raw.get("target_recall", 0.83)),
        target_accuracy=float(cfg_raw.get("target_accuracy", 0.78)),
        precision_floor=float(cfg_raw.get("precision_floor", 0.72)),
    )

    steps_raw: dict[str, Any] = metrics_raw.get("steps", {})
    items: list[ModelStepMetricsItem] = []
    for key, step in steps_raw.items():
        name, full_name = _STEP_NAME_MAP.get(key, (key, key))
        cr = step.get("classification_report", {})
        disease_cr = cr.get("1", cr.get("Disease", {}))
        f1_score = float(disease_cr.get("f1-score", step.get("f1", 0.0)))
        items.append(
            ModelStepMetricsItem(
                key=key,
                name=name,
                full_name=full_name,
                is_selected=key == selected_model_key,
                threshold=float(step.get("threshold", 0.5)),
                accuracy=float(step.get("accuracy", 0.0)),
                precision=float(step.get("precision", 0.0)),
                recall=float(step.get("recall", 0.0)),
                f1=f1_score,
                roc_auc=float(step.get("roc_auc", 0.0)),
                pr_auc=float(step.get("pr_auc", 0.0)),
                fnr=float(step.get("fnr", 0.0)),
            )
        )

    # Sort by predefined display order; unknown models go last.
    def _sort_key(item: ModelStepMetricsItem) -> int:
        try:
            return _DISPLAY_ORDER.index(item.name)
        except ValueError:
            return len(_DISPLAY_ORDER)

    items.sort(key=_sort_key)

    selected_display = _STEP_NAME_MAP.get(selected_model_key, (selected_model_key, ""))[0]

    return AllModelsMetricsResponse(
        selected_model=selected_display or selected_model_key,
        selected_threshold=selected_threshold,
        config=config,
        models=items,
    )


def _format_model_version_response(model_version) -> ModelVersionResponse:
    return ModelVersionResponse(
        model_version=model_version.id,
        model_name=model_version.model_name,
        is_active=model_version.is_active,
        threshold_used=model_version.threshold_used,
        threshold_objective=model_version.threshold_objective,
        created_at=model_version.created_at,
        activated_at=model_version.activated_at,
        metrics={
            "validation": model_version.validation_metrics.model_dump(mode="json"),
            "test": model_version.test_metrics.model_dump(mode="json"),
        },
    )


def _build_context(request: Request, payload: Any) -> InferenceRequestContext:
    request_id = request.headers.get("X-Request-ID", new_document_id("request"))
    REQUEST_ID_CTX.set(request_id)
    return InferenceRequestContext(
        request_id=request_id,
        route=request.url.path,
        method=request.method,
        payload_hash=canonical_json_hash(payload),
        idempotency_key=request.headers.get("X-Idempotency-Key"),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        content_length=int(request.headers["content-length"])
        if request.headers.get("content-length")
        else None,
    )


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container


def get_prediction_service(
    container: ApplicationContainer = Depends(get_container),
) -> PredictionService:
    return container.prediction_service


def get_auth_service(
    container: ApplicationContainer = Depends(get_container),
) -> AuthService:
    return container.auth_service


def get_model_registry(
    container: ApplicationContainer = Depends(get_container),
) -> ModelRegistryService:
    return container.model_registry


def get_analytics_service(
    container: ApplicationContainer = Depends(get_container),
) -> AnalyticsService:
    return container.analytics_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    container = build_container(settings)
    app.state.container = container
    LOGGER.info("Starting CardioSense app with db_backend=%s", settings.db_backend)
    await container.initialize()
    try:
        try:
            await container.model_registry.get_active_runtime()
        except Exception as exc:
            LOGGER.warning("Active model was not ready during startup: %s", exc)
        yield
    finally:
        await container.close()
        LOGGER.info("CardioSense shutdown complete.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="CardioSense Production Inference API",
        description="Async MongoDB-backed heart disease inference service with model registry and drift monitoring.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Input validation failed.",
                "errors": exc.errors(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(CardioSenseError)
    async def domain_exception_handler(request: Request, exc: CardioSenseError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, "path": str(request.url.path)},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        LOGGER.exception("Unhandled exception for path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Unexpected server error.", "path": str(request.url.path)},
        )

    @app.get("/health", response_model=HealthResponse)
    async def health(
        container: ApplicationContainer = Depends(get_container),
    ) -> HealthResponse:
        db_ready = await container.repositories.ping()
        active_version = None
        status = "loading"
        try:
            active_version = (await container.model_registry.get_active_model_version()).id
            status = "ready" if db_ready else "degraded"
        except Exception:
            status = "degraded" if db_ready else "loading"

        return HealthResponse(
            status=status,
            db_backend=container.repositories.backend_name,
            db_ready=db_ready,
            active_model_version=active_version,
            startup_warnings=list(container.repositories.startup_warnings),
        )

    @app.post("/predict", response_model=PredictionResponse)
    async def predict(
        request_model: HeartDiseaseRequest,
        request: Request,
        prediction_service: PredictionService = Depends(get_prediction_service),
    ) -> PredictionResponse:
        payload = request_model.model_dump()
        context = _build_context(request, payload)
        return await prediction_service.predict_single(payload, context)

    @app.post("/predict/batch", response_model=BatchPredictionResponse)
    async def predict_batch(
        request_model: BatchHeartDiseaseRequest,
        request: Request,
        prediction_service: PredictionService = Depends(get_prediction_service),
    ) -> BatchPredictionResponse:
        payload = [record.model_dump() for record in request_model.records]
        context = _build_context(request, payload)
        return await prediction_service.predict_batch(payload, context)

    @app.post("/feedback", response_model=FeedbackResponse)
    async def submit_feedback(
        request_model: FeedbackRequest,
        request: Request,
        prediction_service: PredictionService = Depends(get_prediction_service),
    ) -> FeedbackResponse:
        payload = request_model.model_dump()
        context = _build_context(request, payload)
        return await prediction_service.attach_feedback(
            prediction_id=request_model.prediction_id,
            true_label=request_model.true_label,
            label_source=request_model.label_source,
            reviewer=request_model.reviewer,
            notes=request_model.notes,
            context=context,
        )

    @app.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
    async def analytics_summary(
        bucket: Literal["hour", "day", "month"] = Query("day"),
        start_date: date | None = Query(None),
        end_date: date | None = Query(None),
        model_version: str | None = Query(None),
        analytics_service: AnalyticsService = Depends(get_analytics_service),
    ) -> AnalyticsSummaryResponse:
        return await analytics_service.summarize_predictions(
            bucket=bucket,
            start_date=start_date,
            end_date=end_date,
            model_version=model_version,
        )

    @app.post("/auth/signup", response_model=AuthResponse)
    async def signup_user(
        request_model: SignupRequest,
        auth_service: AuthService = Depends(get_auth_service),
    ) -> AuthResponse:
        result = await auth_service.signup(
            full_name=request_model.full_name,
            email=request_model.email,
            password=request_model.password,
            role=request_model.role,
        )
        return AuthResponse(
            message=result.message,
            access_token=result.access_token,
            token_type=result.token_type,
            user=AuthUserProfile(
                user_id=result.user.id,
                full_name=result.user.full_name,
                email=result.user.email,
                role=result.user.role,
                created_at=result.user.created_at,
                last_login_at=result.user.last_login_at,
            ),
        )

    @app.post("/auth/login", response_model=AuthResponse)
    async def login_user(
        request_model: LoginRequest,
        auth_service: AuthService = Depends(get_auth_service),
    ) -> AuthResponse:
        result = await auth_service.login(
            email=request_model.email,
            password=request_model.password,
        )
        return AuthResponse(
            message=result.message,
            access_token=result.access_token,
            token_type=result.token_type,
            user=AuthUserProfile(
                user_id=result.user.id,
                full_name=result.user.full_name,
                email=result.user.email,
                role=result.user.role,
                created_at=result.user.created_at,
                last_login_at=result.user.last_login_at,
            ),
        )

    @app.get("/models/active", response_model=ModelVersionResponse)
    async def get_active_model(
        model_registry: ModelRegistryService = Depends(get_model_registry),
    ) -> ModelVersionResponse:
        return _format_model_version_response(await model_registry.get_active_model_version())

    @app.post("/models/rollback", response_model=ModelVersionResponse)
    async def rollback_model(
        request_model: RollbackRequest,
        model_registry: ModelRegistryService = Depends(get_model_registry),
    ) -> ModelVersionResponse:
        model_version = await model_registry.rollback(request_model.target_version)
        return _format_model_version_response(model_version)

    @app.get("/models/metrics", response_model=AllModelsMetricsResponse)
    async def get_all_models_metrics() -> AllModelsMetricsResponse:
        """Return metrics for all trained models (XGB, LGBM, RF, Soft Voting, Stacking)."""
        try:
            return _build_all_models_metrics()
        except FileNotFoundError as exc:
            return JSONResponse(
                status_code=404,
                content={"detail": str(exc)},
            )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "message": "CardioSense inference API is running.",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
