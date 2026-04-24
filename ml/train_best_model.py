"""Train and persist the best recall-focused ensemble model."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATASET_PATH, GLOBAL_SEED, TARGET_COLUMN, set_global_seed  # noqa: E402
from src.best_model import BestModelConfig, train_best_ensemble  # noqa: E402
from src.data_loader import load_heart_disease_data  # noqa: E402
from src.data_split import create_train_val_split  # noqa: E402
from src.preprocessing import filter_clinically_implausible_rows, preprocess_splits  # noqa: E402


def main() -> None:
    set_global_seed(GLOBAL_SEED)

    print("\n" + "=" * 70)
    print("BEST MODEL TRAINING - RECALL FIRST (XGB + LGBM + RF)")
    print("=" * 70)

    df = load_heart_disease_data(save_path=str(DATASET_PATH))
    df, plausibility_stats = filter_clinically_implausible_rows(df, target_col=TARGET_COLUMN)
    if plausibility_stats.get("enabled"):
        print(
            "Clinical plausibility filter: "
            f"dropped={plausibility_stats.get('dropped_rows', 0)} "
            f"({plausibility_stats.get('drop_rate', 0.0):.2%})"
        )

    X_raw = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]
    X_train_raw, X_val_raw, X_test_raw, y_train, y_val, y_test, _ = create_train_val_split(X_raw, y)
    X_train, X_val, X_test, _, _ = preprocess_splits(X_train_raw, X_val_raw, X_test_raw, save_pipeline=True)

    cfg = BestModelConfig(
        precision_floor=0.72,
        target_recall=0.83,
        target_accuracy=0.78,
        optuna_trials_xgb=35,
        optuna_trials_lgbm=35,
        optuna_trials_rf=30,
    )
    train_best_ensemble(X_train, y_train, X_val, y_val, X_test, y_test, cfg=cfg)


if __name__ == "__main__":
    main()
