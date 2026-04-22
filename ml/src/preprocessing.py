"""
Preprocessing utilities for the heart disease pipeline.
"""

from datetime import datetime
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    AP_HI_RANGE,
    AP_LO_RANGE,
    CATEGORICAL_IMPUTE_STRATEGY,
    ENABLE_OUTLIER_CLIPPING,
    ENABLE_PLAUSIBILITY_FILTER,
    HEIGHT_RANGE,
    MODELS_DIR,
    NUMERIC_IMPUTE_STRATEGY,
    OUTLIER_COLS,
    OUTLIER_FACTOR,
    PREPROCESSING_PIPELINE_PATH,
    TARGET_COLUMN,
    WEIGHT_RANGE,
)


def _safe_joblib_dump(obj, path: Path) -> Path:
    """Save an artifact; fallback to a timestamped filename if target is locked."""
    try:
        joblib.dump(obj, str(path))
        return path
    except PermissionError:
        fallback = path.with_name(
            f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}"
        )
        joblib.dump(obj, str(fallback))
        print(f"  [WARN] Could not overwrite {path.name}; saved {fallback.name} instead.")
        return fallback


def filter_clinically_implausible_rows(
    df: pd.DataFrame, target_col: str = TARGET_COLUMN
):
    """
    Remove obviously implausible physiological readings.
    """
    if not ENABLE_PLAUSIBILITY_FILTER:
        return df.copy(), {"enabled": False, "dropped_rows": 0, "kept_rows": len(df)}

    required_cols = {"ap_hi", "ap_lo", "height", "weight"}
    if not required_cols.issubset(df.columns):
        return df.copy(), {
            "enabled": True,
            "dropped_rows": 0,
            "kept_rows": len(df),
            "warning": "Missing vitals columns; plausibility filter skipped.",
        }

    mask = (
        (df["ap_hi"] > df["ap_lo"])
        & df["ap_hi"].between(AP_HI_RANGE[0], AP_HI_RANGE[1])
        & df["ap_lo"].between(AP_LO_RANGE[0], AP_LO_RANGE[1])
        & df["height"].between(HEIGHT_RANGE[0], HEIGHT_RANGE[1])
        & df["weight"].between(WEIGHT_RANGE[0], WEIGHT_RANGE[1])
    )
    filtered = df.loc[mask].copy()
    stats = {
        "enabled": True,
        "dropped_rows": int((~mask).sum()),
        "kept_rows": int(mask.sum()),
        "drop_rate": float((~mask).mean()),
        "target_distribution_before": df[target_col].value_counts(normalize=True).to_dict()
        if target_col in df.columns
        else {},
        "target_distribution_after": filtered[target_col].value_counts(normalize=True).to_dict()
        if target_col in filtered.columns
        else {},
    }
    return filtered, stats


class MissingValueHandler(BaseEstimator, TransformerMixin):
    """Impute missing values for numeric and categorical features."""

    def __init__(self, numeric_strategy="median", categorical_strategy="most_frequent"):
        self.numeric_strategy = numeric_strategy
        self.categorical_strategy = categorical_strategy
        self.numeric_cols_ = []
        self.categorical_cols_ = []
        self.imputers_ = {}

    def fit(self, X, y=None):
        self.numeric_cols_ = X.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols_ = X.select_dtypes(exclude=[np.number]).columns.tolist()

        if self.numeric_cols_:
            num_imputer = SimpleImputer(strategy=self.numeric_strategy)
            num_imputer.fit(X[self.numeric_cols_])
            self.imputers_["numeric"] = num_imputer

        if self.categorical_cols_:
            cat_imputer = SimpleImputer(strategy=self.categorical_strategy)
            cat_imputer.fit(X[self.categorical_cols_])
            self.imputers_["categorical"] = cat_imputer
        return self

    def transform(self, X):
        X = X.copy()
        if self.numeric_cols_:
            numeric_imputer = self.imputers_["numeric"]
            self._ensure_imputer_runtime_state(numeric_imputer)
            X[self.numeric_cols_] = numeric_imputer.transform(X[self.numeric_cols_])
        if self.categorical_cols_:
            categorical_imputer = self.imputers_["categorical"]
            self._ensure_imputer_runtime_state(categorical_imputer)
            X[self.categorical_cols_] = categorical_imputer.transform(X[self.categorical_cols_])
        print(f"  [MissingValueHandler] Imputed {X.isnull().sum().sum()} remaining nulls after transform.")
        return X

    @staticmethod
    def _ensure_imputer_runtime_state(imputer) -> None:
        # Compatibility shim for pipelines serialized on older sklearn versions.
        if hasattr(imputer, "_fit_dtype") and not hasattr(imputer, "_fill_dtype"):
            imputer._fill_dtype = imputer._fit_dtype


