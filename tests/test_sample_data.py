"""The injected faults must really be in the data, otherwise later tests prove nothing."""

from qualitylens.sample_data import CATEGORIES, corrupt, generate_orders


def test_generation_is_reproducible():
    assert generate_orders(100, seed=1).equals(generate_orders(100, seed=1))


def test_reference_is_clean():
    df = generate_orders(2_000, seed=42)
    assert df.isna().sum().sum() == 0
    assert df["order_id"].is_unique
    assert set(df["product_category"]) <= set(CATEGORIES)
    assert df["email"].str.contains("@").all()


def test_corruption_injects_every_fault():
    clean = generate_orders(2_000, seed=7)
    bad = corrupt(clean, seed=7)

    assert 0.25 < bad["income"].isna().mean() < 0.35
    assert bad["order_amount"].median() > 50 * clean["order_amount"].median()
    assert "crypto" in set(bad["product_category"])
    assert bad["age"].mean() - clean["age"].mean() > 5
    assert not bad["order_id"].is_unique
    assert (~bad["email"].str.contains("@")).mean() > 0.04
