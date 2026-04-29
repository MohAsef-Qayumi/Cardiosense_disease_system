from src.data_loader import load_heart_disease_data
from src.data_split import create_train_val_split
from src.model import train_xgboost_model
from src.preprocessing import preprocess_splits
from config import TARGET_COLUMN


def test_xgboost_training_returns_expected_metrics():
    df = load_heart_disease_data()
    X_raw = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]
    X_train_raw, X_val_raw, X_test_raw, y_train, y_val, y_test, _ = create_train_val_split(X_raw, y)
    X_train, X_val, X_test, _, _ = preprocess_splits(
        X_train_raw, X_val_raw, X_test_raw, save_pipeline=False
    )

    _, val_metrics, test_metrics = train_xgboost_model(
        X_train, y_train, X_val, y_val, X_test, y_test
    )

    required_metrics = {
        "accuracy",
        "precision",
        "recall",
        "specificity",
        "f1",
        "roc_auc",
        "pr_auc",
        "balanced_accuracy",
        "mcc",
        "brier",
    }
    assert required_metrics.issubset(set(val_metrics.keys()))
    assert required_metrics.issubset(set(test_metrics.keys()))