class OutlierHandler(BaseEstimator, TransformerMixin):
    """Clip outliers via IQR winsorization."""

    def __init__(self, cols=None, factor=1.5):
        self.cols = cols
        self.factor = factor
        self.bounds_ = {}

    def fit(self, X, y=None):
        if self.cols:
            target_cols = [c for c in self.cols if c in X.columns]
        else:
            target_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        for col in target_cols:
            q1 = X[col].quantile(0.25)
            q3 = X[col].quantile(0.75)
            iqr = q3 - q1
            self.bounds_[col] = (q1 - self.factor * iqr, q3 + self.factor * iqr)
        return self

    def transform(self, X):
        X = X.copy()
        clipped = 0
        for col, (lower, upper) in self.bounds_.items():
            if col in X.columns:
                before = ((X[col] < lower) | (X[col] > upper)).sum()
                X[col] = X[col].clip(lower, upper)
                clipped += int(before)
        print(f"  [OutlierHandler] Clipped {clipped} outlier values.")
        return X


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Create domain-driven features for cardiovascular risk prediction."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()

        if "id" in X.columns:
            X = X.drop(columns=["id"])

        if "age" in X.columns:
            X["age_years"] = X["age"] / 365.25
            X["age_risk"] = (X["age_years"] >= 55).astype(int)

        if "height" in X.columns and "weight" in X.columns:
            height_m = X["height"] / 100.0
            X["bmi"] = X["weight"] / np.clip(height_m ** 2, 1e-6, None)
            X["bmi_obese"] = (X["bmi"] >= 30).astype(int)
            X["bmi_underweight"] = (X["bmi"] < 18.5).astype(int)
            X["bmi_overweight"] = ((X["bmi"] >= 25) & (X["bmi"] < 30)).astype(int)

        if "ap_hi" in X.columns and "ap_lo" in X.columns:
            X["pulse_pressure"] = X["ap_hi"] - X["ap_lo"]
            X["mean_arterial_pressure"] = (X["ap_hi"] + 2 * X["ap_lo"]) / 3.0
            X["hypertension_stage2"] = ((X["ap_hi"] >= 140) | (X["ap_lo"] >= 90)).astype(int)
            safe_ap_lo = X["ap_lo"].replace(0, np.nan)
            X["ap_ratio"] = (X["ap_hi"] / safe_ap_lo).replace([np.inf, -np.inf], np.nan).fillna(1.0)

        if "cholesterol" in X.columns:
            X["chol_ge2"] = (X["cholesterol"] >= 2).astype(int)
            X["chol_eq3"] = (X["cholesterol"] == 3).astype(int)

        if "gluc" in X.columns:
            X["gluc_ge2"] = (X["gluc"] >= 2).astype(int)
            X["gluc_eq3"] = (X["gluc"] == 3).astype(int)

        if {"cholesterol", "gluc"}.issubset(X.columns):
            X["metabolic_risk_score"] = (
                (X["cholesterol"] >= 2).astype(int) + (X["gluc"] >= 2).astype(int)
            )

        if "smoke" in X.columns and "alco" in X.columns:
            X["smoke_alco"] = (X["smoke"] * X["alco"]).astype(int)

        if "active" in X.columns:
            X["inactive"] = (1 - X["active"]).astype(int)

        if {"smoke", "alco", "active"}.issubset(X.columns):
            X["lifestyle_risk_score"] = X["smoke"] + X["alco"] + (1 - X["active"])

        if "age_years" in X.columns and "ap_hi" in X.columns:
            X["age_x_hi"] = X["age_years"] * X["ap_hi"]

        if "age_years" in X.columns and "ap_lo" in X.columns:
            X["age_x_lo"] = X["age_years"] * X["ap_lo"]

        if "bmi" in X.columns and "age_years" in X.columns:
            X["bmi_x_age"] = X["bmi"] * X["age_years"]

        print(f"  [FeatureEngineer] Features after engineering: {X.shape[1]}")
        return X


