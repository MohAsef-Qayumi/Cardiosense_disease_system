from src.data_loader import load_heart_disease_data
from src.preprocessing import preprocess_splits
from src.data_split import create_train_val_split
from config import TARGET_COLUMN


def test_train_val_test_split_and_leakage_checks_pass():
    df = load_heart_disease_data()
    X_raw = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]

    X_train_raw, X_val_raw, X_test_raw, y_train, y_val, y_test, leakage_free = create_train_val_split(
        X_raw, y
    )
    X_train, X_val, X_test, _, _ = preprocess_splits(
        X_train_raw, X_val_raw, X_test_raw, save_pipeline=False
    )

    assert leakage_free is True
    assert len(X_train) + len(X_val) + len(X_test) == len(X_raw)
    assert len(y_train) + len(y_val) + len(y_test) == len(y)

    train_idx = set(X_train.index)
    val_idx = set(X_val.index)
    test_idx = set(X_test.index)

    assert len(train_idx & val_idx) == 0
    assert len(train_idx & test_idx) == 0
    assert len(val_idx & test_idx) == 0
