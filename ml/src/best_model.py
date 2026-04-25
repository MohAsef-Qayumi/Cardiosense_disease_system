"""Recall-first best model selection pipeline for heart disease inference."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import ParameterGrid, StratifiedKFold
from xgboost import XGBClassifier

from config import MODELS_DIR, RESULTS_DIR

try:
    import optuna
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    optuna = None


@dataclass
class BestModelConfig:
    random_state: int = 42
    precision_floor: float = 0.72
    target_recall: float = 0.83
    target_accuracy: float = 0.78
    target_fnr: float = 0.17
    optuna_trials_xgb: int = 35
    optuna_trials_lgbm: int = 35
    optuna_trials_rf: int = 30
    optuna_timeout_seconds: int | None = None
    hyperopt_cv_folds: int = 4
    calibration_cv_folds: int = 5
    calibration_method: Literal["sigmoid", "isotonic"] = "sigmoid"


def _to_builtin(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_builtin(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def _slice_rows(data: Any, idx: np.ndarray) -> Any:
    if hasattr(data, "iloc"):
        return data.iloc[idx]
    return data[idx]


def _fnr(y_true: pd.Series, y_pred: np.ndarray) -> float:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    _, _, fn, tp = cm.ravel()
    return float(fn / (fn + tp + 1e-12))


def _candidate_metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float, source: str) -> dict[str, Any]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "source": source,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "fnr": _fnr(y_true, y_pred),
    }


def _threshold_candidates(y_true: pd.Series, y_prob: np.ndarray) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    _, _, pr_thresholds = precision_recall_curve(y_true, y_prob)
    for threshold in pr_thresholds:
        candidates.append(_candidate_metrics(y_true, y_prob, float(threshold), "pr_curve"))

    fpr, tpr, roc_thresholds = roc_curve(y_true, y_prob)
    if len(roc_thresholds) > 0:
        youden_idx = int(np.argmax(tpr - fpr))
        roc_t = float(roc_thresholds[youden_idx])
        if np.isfinite(roc_t):
            candidates.append(_candidate_metrics(y_true, y_prob, roc_t, "roc_youden"))

    # Always include a clinical baseline threshold.
    candidates.append(_candidate_metrics(y_true, y_prob, 0.5, "fixed_0_5"))

    unique: dict[tuple[float, str], dict[str, Any]] = {}
    for item in candidates:
        key = (round(float(item["threshold"]), 6), str(item["source"]))
        unique[key] = item
    return list(unique.values())


def _choose_threshold(y_true: pd.Series, y_prob: np.ndarray, precision_floor: float) -> dict[str, Any]:
    candidates = _threshold_candidates(y_true, y_prob)
    feasible = [c for c in candidates if c["precision"] >= precision_floor]
    pool = feasible if feasible else candidates

    best = max(
        pool,
        key=lambda c: (
            c["recall"],
            c["accuracy"],
            c["precision"],
            -c["fnr"],
        ),
    )

    return {
        "selected_threshold": float(best["threshold"]),
        "selected_source": str(best["source"]),
        "precision": float(best["precision"]),
        "recall": float(best["recall"]),
        "accuracy": float(best["accuracy"]),
        "fnr": float(best["fnr"]),
        "precision_floor": float(precision_floor),
        "precision_floor_satisfied": bool(best["precision"] >= precision_floor),
        "num_candidates": int(len(candidates)),
        "num_feasible_candidates": int(len(feasible)),
    }


def _metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float, label: str) -> dict[str, Any]:
    y_pred = (y_prob >= threshold).astype(int)

    report_text = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["No Disease", "Disease"],
        zero_division=0,
    )
    report_dict = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["No Disease", "Disease"],
        zero_division=0,
        output_dict=True,
    )

    return {
        "label": label,
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "fnr": _fnr(y_true, y_pred),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "classification_report_text": report_text,
        "classification_report": report_dict,
    }


def _print_metrics(label: str, threshold_info: dict[str, Any], val_metrics: dict[str, Any], test_metrics: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print(f"[{label}]")
    print("=" * 78)
    print(
        "Validation threshold selection -> "
        f"threshold={threshold_info['selected_threshold']:.4f}, "
        f"source={threshold_info['selected_source']}, "
        f"precision={threshold_info['precision']:.4f}, "
        f"recall={threshold_info['recall']:.4f}, "
        f"accuracy={threshold_info['accuracy']:.4f}, "
        f"fnr={threshold_info['fnr']:.4f}, "
        f"precision_floor_met={threshold_info['precision_floor_satisfied']}"
    )

    print("\nValidation metrics:")
    print(
        f"Acc={val_metrics['accuracy']:.4f} | Prec={val_metrics['precision']:.4f} | "
        f"Recall={val_metrics['recall']:.4f} | FNR={val_metrics['fnr']:.4f} | "
        f"ROC-AUC={val_metrics['roc_auc']:.4f} | PR-AUC={val_metrics['pr_auc']:.4f}"
    )
    print("Confusion Matrix [[TN, FP], [FN, TP]]:")
    print(np.array(val_metrics["confusion_matrix"]))
    print(val_metrics["classification_report_text"])

    print("Test metrics (fixed threshold from validation):")
    print(
        f"Acc={test_metrics['accuracy']:.4f} | Prec={test_metrics['precision']:.4f} | "
        f"Recall={test_metrics['recall']:.4f} | FNR={test_metrics['fnr']:.4f} | "
        f"ROC-AUC={test_metrics['roc_auc']:.4f} | PR-AUC={test_metrics['pr_auc']:.4f}"
    )
    print("Confusion Matrix [[TN, FP], [FN, TP]]:")
    print(np.array(test_metrics["confusion_matrix"]))
    print(test_metrics["classification_report_text"])


def _build_model(model_name: str, cfg: BestModelConfig, params: dict[str, Any] | None = None):
    if model_name == "xgb":
        model = XGBClassifier(
            random_state=cfg.random_state,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_estimators=500,
            learning_rate=0.03,
            max_depth=4,
            min_child_weight=2,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            n_jobs=1,
        )
    elif model_name == "lgbm":
        model = LGBMClassifier(
            random_state=cfg.random_state,
            objective="binary",
            n_estimators=500,
            learning_rate=0.03,
            num_leaves=31,
            min_child_samples=30,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            verbosity=-1,
            n_jobs=1,
        )
    elif model_name == "rf":
        model = RandomForestClassifier(
            random_state=cfg.random_state,
            n_estimators=600,
            max_depth=None,
            min_samples_split=6,
            min_samples_leaf=2,
            max_features="sqrt",
            n_jobs=1,
        )
    else:
        raise ValueError(f"Unsupported model_name: {model_name}")

    if params:
        model.set_params(**params)
    return model


def _recall_objective_score(threshold_summary: dict[str, Any], cfg: BestModelConfig) -> float:
    recall = float(threshold_summary["recall"])
    precision = float(threshold_summary["precision"])
    accuracy = float(threshold_summary["accuracy"])
    fnr = float(threshold_summary["fnr"])

    precision_penalty = max(0.0, cfg.precision_floor - precision) * 2.5
    accuracy_penalty = max(0.0, cfg.target_accuracy - accuracy) * 0.6
    fnr_penalty = max(0.0, fnr - cfg.target_fnr) * 0.6
    return float(recall - precision_penalty - accuracy_penalty - fnr_penalty)


def _suggest_hyperparameters(trial: Any, model_name: str) -> dict[str, Any]:
    if model_name == "xgb":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 250, 900),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.12, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
        }
    if model_name == "lgbm":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 250, 900),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.12, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 16, 160),
            "max_depth": trial.suggest_int("max_depth", -1, 12),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 80),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }
    return {
        "n_estimators": trial.suggest_int("n_estimators", 250, 1200),
        "max_depth": trial.suggest_int("max_depth", 4, 30),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 8),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
    }


def _grid_search_space(model_name: str) -> dict[str, list[Any]]:
    if model_name == "xgb":
        return {
            "n_estimators": [300, 500, 700],
            "learning_rate": [0.01, 0.03, 0.07],
            "max_depth": [3, 4, 6],
            "min_child_weight": [1, 3, 6],
            "subsample": [0.7, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.9, 1.0],
        }
    if model_name == "lgbm":
        return {
            "n_estimators": [300, 500, 700],
            "learning_rate": [0.01, 0.03, 0.07],
            "num_leaves": [24, 31, 63],
            "max_depth": [-1, 6, 10],
            "min_child_samples": [15, 30, 60],
            "subsample": [0.7, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.9, 1.0],
        }
    return {
        "n_estimators": [300, 600, 900],
        "max_depth": [8, 16, 24],
        "min_samples_split": [2, 6, 12],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2", None],
    }


def _fit_calibrated(
    model: BaseEstimator,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cfg: BestModelConfig,
):
    cv = StratifiedKFold(
        n_splits=cfg.calibration_cv_folds,
        shuffle=True,
        random_state=cfg.random_state,
    )
    try:
        calibrated = CalibratedClassifierCV(
            estimator=model,
            method=cfg.calibration_method,
            cv=cv,
        )
    except TypeError:
        calibrated = CalibratedClassifierCV(
            base_estimator=model,
            method=cfg.calibration_method,
            cv=cv,
        )
    calibrated.fit(X_train, y_train)
    return calibrated


def _tune_model_grid(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cfg: BestModelConfig,
) -> tuple[dict[str, Any], float]:
    cv = StratifiedKFold(
        n_splits=cfg.hyperopt_cv_folds,
        shuffle=True,
        random_state=cfg.random_state,
    )
    all_params = list(ParameterGrid(_grid_search_space(model_name)))

    max_trials = cfg.optuna_trials_xgb
    if model_name == "lgbm":
        max_trials = cfg.optuna_trials_lgbm
    elif model_name == "rf":
        max_trials = cfg.optuna_trials_rf

    rng = np.random.default_rng(cfg.random_state)
    if len(all_params) > max_trials:
        selected_idx = rng.choice(len(all_params), size=max_trials, replace=False)
        param_candidates = [all_params[i] for i in selected_idx]
    else:
        param_candidates = all_params

    best_score = float("-inf")
    best_params = param_candidates[0]

    for params in param_candidates:
        fold_scores: list[float] = []
        for train_idx, val_idx in cv.split(X_train, y_train):
            X_tr = _slice_rows(X_train, train_idx)
            y_tr = _slice_rows(y_train, train_idx)
            X_va = _slice_rows(X_train, val_idx)
            y_va = _slice_rows(y_train, val_idx)

            fold_model = cast(BaseEstimator, _build_model(model_name, cfg, params))
            calibrated = _fit_calibrated(fold_model, X_tr, y_tr, cfg)
            val_prob = calibrated.predict_proba(X_va)[:, 1]
            threshold_summary = _choose_threshold(y_va, val_prob, cfg.precision_floor)
            fold_scores.append(_recall_objective_score(threshold_summary, cfg))

        score = float(np.mean(fold_scores))
        if score > best_score:
            best_score = score
            best_params = params

    return best_params, best_score


def _tune_model_optuna(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cfg: BestModelConfig,
) -> tuple[dict[str, Any], float]:
    if optuna is None:
        print("  [WARN] Optuna is not installed. Falling back to grid-style hyperparameter search.")
        return _tune_model_grid(model_name, X_train, y_train, cfg)

    cv = StratifiedKFold(
        n_splits=cfg.hyperopt_cv_folds,
        shuffle=True,
        random_state=cfg.random_state,
    )

    def objective(trial: Any) -> float:
        params = _suggest_hyperparameters(trial, model_name)

        fold_scores: list[float] = []
        for train_idx, val_idx in cv.split(X_train, y_train):
            X_tr = _slice_rows(X_train, train_idx)
            y_tr = _slice_rows(y_train, train_idx)
            X_va = _slice_rows(X_train, val_idx)
            y_va = _slice_rows(y_train, val_idx)

            fold_model = cast(BaseEstimator, _build_model(model_name, cfg, params))
            calibrated = _fit_calibrated(fold_model, X_tr, y_tr, cfg)
            val_prob = calibrated.predict_proba(X_va)[:, 1]
            threshold_summary = _choose_threshold(y_va, val_prob, cfg.precision_floor)
            fold_scores.append(_recall_objective_score(threshold_summary, cfg))

        return float(np.mean(fold_scores))

    trials = cfg.optuna_trials_xgb
    if model_name == "lgbm":
        trials = cfg.optuna_trials_lgbm
    elif model_name == "rf":
        trials = cfg.optuna_trials_rf

    sampler = optuna.samplers.TPESampler(seed=cfg.random_state)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(
        objective,
        n_trials=trials,
        timeout=cfg.optuna_timeout_seconds,
        show_progress_bar=False,
    )
    return study.best_params, float(study.best_value)


def _evaluate_step(
    step_name: str,
    model,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    cfg: BestModelConfig,
) -> dict[str, Any]:
    val_prob = model.predict_proba(X_val)[:, 1]
    threshold_info = _choose_threshold(y_val, val_prob, cfg.precision_floor)
    threshold = float(threshold_info["selected_threshold"])

    val_metrics = _metrics(y_val, val_prob, threshold, f"{step_name}_validation")
    test_prob = model.predict_proba(X_test)[:, 1]
    test_metrics = _metrics(y_test, test_prob, threshold, f"{step_name}_test")

    _print_metrics(step_name, threshold_info, val_metrics, test_metrics)

    return {
        "threshold": threshold_info,
        "validation": val_metrics,
        "test": test_metrics,
    }


def _candidate_rank(step_result: dict[str, Any], cfg: BestModelConfig) -> tuple[Any, ...]:
    val = step_result["validation"]
    return (
        int(val["precision"] >= cfg.precision_floor),
        int(val["recall"] >= cfg.target_recall),
        int(val["accuracy"] >= cfg.target_accuracy),
        int(val["fnr"] <= cfg.target_fnr),
        val["recall"],
        val["accuracy"],
        -val["fnr"],
        val["precision"],
    )


def train_best_ensemble(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    cfg: BestModelConfig | None = None,
):
    cfg = cfg or BestModelConfig()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {
        "config": asdict(cfg),
        "hyperparameter_search": {},
        "steps": {},
    }
    fitted_models: dict[str, Any] = {}

    print("\n[BestModel] Hyperparameter tuning with Optuna (recall-first objective)...")
    tuned_params: dict[str, dict[str, Any]] = {}
    for model_name in ("xgb", "lgbm", "rf"):
        best_params, best_score = _tune_model_optuna(model_name, X_train, y_train, cfg)
        tuned_params[model_name] = best_params
        results["hyperparameter_search"][model_name] = {
            "best_params": best_params,
            "best_objective_score": best_score,
        }
        print(f"  - {model_name.upper()} best objective score: {best_score:.5f}")

    print("\n[BestModel] Step 1 - calibrated tuned base models...")
    for model_name in ("xgb", "lgbm", "rf"):
        step_name = f"step1_{model_name}_calibrated"
        tuned_model = cast(BaseEstimator, _build_model(model_name, cfg, tuned_params[model_name]))
        calibrated = _fit_calibrated(tuned_model, X_train, y_train, cfg)
        fitted_models[step_name] = calibrated
        results["steps"][step_name] = _evaluate_step(
            step_name,
            calibrated,
            X_val,
            y_val,
            X_test,
            y_test,
            cfg,
        )

    print("\n[BestModel] Step 2 - calibrated soft-voting ensemble...")
    soft_voting = VotingClassifier(
        estimators=[
            ("xgb", cast(BaseEstimator, _build_model("xgb", cfg, tuned_params["xgb"]))),
            ("lgbm", cast(BaseEstimator, _build_model("lgbm", cfg, tuned_params["lgbm"]))),
            ("rf", cast(BaseEstimator, _build_model("rf", cfg, tuned_params["rf"]))),
        ],
        voting="soft",
        n_jobs=1,
    )
    calibrated_soft_voting = _fit_calibrated(soft_voting, X_train, y_train, cfg)
    fitted_models["step2_soft_voting_calibrated"] = calibrated_soft_voting
    results["steps"]["step2_soft_voting_calibrated"] = _evaluate_step(
        "step2_soft_voting_calibrated",
        calibrated_soft_voting,
        X_val,
        y_val,
        X_test,
        y_test,
        cfg,
    )

    print("\n[BestModel] Step 3 - calibrated stacking ensemble...")
    stacking = StackingClassifier(
        estimators=[
            ("xgb", cast(BaseEstimator, _build_model("xgb", cfg, tuned_params["xgb"]))),
            ("lgbm", cast(BaseEstimator, _build_model("lgbm", cfg, tuned_params["lgbm"]))),
            ("rf", cast(BaseEstimator, _build_model("rf", cfg, tuned_params["rf"]))),
        ],
        final_estimator=LogisticRegression(max_iter=1000, random_state=cfg.random_state),
        stack_method="predict_proba",
        cv=5,
        n_jobs=1,
    )
    calibrated_stacking = _fit_calibrated(stacking, X_train, y_train, cfg)
    fitted_models["step3_stacking_calibrated"] = calibrated_stacking
    results["steps"]["step3_stacking_calibrated"] = _evaluate_step(
        "step3_stacking_calibrated",
        calibrated_stacking,
        X_val,
        y_val,
        X_test,
        y_test,
        cfg,
    )

    selected_name = max(results["steps"], key=lambda name: _candidate_rank(results["steps"][name], cfg))
    selected_step = results["steps"][selected_name]
    selected_threshold = float(selected_step["threshold"]["selected_threshold"])
    selected_test_metrics = selected_step["test"]

    target_check = {
        "precision_floor_met": bool(selected_test_metrics["precision"] >= cfg.precision_floor),
        "target_recall_met": bool(selected_test_metrics["recall"] >= cfg.target_recall),
        "target_fnr_met": bool(selected_test_metrics["fnr"] <= cfg.target_fnr),
        "target_accuracy_met": bool(selected_test_metrics["accuracy"] >= cfg.target_accuracy),
    }

    artifact = {
        "model_name": selected_name,
        "estimator": fitted_models[selected_name],
        "threshold": selected_threshold,
        "validation_metrics": selected_step["validation"],
        "test_metrics": selected_test_metrics,
        "config": asdict(cfg),
    }

    model_path = MODELS_DIR / "best_ensemble_model.pkl"
    metrics_path = RESULTS_DIR / "best_ensemble_metrics.json"
    summary_path = RESULTS_DIR / "best_ensemble_summary.json"

    joblib.dump(artifact, model_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(_to_builtin(results), f, indent=2)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            _to_builtin(
                {
                    "selected_model": selected_name,
                    "selected_threshold": selected_threshold,
                    "selected_test_metrics": selected_test_metrics,
                    "target_check": target_check,
                    "model_path": str(model_path),
                }
            ),
            f,
            indent=2,
        )

    print("\n[BestModel] Final selection:", selected_name)
    print(
        "[BestModel] Test metrics -> "
        f"Recall={selected_test_metrics['recall']:.4f}, "
        f"FNR={selected_test_metrics['fnr']:.4f}, "
        f"Precision={selected_test_metrics['precision']:.4f}, "
        f"Accuracy={selected_test_metrics['accuracy']:.4f}"
    )
    print("[BestModel] Target check:", target_check)
    print(f"[BestModel] Saved model: {model_path}")
    print(f"[BestModel] Saved detailed metrics: {metrics_path}")

    return artifact, results


class BestEnsembleService:
    """Wraps the best-selected ensemble artifact with the ConfidenceAwareInferenceService API.

    This allows main.py to use the same interface whether training a single XGBoost
    model or the full 5-model ensemble pipeline.
    """

    def __init__(self, artifact: dict[str, Any]):
        self.artifact = artifact
        self.model_name: str = str(artifact.get("model_name", "BestEnsemble"))
        self._estimator: Any = artifact["estimator"]
        self.decision_threshold: float = float(artifact["threshold"])
        self.is_fitted: bool = True
        self.use_calibration: bool = True
        # Not a single calibrated model — set to None so plot_evaluation skips feature importance.
        self.calibrated_model: Any = None
        self.fitted_estimator: Any = None
        _val = artifact.get("validation_metrics", {})
        self.threshold_optimization_summary: dict[str, Any] = {
            "objective": "recall_first",
            "threshold": self.decision_threshold,
            "score": float(_val.get("recall", 0.0)),
            "evaluated_thresholds": int(artifact.get("config", {}).get("num_candidates", 0)),
        }

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def predict(self, X: Any) -> Any:
        proba = self._estimator.predict_proba(X)[:, 1]
        return (proba >= self.decision_threshold).astype(int)

    def predict_proba(self, X: Any) -> Any:
        return self._estimator.predict_proba(X)

    def predict_with_confidence(self, X: Any) -> pd.DataFrame:
        proba = self._estimator.predict_proba(X)
        preds = (proba[:, 1] >= self.decision_threshold).astype(int)
        confidence_scores = np.max(proba, axis=1)

        tiers: list[str] = []
        for score in confidence_scores:
            if score >= 0.75:
                tiers.append("HIGH")
            elif score >= 0.55:
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

    # ------------------------------------------------------------------
    # Evaluation — matches ConfidenceAwareInferenceService.evaluate()
    # ------------------------------------------------------------------

    def evaluate(self, X: Any, y: Any, split_name: str = "Validation") -> tuple[dict[str, Any], Any]:
        from sklearn.metrics import (
            accuracy_score,
            average_precision_score,
            balanced_accuracy_score,
            brier_score_loss,
            classification_report,
            confusion_matrix,
            f1_score,
            matthews_corrcoef,
            precision_recall_fscore_support,
            precision_score,
            recall_score,
            roc_auc_score,
        )

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
        specificity = float(tn / (tn + fp)) if (tn + fp) else 0.0

        per_class_values = precision_recall_fscore_support(y, preds, labels=[0, 1], zero_division=0)
        per_class: dict[str, Any] = {
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

        metrics: dict[str, Any] = {
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

        print(f"\n{'=' * 60}")
        print(f"EVALUATION - {split_name} Set")
        print(f"{'=' * 60}")
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

    # ------------------------------------------------------------------
    # Persistence — saves self (the wrapper) to TRAINED_MODEL_PATH
    # so the model registry can joblib.load() and call predict_with_confidence()
    # ------------------------------------------------------------------

    def save(self, path: Any = None) -> Path:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import TRAINED_MODEL_PATH  # noqa: E402

        path_obj = Path(path) if path is not None else TRAINED_MODEL_PATH
        joblib.dump(self, str(path_obj))
        print(f"[Model saved] -> {path_obj}")
        return path_obj
