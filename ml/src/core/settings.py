"""Environment-driven runtime settings for CardioSense."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from config import MODEL_METRICS_JSON, PREPROCESSING_PIPELINE_PATH, TRAINED_MODEL_PATH


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int | None) -> int | None:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _get_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items if items else default


@dataclass(frozen=True)
class Settings:
    """Operational settings loaded from environment variables."""

    app_name: str
    app_version: str
    db_backend: str
    mongodb_uri: str
    mongodb_password: str | None
    mongodb_database: str
    mongodb_min_pool_size: int
    mongodb_max_pool_size: int
    mongodb_max_idle_time_ms: int
    mongodb_connect_timeout_ms: int | None
    mongodb_server_selection_timeout_ms: int | None
    mongodb_socket_timeout_ms: int | None
    mongodb_wait_queue_timeout_ms: int | None
    mongodb_index_build_timeout_ms: int | None
    cors_allow_origins: tuple[str, ...]
    log_level: str
    log_payloads: bool
    request_body_max_chars: int
    hash_salt: str
    drift_feature_psi_threshold: float
    drift_prediction_shift_threshold: float
    drift_min_sample_size: int
    enable_threshold_optimization: bool
    threshold_optimization_objective: str
    bootstrap_local_model: bool
    artifact_model_path: Path
    artifact_preprocessing_path: Path
    artifact_metrics_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings(
        app_name="CardioSense",
        app_version="2.1.0",
        db_backend=os.getenv("CARDIOSENSE_DB_BACKEND", "mongodb").strip().lower(),
        mongodb_uri=os.getenv("CARDIOSENSE_MONGODB_URI", "mongodb://127.0.0.1:27017"),
        mongodb_password=os.getenv("CARDIOSENSE_MONGODB_PASSWORD"),
        mongodb_database=os.getenv("CARDIOSENSE_MONGODB_DATABASE", "cardiosense"),
        mongodb_min_pool_size=_get_int("CARDIOSENSE_MONGODB_MIN_POOL_SIZE", 1),
        mongodb_max_pool_size=_get_int("CARDIOSENSE_MONGODB_MAX_POOL_SIZE", 20),
        mongodb_max_idle_time_ms=_get_int("CARDIOSENSE_MONGODB_MAX_IDLE_TIME_MS", 60000),
        mongodb_connect_timeout_ms=_get_int("CARDIOSENSE_MONGODB_CONNECT_TIMEOUT_MS", 30000),
        mongodb_server_selection_timeout_ms=_get_int(
            "CARDIOSENSE_MONGODB_SERVER_SELECTION_TIMEOUT_MS",
            30000,
        ),
        mongodb_socket_timeout_ms=_get_int("CARDIOSENSE_MONGODB_SOCKET_TIMEOUT_MS", 30000),
        mongodb_wait_queue_timeout_ms=_get_int(
            "CARDIOSENSE_MONGODB_WAIT_QUEUE_TIMEOUT_MS",
            30000,
        ),
        mongodb_index_build_timeout_ms=_get_int(
            "CARDIOSENSE_MONGODB_INDEX_BUILD_TIMEOUT_MS",
            30000,
        ),
        cors_allow_origins=_get_csv(
            "CARDIOSENSE_CORS_ALLOW_ORIGINS",
            (
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "null",
            ),
        ),
        log_level=os.getenv("CARDIOSENSE_LOG_LEVEL", "INFO").upper(),
        log_payloads=_get_bool("CARDIOSENSE_LOG_PAYLOADS", False),
        request_body_max_chars=_get_int("CARDIOSENSE_REQUEST_BODY_MAX_CHARS", 2048),
        hash_salt=os.getenv("CARDIOSENSE_HASH_SALT", "cardiosense-local-salt"),
        drift_feature_psi_threshold=_get_float("CARDIOSENSE_DRIFT_FEATURE_PSI_THRESHOLD", 0.2),
        drift_prediction_shift_threshold=_get_float(
            "CARDIOSENSE_DRIFT_PREDICTION_SHIFT_THRESHOLD",
            0.15,
        ),
        drift_min_sample_size=_get_int("CARDIOSENSE_DRIFT_MIN_SAMPLE_SIZE", 25),
        enable_threshold_optimization=_get_bool(
            "CARDIOSENSE_ENABLE_THRESHOLD_OPTIMIZATION",
            True,
        ),
        threshold_optimization_objective=os.getenv(
            "CARDIOSENSE_THRESHOLD_OPTIMIZATION_OBJECTIVE",
            "balanced_accuracy",
        ).strip().lower(),
        bootstrap_local_model=_get_bool("CARDIOSENSE_BOOTSTRAP_LOCAL_MODEL", True),
        artifact_model_path=TRAINED_MODEL_PATH,
        artifact_preprocessing_path=PREPROCESSING_PIPELINE_PATH,
        artifact_metrics_path=MODEL_METRICS_JSON,
    )
