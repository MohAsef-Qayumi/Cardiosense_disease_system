"""XGBoost modeling and evaluation utilities for confidence-aware inference service."""

from datetime import datetime
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    precision_recall_fscore_support,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    ERROR_ANALYSIS_CSV,
    ERROR_SUMMARY_JSON,
    MODEL_METRICS_CSV,
    MODEL_METRICS_JSON,
    MODEL_NAME,
    MODELS_DIR,
    OPTIMIZE_DECISION_THRESHOLD,
    RESULTS_DIR,
    THRESHOLD_OPTIMIZATION_OBJECTIVE,
    THRESHOLD_SEARCH_END,
    THRESHOLD_SEARCH_START,
    THRESHOLD_SEARCH_STEP,
    TRAINED_MODEL_PATH,
    USE_PROBABILITY_CALIBRATION,
    XGB_MODEL_PARAMS,
)

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _with_timestamp(path: Path) -> Path:
    return path.with_name(f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}")


def _safe_joblib_dump(obj, path: Path) -> Path:
    try:
        joblib.dump(obj, str(path))
        return path
    except PermissionError:
        fallback = _with_timestamp(path)
        joblib.dump(obj, str(fallback))
        print(f"[WARN] Could not overwrite {path.name}; saved {fallback.name} instead.")
        return fallback


