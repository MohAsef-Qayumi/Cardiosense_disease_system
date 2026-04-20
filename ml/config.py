"""
Centralized configuration for the heart disease pipeline.
"""

import os
import random
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import numpy as np

# Thread caps for deterministic and sandbox-safe execution.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


def _ensure_writable_dir(primary: Path, fallback: Path) -> Path:
    """
    Return primary directory when writable; otherwise return fallback directory.
    """
    for candidate in (primary, fallback):
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    raise PermissionError(f"No writable directory available: {primary} or {fallback}")


# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATASET_PATH = DATA_RAW_DIR / "cardio_train.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Output/artifact paths (auto-fallback to writable location when needed)
ARTIFACTS_FALLBACK_DIR = DATA_PROCESSED_DIR / "artifacts"
MODELS_DIR = _ensure_writable_dir(
    PROJECT_ROOT / "outputs" / "models",
    ARTIFACTS_FALLBACK_DIR / "models",
)
RESULTS_DIR = _ensure_writable_dir(
    PROJECT_ROOT / "outputs" / "results",
    ARTIFACTS_FALLBACK_DIR / "results",
)
EDA_PLOTS_DIR = _ensure_writable_dir(
    PROJECT_ROOT / "outputs" / "eda_plots",
    ARTIFACTS_FALLBACK_DIR / "eda_plots",
)
PLOTS_DIR = _ensure_writable_dir(
    PROJECT_ROOT / "plots",
    ARTIFACTS_FALLBACK_DIR / "plots",
)
OUTPUT_DIR = MODELS_DIR.parent

# Model artifacts
PREPROCESSING_PIPELINE_PATH = MODELS_DIR / "preprocessing_pipeline.pkl"
TRAINED_MODEL_PATH = MODELS_DIR / "xgboost_confidence_service.pkl"
BEST_MODEL_PATH = TRAINED_MODEL_PATH

# Plot outputs
PLOT_TARGET_DIST = PLOTS_DIR / "01_target_distribution.png"
PLOT_CORR_HEATMAP = PLOTS_DIR / "02_correlation_heatmap.png"
PLOT_FEATURE_DIST = PLOTS_DIR / "03_feature_distributions.png"
PLOT_AGE_THALACH = PLOTS_DIR / "04_age_vs_thalach.png"
PLOT_EVALUATION = PLOTS_DIR / "05_model_evaluation.png"

# Train/validation split
RANDOM_STATE = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.1

# Global reproducibility
GLOBAL_SEED = 42


def set_global_seed(seed: int = GLOBAL_SEED):
    """Set global random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


# Single model: XGBoost
MODEL_NAME = "XGBoost"
XGB_N_ESTIMATORS = 1200
XGB_MAX_DEPTH = 3
XGB_LEARNING_RATE = 0.03
XGB_SUBSAMPLE = 0.85
XGB_COLSAMPLE_BYTREE = 0.9
XGB_MIN_CHILD_WEIGHT = 1
XGB_GAMMA = 0.1
XGB_REG_ALPHA = 0.1
XGB_REG_LAMBDA = 1.5
XGB_EARLY_STOPPING_ROUNDS = 50

XGB_MODEL_PARAMS = {
    "n_estimators": XGB_N_ESTIMATORS,
    "max_depth": XGB_MAX_DEPTH,
    "learning_rate": XGB_LEARNING_RATE,
    "subsample": XGB_SUBSAMPLE,
    "colsample_bytree": XGB_COLSAMPLE_BYTREE,
    "min_child_weight": XGB_MIN_CHILD_WEIGHT,
    "gamma": XGB_GAMMA,
    "reg_alpha": XGB_REG_ALPHA,
    "reg_lambda": XGB_REG_LAMBDA,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "random_state": RANDOM_STATE,
    "n_jobs": 1,
    "tree_method": "hist",
    "early_stopping_rounds": XGB_EARLY_STOPPING_ROUNDS,
}

# Preprocessing parameters
OUTLIER_FACTOR = 1.5
OUTLIER_COLS = ["ap_hi", "ap_lo", "weight", "height", "age"]
ENABLE_OUTLIER_CLIPPING = False
NUMERIC_IMPUTE_STRATEGY = "median"
CATEGORICAL_IMPUTE_STRATEGY = "most_frequent"

# Clinical plausibility filtering
ENABLE_PLAUSIBILITY_FILTER = True
AP_HI_RANGE = (80, 240)
AP_LO_RANGE = (40, 160)
HEIGHT_RANGE = (120, 220)
WEIGHT_RANGE = (30, 220)

# Confidence tiers
CONFIDENCE_HIGH_THRESHOLD = 0.75
CONFIDENCE_MEDIUM_THRESHOLD = 0.55
OPTIMIZE_DECISION_THRESHOLD = os.getenv(
    "CARDIOSENSE_ENABLE_THRESHOLD_OPTIMIZATION",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
THRESHOLD_OPTIMIZATION_OBJECTIVE = os.getenv(
    "CARDIOSENSE_THRESHOLD_OPTIMIZATION_OBJECTIVE",
    "balanced_accuracy",
).strip().lower()
THRESHOLD_SEARCH_START = float(os.getenv("CARDIOSENSE_THRESHOLD_SEARCH_START", "0.30"))
THRESHOLD_SEARCH_END = float(os.getenv("CARDIOSENSE_THRESHOLD_SEARCH_END", "0.70"))
THRESHOLD_SEARCH_STEP = float(os.getenv("CARDIOSENSE_THRESHOLD_SEARCH_STEP", "0.01"))

# Probability calibration toggle
USE_PROBABILITY_CALIBRATION = False

# Dataset
TARGET_COLUMN = "cardio"

# Result artifacts
MODEL_METRICS_CSV = RESULTS_DIR / "xgboost_metrics.csv"
MODEL_METRICS_JSON = RESULTS_DIR / "xgboost_metrics.json"
ERROR_ANALYSIS_CSV = RESULTS_DIR / "error_analysis_misclassified.csv"
ERROR_SUMMARY_JSON = RESULTS_DIR / "error_analysis_summary.json"

# Logging
VERBOSE = True
