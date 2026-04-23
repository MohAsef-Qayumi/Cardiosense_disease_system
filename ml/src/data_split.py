"""
Module 4: Train/Validation Split with Leakage Prevention
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
import warnings
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import RANDOM_STATE, TARGET_COLUMN, TEST_SIZE, VAL_SIZE

warnings.filterwarnings("ignore")

# ─── Leakage Detection ────────────────────────────────────────────────────────

def check_for_leakage(X_train: pd.DataFrame, X_val: pd.DataFrame, y_train, y_val):
    """Run multiple leakage checks between train and validation sets.

    Returns True if no leakage is detected.
    """
    print("\n" + "=" * 60)
    print("LEAKAGE DETECTION CHECKS")
    print("=" * 60)

    failures = []
    warnings_list = []

    # Check 1: No duplicate rows between train and val
    train_hashes = set(pd.util.hash_pandas_object(X_train).values)
    val_hashes = set(pd.util.hash_pandas_object(X_val).values)
    overlap = len(train_hashes & val_hashes)
    if overlap > 0:
        failures.append(f"  [FAIL] Row overlap: {overlap} duplicate rows between train and val!")
    else:
        print("  [PASS] No duplicate rows between train and validation sets.")

    # Check 2: Target not in feature set
    target_aliases = {"target", TARGET_COLUMN}
    if target_aliases & set(X_train.columns) or target_aliases & set(X_val.columns):
        failures.append(
            f"  [FAIL] Target column found in features ({sorted(target_aliases)})."
        )
    else:
        print("  [PASS] Target column is not present in feature set.")

    # Check 3: Index integrity — no overlapping indices
    train_idx = set(X_train.index)
    val_idx = set(X_val.index)
    idx_overlap = len(train_idx & val_idx)
    if idx_overlap > 0:
        failures.append(f"  [FAIL] Index overlap: {idx_overlap} shared indices!")
    else:
        print("  [PASS] No index overlap between train and validation.")

    # Check 4: Label distribution check (no label shift)
    train_ratio = y_train.mean()
    val_ratio = y_val.mean()
    drift = abs(train_ratio - val_ratio)
    if drift > 0.1:
        warnings_list.append(
            f"  [WARN] Label distribution drift: train={train_ratio:.2f}, val={val_ratio:.2f}"
        )
    else:
        print(f"  [PASS] Label distribution consistent: train={train_ratio:.2f}, val={val_ratio:.2f}")

    # Check 5: Feature-scale consistency (means should be close if standardized)
    numeric_cols = [c for c in X_train.columns if np.issubdtype(X_train[c].dtype, np.number) and c != "id"]
    mean_diff = (X_train[numeric_cols].mean() - X_val[numeric_cols].mean()).abs() if numeric_cols else pd.Series([0.0])
    max_mean_diff = mean_diff.max()
    if max_mean_diff > 3.0:
        warnings_list.append(
            f"  [WARN] High feature mean difference (max={max_mean_diff:.2f}). "
            "Possible distribution shift."
        )
    else:
        print(f"  [PASS] Feature distributions consistent across splits (max mean diff={max_mean_diff:.2f}).")

    if warnings_list:
        print("\n[LEAKAGE ALERTS]:")
        for issue in warnings_list:
            print(issue)

    if failures:
        print("\n[LEAKAGE FAILURES]:")
        for issue in failures:
            print(issue)
        return False
    else:
        print("\n  [ALL CRITICAL CHECKS PASSED] No data leakage detected.")
        return True


# ─── Main Split Function ──────────────────────────────────────────────────────

def create_train_val_split(X: pd.DataFrame, y: pd.Series,
                           test_size=None, val_size=None,
                           random_state=None, stratify=True):
    """
    Create a clean 70/10/20 train/val/test split with stratification.
    Run leakage checks after splitting.
    """
    if test_size is None:
        test_size = TEST_SIZE
    if val_size is None:
        val_size = VAL_SIZE
    if random_state is None:
        random_state = RANDOM_STATE
    if test_size <= 0 or test_size >= 1:
        raise ValueError(f"test_size must be in (0, 1). Got: {test_size}")
    if val_size <= 0 or val_size >= 1:
        raise ValueError(f"val_size must be in (0, 1). Got: {val_size}")
    if test_size + val_size >= 1:
        raise ValueError(
            f"test_size + val_size must be < 1. Got: {test_size + val_size:.3f}"
        )

    print("\n" + "=" * 60)
    print("TRAIN / VALIDATION / TEST SPLIT")
    print("=" * 60)

    strat_y = y if stratify else None

    # Step 1: Split off test set (20%)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=strat_y
    )

    # Step 2: Split the remainder into train (87.5%) and val (12.5%) → ~70/10 of total
    val_frac_of_remaining = val_size / (1 - test_size)
    strat_temp = y_temp if stratify else None

    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp,
        test_size=val_frac_of_remaining,
        random_state=random_state,
        stratify=strat_temp
    )

    # Print split summary
    total = len(X)
    print(f"\n  Total samples:      {total}")
    print(f"  Training set:       {len(X_train)} ({len(X_train)/total*100:.1f}%)")
    print(f"  Validation set:     {len(X_val)} ({len(X_val)/total*100:.1f}%)")
    print(f"  Test set:           {len(X_test)} ({len(X_test)/total*100:.1f}%)")

    train_counts = y_train.value_counts().reindex([0, 1], fill_value=0)
    val_counts = y_val.value_counts().reindex([0, 1], fill_value=0)
    test_counts = y_test.value_counts().reindex([0, 1], fill_value=0)

    print(f"\n  Class balance (train):  0={train_counts.loc[0]}  1={train_counts.loc[1]}")
    print(f"  Class balance (val):    0={val_counts.loc[0]}  1={val_counts.loc[1]}")
    print(f"  Class balance (test):   0={test_counts.loc[0]}  1={test_counts.loc[1]}")

    # Run leakage checks
    leakage_free = check_for_leakage(X_train, X_val, y_train, y_val)

    return X_train, X_val, X_test, y_train, y_val, y_test, leakage_free


def create_cv_folds(X: pd.DataFrame, y: pd.Series, n_splits=5):
    """
    Create stratified K-Fold cross-validation folds for robust evaluation.
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    folds = list(skf.split(X, y))
    print(f"\n  [CV] Created {n_splits}-fold stratified cross-validation splits.")
    return folds


if __name__ == "__main__":
    from src.data_loader import load_heart_disease_data

    df = load_heart_disease_data()
    X = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]
    X_train, X_val, X_test, y_train, y_val, y_test, clean = create_train_val_split(X, y)
    print(f"\nLeakage-free: {clean}")