def _safe_save_json(path: Path, obj) -> Path:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        return path
    except PermissionError:
        fallback = _with_timestamp(path)
        with open(fallback, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        print(f"[WARN] Could not overwrite {path.name}; saved {fallback.name} instead.")
        return fallback


def _safe_save_csv(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_csv(path, index=False)
        return path
    except PermissionError:
        fallback = _with_timestamp(path)
        df.to_csv(fallback, index=False)
        print(f"[WARN] Could not overwrite {path.name}; saved {fallback.name} instead.")
        return fallback


class ConfidenceAwareInferenceService:
    """
    Wraps XGBoost to provide:
    1. Binary predictions
    2. Optional calibrated confidence scores
    3. Confidence tier: HIGH / MEDIUM / LOW
    """

    CONFIDENCE_TIERS = {
        "HIGH": (0.75, 1.00, "Model is confident, recommend clinical review"),
        "MEDIUM": (0.55, 0.75, "Moderate confidence, additional tests suggested"),
        "LOW": (0.50, 0.55, "Low confidence, human expert review needed"),
    }

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        model_params: dict | None = None,
        calibration_cv: int = 5,
        use_calibration: bool = USE_PROBABILITY_CALIBRATION,
    ):
        self.model_name = model_name
        self.model_params = model_params or {}
        self.calibration_cv = calibration_cv
        self.use_calibration = use_calibration
        self.calibrated_model = None
        self.fitted_estimator = None
        self.decision_threshold = 0.5
        self.threshold_optimization_summary = {
            "objective": THRESHOLD_OPTIMIZATION_OBJECTIVE,
            "threshold": 0.5,
            "score": 0.0,
            "evaluated_thresholds": 0,
        }
        self.is_fitted = False

    def _build_model(self):
        params = dict(XGB_MODEL_PARAMS)
        params.update(self.model_params)
        return XGBClassifier(**params)

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """Train model and optimize the decision threshold on validation data."""
        print(f"\n[Model] Training {self.model_name}...")
        pos_count = int((y_train == 1).sum())
        neg_count = int((y_train == 0).sum())
        auto_scale_pos_weight = (neg_count / pos_count) if pos_count > 0 else 1.0
        if "scale_pos_weight" not in self.model_params:
            self.model_params["scale_pos_weight"] = auto_scale_pos_weight
            print(
                f"[Model] Auto scale_pos_weight={auto_scale_pos_weight:.4f} "
                f"(neg={neg_count}, pos={pos_count})"
            )

        base_model = self._build_model()
        calibration_cv = StratifiedKFold(n_splits=self.calibration_cv, shuffle=True, random_state=42)

        if self.use_calibration:
            self.calibrated_model = CalibratedClassifierCV(base_model, method="sigmoid", cv=calibration_cv)
            self.calibrated_model.fit(X_train, y_train)
            self.fitted_estimator = self.calibrated_model
        else:
            fit_kwargs = {}
            if X_val is not None and y_val is not None:
                fit_kwargs["eval_set"] = [(X_val, y_val)]
                fit_kwargs["verbose"] = False
            base_model.fit(X_train, y_train, **fit_kwargs)
            self.calibrated_model = None
            self.fitted_estimator = base_model

        if OPTIMIZE_DECISION_THRESHOLD and X_val is not None and y_val is not None:
            val_probs = self.fitted_estimator.predict_proba(X_val)[:, 1]
            thresholds = np.arange(
                THRESHOLD_SEARCH_START,
                THRESHOLD_SEARCH_END + THRESHOLD_SEARCH_STEP,
                THRESHOLD_SEARCH_STEP,
            )
            best_t = 0.5
            best_score = -1.0
            for t in thresholds:
                val_preds = (val_probs >= t).astype(int)
                score = _threshold_objective_score(
                    THRESHOLD_OPTIMIZATION_OBJECTIVE,
                    y_val,
                    val_preds,
                    val_probs,
                )
                if score > best_score:
                    best_score = score
                    best_t = float(t)
            self.decision_threshold = best_t
            self.threshold_optimization_summary = {
                "objective": THRESHOLD_OPTIMIZATION_OBJECTIVE,
                "threshold": self.decision_threshold,
                "score": float(best_score),
                "evaluated_thresholds": int(len(thresholds)),
            }
            print(
                f"[Model] Optimized decision threshold={self.decision_threshold:.2f} "
                f"({THRESHOLD_OPTIMIZATION_OBJECTIVE}={best_score:.4f})"
            )
        else:
            self.decision_threshold = 0.5
            baseline_score = 0.0
            if X_val is not None and y_val is not None:
                val_probs = self.fitted_estimator.predict_proba(X_val)[:, 1]
                val_preds = (val_probs >= self.decision_threshold).astype(int)
                baseline_score = _threshold_objective_score(
                    THRESHOLD_OPTIMIZATION_OBJECTIVE,
                    y_val,
                    val_preds,
                    val_probs,
                )
            self.threshold_optimization_summary = {
                "objective": THRESHOLD_OPTIMIZATION_OBJECTIVE,
                "threshold": self.decision_threshold,
                "score": float(baseline_score),
                "evaluated_thresholds": 1,
            }
            print("[Model] Using fixed decision threshold=0.50 (production default).")

        self.is_fitted = True
        print("[Model] Training complete.")
        return self

    def predict(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction.")
        proba = self.fitted_estimator.predict_proba(X)[:, 1]
        return (proba >= self.decision_threshold).astype(int)

    def predict_proba(self, X):
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction.")
        return self.fitted_estimator.predict_proba(X)

    def predict_with_confidence(self, X):
        proba = self.predict_proba(X)
        preds = self.predict(X)
        confidence_scores = np.max(proba, axis=1)

        tiers = []
        for score in confidence_scores:
            if score >= CONFIDENCE_HIGH_THRESHOLD:
                tiers.append("HIGH")
            elif score >= CONFIDENCE_MEDIUM_THRESHOLD:
                tiers.append("MEDIUM")
            else:
                tiers.append("LOW")

        return pd.DataFrame(
            {
                "prediction": preds,
                "prob_no_disease": proba[:, 0].round(3),
                "prob_disease": proba[:, 1].round(3),
                "confidence_score": confidence_scores.round(3),
                "confidence_tier": tiers,
            }
        )

    def evaluate(self, X, y, split_name="Validation"):
        print(f"\n{'=' * 60}")
        print(f"EVALUATION - {split_name} Set")
        print(f"{'=' * 60}")

        preds = self.predict(X)
        proba = self.predict_proba(X)[:, 1]

        acc = accuracy_score(y, preds)
        prec = precision_score(y, preds, zero_division=0)
        rec = recall_score(y, preds, zero_division=0)
        f1 = f1_score(y, preds, zero_division=0)
        auc = roc_auc_score(y, proba)
        pr_auc = average_precision_score(y, proba)
        brier = brier_score_loss(y, proba)
        balanced_acc = balanced_accuracy_score(y, preds)
        mcc = matthews_corrcoef(y, preds)
        cm = confusion_matrix(y, preds, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        per_class_values = precision_recall_fscore_support(
            y,
            preds,
            labels=[0, 1],
            zero_division=0,
        )
        per_class = {
            "No Disease": {
                "precision": float(per_class_values[0][0]),
                "recall": float(per_class_values[1][0]),
                "f1": float(per_class_values[2][0]),
                "support": int(per_class_values[3][0]),
            },
            "Disease": {
                "precision": float(per_class_values[0][1]),
                "recall": float(per_class_values[1][1]),
                "f1": float(per_class_values[2][1]),
                "support": int(per_class_values[3][1]),
            },
        }

        metrics = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "specificity": specificity,
            "f1": f1,
            "roc_auc": auc,
            "pr_auc": pr_auc,
            "balanced_accuracy": balanced_acc,
            "mcc": mcc,
            "brier": brier,
            "per_class": per_class,
        }

        print(f"\n  Accuracy:    {acc:.4f}")
        print(f"  Precision:   {prec:.4f}")
        print(f"  Recall:      {rec:.4f}")
        print(f"  Specificity: {specificity:.4f}")
        print(f"  F1-Score:    {f1:.4f}")
        print(f"  ROC-AUC:     {auc:.4f}")
        print(f"  PR-AUC:      {pr_auc:.4f}")
        print(f"  Bal.Acc:     {balanced_acc:.4f}")
        print(f"  MCC:         {mcc:.4f}")
        print(f"  Brier:       {brier:.4f}")
        print(f"\n{classification_report(y, preds, target_names=['No Disease', 'Disease'])}")

        return metrics, cm

    def save(self, path=None):
        path_obj = Path(path) if path is not None else TRAINED_MODEL_PATH
        saved_path = _safe_joblib_dump(self, path_obj)
        print(f"[Model saved] -> {saved_path}")
        return saved_path


def train_xgboost_model(X_train, y_train, X_val, y_val, X_test, y_test):
    """Train a single XGBoost model and persist metrics artifacts."""
    print("\n" + "=" * 70)
    print("XGBOOST TRAINING")
    print("=" * 70)

    service = ConfidenceAwareInferenceService(model_name=MODEL_NAME, model_params=XGB_MODEL_PARAMS)
    service.fit(X_train, y_train, X_val=X_val, y_val=y_val)
    val_metrics, _ = service.evaluate(X_val, y_val, "Validation")
    test_metrics, _ = service.evaluate(X_test, y_test, "Test")

    metrics_row = {"model": MODEL_NAME}
    metrics_row.update({f"val_{k}": v for k, v in val_metrics.items() if k != "per_class"})
    metrics_row.update({f"test_{k}": v for k, v in test_metrics.items() if k != "per_class"})
    metrics_row["threshold_used"] = float(service.decision_threshold)
    metrics_row["threshold_objective"] = service.threshold_optimization_summary["objective"]
    metrics_df = pd.DataFrame([metrics_row])

    csv_path = _safe_save_csv(metrics_df, MODEL_METRICS_CSV)
    json_path = _safe_save_json(
        MODEL_METRICS_JSON,
        {
            "model": MODEL_NAME,
            "threshold_optimization": service.threshold_optimization_summary,
            "validation": val_metrics,
            "test": test_metrics,
        },
    )
    print(f"\n[Saved] Metrics CSV -> {csv_path}")
    print(f"[Saved] Metrics JSON -> {json_path}")

    service.save(TRAINED_MODEL_PATH)
    return service, val_metrics, test_metrics


def _threshold_objective_score(objective: str, y_true, y_pred, y_prob) -> float:
    objective = objective.lower()
    if objective == "accuracy":
        return float(accuracy_score(y_true, y_pred))
    if objective == "f1":
        return float(f1_score(y_true, y_pred, zero_division=0))
    if objective == "balanced_accuracy":
        return float(balanced_accuracy_score(y_true, y_pred))
    if objective == "mcc":
        return float(matthews_corrcoef(y_true, y_pred))
    if objective == "pr_auc":
        return float(average_precision_score(y_true, y_prob))
    if objective == "roc_auc":
        return float(roc_auc_score(y_true, y_prob))
    return float(balanced_accuracy_score(y_true, y_pred))


def run_error_analysis(model, X, y, split_name="Test"):
    """Persist systematic error artifacts for downstream analysis/reporting."""
    preds = model.predict(X)
    proba = model.predict_proba(X)[:, 1]
    cm = confusion_matrix(y, preds, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    error_mask = preds != y
    misclassified = X.loc[error_mask].copy()
    misclassified["true_label"] = y.loc[error_mask].values
    misclassified["predicted_label"] = preds[error_mask]
    misclassified["predicted_probability"] = proba[error_mask]
    misclassified["error_type"] = np.where(
        (misclassified["true_label"] == 0) & (misclassified["predicted_label"] == 1),
        "False Positive",
        "False Negative",
    )

    summary = {
        "split": split_name,
        "model": MODEL_NAME,
        "total_samples": int(len(y)),
        "total_errors": int(error_mask.sum()),
        "error_rate": float(error_mask.mean()),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
    }

    csv_path = _safe_save_csv(misclassified, ERROR_ANALYSIS_CSV)
    json_path = _safe_save_json(ERROR_SUMMARY_JSON, summary)
    print(f"[Saved] Error analysis CSV -> {csv_path}")
    print(f"[Saved] Error analysis summary JSON -> {json_path}")
    return summary, misclassified
