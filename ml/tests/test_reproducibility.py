from src.data_loader import load_heart_disease_data


def test_data_loader_is_reproducible_with_fixed_seed():
    df_first = load_heart_disease_data()
    df_second = load_heart_disease_data()

    assert df_first.equals(df_second)
