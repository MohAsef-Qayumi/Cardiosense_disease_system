"""
main.py - Confidence-aware heart disease training pipeline.
"""

import asyncio
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Ensure project root is importable when run as a script.
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    DATA_PROCESSED_DIR,
    DATASET_PATH,
    GLOBAL_SEED,
    PREPROCESSING_PIPELINE_PATH,
    RESULTS_DIR,
    TARGET_COLUMN,
    THRESHOLD_OPTIMIZATION_OBJECTIVE,
    set_global_seed,
)
from src.best_model import BestEnsembleService, BestModelConfig, train_best_ensemble  # noqa: E402
from src.core.settings import get_settings  # noqa: E402
from src.data_loader import load_heart_disease_data  # noqa: E402
from src.data_split import create_train_val_split  # noqa: E402
from src.eda import run_eda  # noqa: E402
from src.evaluation import plot_evaluation  # noqa: E402
from src.model import run_error_analysis  # noqa: E402
from src.preprocessing import (  # noqa: E402
    filter_clinically_implausible_rows,
    preprocess_splits,
)
from src.services.container import build_container  # noqa: E402


def main():
    set_global_seed(GLOBAL_SEED)

    print("\n" + "=" * 70)
    print("  CONFIDENCE-AWARE AI INFERENCE SERVICE FOR HEART DISEASE PREDICTION")
    print("=" * 70)

    start_time = time.time()

    # Step 1: load and clean obvious clinical anomalies.
    print("\n[STEP 1/5] Loading dataset...")
    df = load_heart_disease_data(save_path=str(DATASET_PATH))
    print(f"  Dataset loaded: {df.shape[0]} samples, {df.shape[1]} columns")
    print(f"  Missing values: {df.isnull().sum().sum()}")

    df, plausibility_stats = filter_clinically_implausible_rows(df, target_col=TARGET_COLUMN)
    if plausibility_stats.get("enabled"):
        print(
            "  Clinical plausibility filter: "
            f"dropped={plausibility_stats.get('dropped_rows', 0)} "
            f"({plausibility_stats.get('drop_rate', 0.0):.2%}), "
            f"kept={plausibility_stats.get('kept_rows', len(df))}"
        )

    # Step 2: EDA.
    print("\n[STEP 2/5] Running Exploratory Data Analysis...")
    _, top_features = run_eda(df, save_plots=True)
    print(f"  Top predictive features:\n{top_features.head(5)}")

    # Step 3: split raw data first to avoid preprocessing leakage.
    print("\n[STEP 3/5] Creating stratified train/val/test splits on raw features...")
    X_raw = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]
    X_train_raw, X_val_raw, X_test_raw, y_train, y_val, y_test, leakage_free = create_train_val_split(
        X_raw, y
    )

    # Step 4: fit preprocessing on train only, then transform val/test.
    print("\n[STEP 4/5] Running leak-safe preprocessing (fit only on train split)...")
    X_train, X_val, X_test, pipeline, feature_names = preprocess_splits(
        X_train_raw, X_val_raw, X_test_raw, save_pipeline=True
    )
    print(f"  Preprocessed features: {len(feature_names)}")

    # Save processed splits for reproducibility and downstream usage.
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_df = X_train.copy()
    train_df[TARGET_COLUMN] = y_train.values
    val_df = X_val.copy()
    val_df[TARGET_COLUMN] = y_val.values
    test_df = X_test.copy()
    test_df[TARGET_COLUMN] = y_test.values

    train_path = DATA_PROCESSED_DIR / "train_processed.csv"
    val_path = DATA_PROCESSED_DIR / "val_processed.csv"
    test_path = DATA_PROCESSED_DIR / "test_processed.csv"

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print("\n  Processed splits saved:")
    print(f"    - Train: {train_path}")
    print(f"    - Val:   {val_path}")
    print(f"    - Test:  {test_path}")

    if not leakage_free:
        print("\n[WARNING] Potential split issues detected. Review leakage diagnostics.")

    # Step 5: Train all 5 calibrated models (XGB, LGBM, RF, Soft Voting, Stacking).
    print("\n[STEP 5/5] Training 5 calibrated models (XGB, LGBM, RF, Soft Voting, Stacking)...")
    cfg = BestModelConfig( optuna_trials_xgb=5,
    optuna_trials_lgbm=5,
    optuna_trials_rf=4,)
    artifact, ensemble_results = train_best_ensemble(
        X_train, y_train, X_val, y_val, X_test, y_test, cfg=cfg
    )
    service = BestEnsembleService(artifact)
    val_metrics, _ = service.evaluate(X_val, y_val, "Validation")
    test_metrics, _ = service.evaluate(X_test, y_test, "Test")

    # Evaluation artifacts.
    plot_evaluation(service, X_val, y_val, X_test, y_test, feature_names)

    print("\n" + "=" * 60)
    print("INFERENCE SERVICE DEMO - SAMPLE PREDICTIONS WITH CONFIDENCE")
    print("=" * 60)
    sample_results = service.predict_with_confidence(X_test.head(10))
    print(sample_results.to_string(index=False))

    print("\n" + "=" * 60)
    print("ERROR ANALYSIS - TEST SPLIT")
    print("=" * 60)
    error_summary, _ = run_error_analysis(service, X_test, y_test, split_name="Test")
    print(json.dumps(error_summary, indent=2))

    model_artifact_path = service.save()

    settings = get_settings()
    container = build_container(settings)
    class_balance = {
        str(label): float(value)
        for label, value in y_train.value_counts(normalize=True).sort_index().items()
    }
    validation_metrics_for_registry = dict(val_metrics)
    validation_metrics_for_registry["threshold_candidates_evaluated"] = service.threshold_optimization_summary[
        "evaluated_thresholds"
    ]
    async def _register_runtime_assets():
        await container.initialize()
        model_version = await container.model_registry.register_model_version(
            model_name=service.model_name,
            artifact_path=model_artifact_path,
            preprocessing_path=PREPROCESSING_PIPELINE_PATH,
            threshold_used=float(service.decision_threshold),
            threshold_objective=THRESHOLD_OPTIMIZATION_OBJECTIVE,
            threshold_score=float(service.threshold_optimization_summary["score"]),
            validation_metrics=validation_metrics_for_registry,
            test_metrics=test_metrics,
            class_balance=class_balance,
            feature_names=feature_names,
            training_parameters={"model_name": service.model_name, **artifact.get("config", {})},
            baseline_snapshot_id=None,
            metrics_path=RESULTS_DIR / "best_ensemble_metrics.json",
            notes="Registered from main.py 5-model ensemble training pipeline.",
            preloaded_model_service=service,
            preloaded_preprocessing_pipeline=pipeline,
        )
        baseline_snapshot = await container.drift_service.capture_training_baseline(
            model_version=model_version.id,
            feature_frame=X_val_raw.reset_index(drop=True),
            prediction_frame=service.predict_with_confidence(X_val.reset_index(drop=True)),
        )
        await container.model_registry.attach_baseline_snapshot(
            model_version.id,
            baseline_snapshot.id,
        )
        await container.close()
        return model_version, baseline_snapshot

    asyncio.run(_register_runtime_assets())

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("  PIPELINE COMPLETE - FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  Dataset:           {df.shape[0]} samples")
    print(f"  Features (raw):    {df.shape[1] - 1} columns")
    print(f"  Features (final):  {len(feature_names)} (after engineering)")
    print("  Train/Val/Test:    ~70% / ~10% / ~20%")
    print(f"\n  Selected Model:    {service.model_name} + Platt Calibration")
    print(f"  Val  Accuracy:     {val_metrics['accuracy']:.4f}")
    print(f"  Val  F1-Score:     {val_metrics['f1']:.4f}")
    print(f"  Val  ROC-AUC:      {val_metrics['roc_auc']:.4f}")
    print(f"  Val  PR-AUC:       {val_metrics['pr_auc']:.4f}")
    print(f"  Test Accuracy:     {test_metrics['accuracy']:.4f}")
    print(f"  Test F1-Score:     {test_metrics['f1']:.4f}")
    print(f"  Test ROC-AUC:      {test_metrics['roc_auc']:.4f}")
    print(f"  Test PR-AUC:       {test_metrics['pr_auc']:.4f}")
    print(f"\n  Total runtime:     {elapsed:.1f}s")
    print("\n  Output files saved to: outputs/")
    print("=" * 70)

    return service, val_metrics, test_metrics


if __name__ == "__main__":
    main()
