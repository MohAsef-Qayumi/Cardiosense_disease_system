"""
Module 1: Data Loader
Loads the heart disease dataset from disk.
"""

from pathlib import Path
import sys

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATA_RAW_DIR, DATASET_PATH, TARGET_COLUMN

CARDIO_REQUIRED_COLUMNS = [
    "id",
    "age",
    "gender",
    "height",
    "weight",
    "ap_hi",
    "ap_lo",
    "cholesterol",
    "gluc",
    "smoke",
    "alco",
    "active",
    TARGET_COLUMN,
]


def _resolve_dataset_path(dataset_path: Path) -> Path:
    """Resolve the configured dataset path with deterministic fallbacks."""
    if dataset_path.exists():
        return dataset_path

    downloads_candidate = Path.home() / "Downloads" / dataset_path.name
    if downloads_candidate.exists():
        print(
            f"[DataLoader] Using fallback dataset from Downloads: {downloads_candidate}"
        )
        return downloads_candidate

    same_name_candidates = sorted(DATA_RAW_DIR.glob(dataset_path.name))
    if same_name_candidates:
        return same_name_candidates[0]

    raise FileNotFoundError(
        f"Dataset not found at '{dataset_path}'. "
        f"Place '{dataset_path.name}' in '{DATA_RAW_DIR}' or Downloads."
    )


def _normalize_target_column(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize known target aliases to the canonical target column name."""
    if TARGET_COLUMN in df.columns:
        return df

    target_aliases = [
        "HeartDiseaseorAttack",
        "heartdiseaseorattack",
        "target",
        "Target",
        "cardio",
        "Cardio",
    ]
    lower_to_original = {c.lower(): c for c in df.columns}
    detected = None

    for alias in target_aliases:
        if alias in df.columns:
            detected = alias
            break
        if alias.lower() in lower_to_original:
            detected = lower_to_original[alias.lower()]
            break

    if detected is None:
        raise KeyError(
            f"Target column '{TARGET_COLUMN}' not found and no known alias detected. "
            f"Columns available: {list(df.columns)}"
        )

    print(f"[DataLoader] Normalized target column '{detected}' -> '{TARGET_COLUMN}'.")
    return df.rename(columns={detected: TARGET_COLUMN})


def load_heart_disease_data(save_path=None):
    """
    Load heart disease dataset from CSV.

    Supports both comma and semicolon delimiters.
    """
    dataset_path = Path(save_path) if save_path else DATASET_PATH
    dataset_path = _resolve_dataset_path(dataset_path)

    df = pd.read_csv(dataset_path, sep=None, engine="python")
    df.columns = [c.strip() for c in df.columns]
    df = _normalize_target_column(df)

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        df = df.drop_duplicates().reset_index(drop=True)
        print(f"[DataLoader] Dropped {duplicate_rows} duplicate rows.")

    for col in df.columns:
        if df[col].dtype == "O":
            df[col] = pd.to_numeric(df[col], errors="ignore")

    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    before_target_clean = len(df)
    df = df[df[TARGET_COLUMN].isin([0, 1])].copy()
    removed_invalid_target = before_target_clean - len(df)
    if removed_invalid_target:
        print(f"[DataLoader] Removed {removed_invalid_target} rows with invalid target values.")

    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    missing_required = sorted(set(CARDIO_REQUIRED_COLUMNS) - set(df.columns))
    if missing_required:
        print(
            "[DataLoader] Warning: dataset does not fully match cardio schema. "
            f"Missing columns: {missing_required}"
        )
    else:
        # Keep a deterministic column order for reproducible preprocessing behavior.
        ordered_cols = [c for c in CARDIO_REQUIRED_COLUMNS if c in df.columns]
        df = df[ordered_cols]

    class_dist = df[TARGET_COLUMN].value_counts(normalize=True).sort_index().round(4).to_dict()
    print(f"[DataLoader] Dataset loaded from {dataset_path} | Shape: {df.shape}")
    print(f"[DataLoader] Target distribution: {class_dist}")
    return df

if __name__ == "__main__":
    df = load_heart_disease_data()
    print(df.head())
    print("\nTarget distribution:\n", df[TARGET_COLUMN].value_counts())