class FeatureScaler(BaseEstimator, TransformerMixin):
    """Scale numeric features."""

    def __init__(self, method="standard", exclude_cols=None):
        self.method = method
        self.exclude_cols = exclude_cols or []
        self.scaler_ = None
        self.scale_cols_ = []

    def fit(self, X, y=None):
        self.scale_cols_ = [
            c for c in X.select_dtypes(include=[np.number]).columns if c not in self.exclude_cols
        ]
        self.scaler_ = StandardScaler() if self.method == "standard" else MinMaxScaler()
        self.scaler_.fit(X[self.scale_cols_])
        return self

    def transform(self, X):
        X = X.copy()
        X[self.scale_cols_] = self.scaler_.transform(X[self.scale_cols_])
        print(f"  [FeatureScaler] Scaled {len(self.scale_cols_)} columns using '{self.method}' method.")
        return X


def build_preprocessing_pipeline(outlier_cols=None):
    """Build the preprocessing pipeline."""
    steps = [
        (
            "missing_handler",
            MissingValueHandler(
                numeric_strategy=NUMERIC_IMPUTE_STRATEGY,
                categorical_strategy=CATEGORICAL_IMPUTE_STRATEGY,
            ),
        ),
    ]
    if ENABLE_OUTLIER_CLIPPING:
        steps.append(("outlier_handler", OutlierHandler(cols=outlier_cols, factor=OUTLIER_FACTOR)))
    steps.extend(
        [
            ("feature_engineer", FeatureEngineer()),
            ("scaler", FeatureScaler(method="standard")),
        ]
    )
    return Pipeline(steps=steps)


def preprocess_data(df: pd.DataFrame, target_col=TARGET_COLUMN, save_pipeline=True):
    """
    Legacy helper: fit preprocessing on full dataset and return transformed X,y.
    """
    print("\n" + "=" * 60)
    print("PREPROCESSING PIPELINE")
    print("=" * 60)

    X = df.drop(columns=[target_col])
    y = df[target_col]
    print(f"\n[Step 0] Features: {X.shape[1]} | Samples: {X.shape[0]}")
    print(f"         Missing values before: {X.isnull().sum().sum()}")

    pipeline = build_preprocessing_pipeline(outlier_cols=OUTLIER_COLS)
    X_processed = pipeline.fit_transform(X)
    if not isinstance(X_processed, pd.DataFrame):
        X_processed = pd.DataFrame(X_processed, index=X.index)

    final_cols = X_processed.columns.tolist()
    print(f"\n[Done] Processed shape: {X_processed.shape}")
    print(f"       Final features: {final_cols}")

    if save_pipeline:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        saved_path = _safe_joblib_dump(pipeline, PREPROCESSING_PIPELINE_PATH)
        print(f"  [Pipeline saved] -> {saved_path}")

    return X_processed, y, pipeline, final_cols


def preprocess_splits(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    save_pipeline: bool = True,
):
    """
    Fit preprocessing on train only and transform val/test.
    """
    print("\n" + "=" * 60)
    print("LEAK-SAFE PREPROCESSING (FIT ON TRAIN ONLY)")
    print("=" * 60)

    pipeline = build_preprocessing_pipeline(outlier_cols=OUTLIER_COLS)
    X_train_processed = pipeline.fit_transform(X_train)
    X_val_processed = pipeline.transform(X_val)
    X_test_processed = pipeline.transform(X_test)

    if not isinstance(X_train_processed, pd.DataFrame):
        X_train_processed = pd.DataFrame(X_train_processed, index=X_train.index)
    if not isinstance(X_val_processed, pd.DataFrame):
        X_val_processed = pd.DataFrame(X_val_processed, index=X_val.index)
    if not isinstance(X_test_processed, pd.DataFrame):
        X_test_processed = pd.DataFrame(X_test_processed, index=X_test.index)

    feature_names = X_train_processed.columns.tolist()
    print(f"  [Preprocess] Train shape: {X_train_processed.shape}")
    print(f"  [Preprocess] Val shape:   {X_val_processed.shape}")
    print(f"  [Preprocess] Test shape:  {X_test_processed.shape}")

    if save_pipeline:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        saved_path = _safe_joblib_dump(pipeline, PREPROCESSING_PIPELINE_PATH)
        print(f"  [Pipeline saved] -> {saved_path}")

    return X_train_processed, X_val_processed, X_test_processed, pipeline, feature_names


if __name__ == "__main__":
    from src.data_loader import load_heart_disease_data

    df = load_heart_disease_data()
    X, y, _, cols = preprocess_data(df)
    print(f"\nFinal X shape: {X.shape}")
    print(f"Final features ({len(cols)}): {cols}")
    print(f"Target distribution:\n{y.value_counts()}")
