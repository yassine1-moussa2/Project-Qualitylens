import numpy as np
import pandas as pd
import pytest

from qualitylens.ingest import load_table
from qualitylens.profile import profile_dataframe
from qualitylens.sample_data import corrupt, generate_orders


@pytest.fixture
def small_df():
    return pd.DataFrame(
        {
            "amount": [1.0, 2.0, 3.0, np.nan],
            "city": ["Paris", "Lyon", "Paris", None],
            "flag": [True, False, True, True],
            "when": pd.to_datetime(["2026-01-01", "2026-01-02", None, "2026-01-05"]),
        }
    )


def test_column_kinds(small_df):
    cols = profile_dataframe(small_df).columns
    assert cols["amount"].kind == "numeric"
    assert cols["city"].kind == "categorical"
    assert cols["flag"].kind == "boolean"
    assert cols["when"].kind == "datetime"


def test_null_stats_and_numeric_summary(small_df):
    amount = profile_dataframe(small_df).columns["amount"]
    assert amount.count == 4
    assert amount.null_count == 1
    assert amount.null_pct == pytest.approx(0.25)
    assert (amount.min, amount.max, amount.mean) == (1.0, 3.0, 2.0)
    assert sum(amount.histogram["counts"]) == 3


def test_categorical_top_values(small_df):
    city = profile_dataframe(small_df).columns["city"]
    assert city.top_values == {"Paris": 2, "Lyon": 1}
    assert city.n_unique == 2


def test_datetime_range(small_df):
    when = profile_dataframe(small_df).columns["when"]
    assert when.min.startswith("2026-01-01")
    assert when.max.startswith("2026-01-05")


def test_current_batch_reuses_reference_bins():
    reference = profile_dataframe(generate_orders(1_000, seed=1))
    current = profile_dataframe(corrupt(generate_orders(1_000, seed=2), seed=2), reference=reference)

    ref_edges = reference.columns["age"].histogram["bin_edges"]
    assert current.columns["age"].histogram["bin_edges"] == ref_edges


def test_out_of_range_values_land_in_outer_bins():
    reference = profile_dataframe(pd.DataFrame({"x": np.arange(100.0)}))
    current = profile_dataframe(pd.DataFrame({"x": [-50.0, 50.0, 10_000.0]}), reference=reference)

    counts = current.columns["x"].histogram["counts"]
    assert sum(counts) == 3
    assert counts[0] == 1 and counts[-1] == 1


def test_profile_shows_injected_faults():
    """The profiler alone already surfaces some faults: nulls and the new category."""
    profile = profile_dataframe(corrupt(generate_orders(2_000, seed=3), seed=3))
    assert profile.columns["income"].null_pct > 0.25
    assert "crypto" in profile.columns["product_category"].top_values


def test_to_dict_is_json_ready(small_df):
    import json

    json.dumps(profile_dataframe(small_df).to_dict(), default=str)


def test_load_table_roundtrip(tmp_path, small_df):
    csv_path = tmp_path / "t.csv"
    small_df.to_csv(csv_path, index=False)
    loaded = load_table(csv_path, parse_dates=["when"])
    assert loaded.shape == small_df.shape

    with pytest.raises(ValueError, match="Available columns"):
        load_table(csv_path, parse_dates=["wen"])

    with pytest.raises(ValueError):
        (tmp_path / "t.txt").write_text("x")
        load_table(tmp_path / "t.txt")
