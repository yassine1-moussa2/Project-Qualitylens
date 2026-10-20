"""Synthetic reference/current datasets with known, injected faults.

This is step 1 of the build: before writing any check, we need data where we
*know* what is wrong. The reference set is clean. The current set is drawn from
the same generator, then corrupted on purpose. ``FAULTS`` lists every
corruption, so tests can assert that QualityLens catches each one.

The dataset imitates an e-commerce orders table:

    order_id, customer_id, age, income, country, product_category,
    order_amount, email, order_date
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

COUNTRIES = ["FR", "DE", "ES", "IT", "UK", "US"]
COUNTRY_WEIGHTS = [0.30, 0.20, 0.15, 0.10, 0.10, 0.15]
CATEGORIES = ["electronics", "books", "clothing", "home", "sports"]
CATEGORY_WEIGHTS = [0.25, 0.20, 0.25, 0.20, 0.10]

# Ground truth: what we break in the "current" dataset, and which kind of
# check is supposed to catch it.
FAULTS = [
    {"column": "income", "fault": "30% of values set to null", "caught_by": "quality: not_null"},
    {"column": "order_amount", "fault": "unit changed from dollars to cents (x100)", "caught_by": "quality: range + drift: PSI/KS"},
    {"column": "product_category", "fault": "new unseen category 'crypto'", "caught_by": "quality: allowed_values + drift: chi-square"},
    {"column": "age", "fault": "mean shifted up by ~8 years", "caught_by": "drift: PSI/KS"},
    {"column": "order_id", "fault": "2% duplicated ids", "caught_by": "quality: unique"},
    {"column": "email", "fault": "5% malformed emails", "caught_by": "quality: regex format"},
]


def generate_orders(n_rows: int, seed: int, start_date: str = "2026-01-01") -> pd.DataFrame:
    """Generate a clean orders table. Same seed gives the same table."""
    rng = np.random.default_rng(seed)

    age = rng.normal(loc=38, scale=11, size=n_rows).clip(18, 90).round().astype(int)
    # Income is right-skewed in real life, so a log-normal fits better than a normal.
    income = rng.lognormal(mean=10.6, sigma=0.45, size=n_rows).round(2)
    order_amount = rng.gamma(shape=2.0, scale=35.0, size=n_rows).round(2) + 1.0

    customer_ids = rng.integers(10_000, 99_999, size=n_rows)
    emails = [f"user{cid}@example.com" for cid in customer_ids]
    order_dates = pd.Timestamp(start_date) + pd.to_timedelta(
        rng.integers(0, 90, size=n_rows), unit="D"
    )

    return pd.DataFrame(
        {
            "order_id": np.arange(1, n_rows + 1) + seed * 1_000_000,
            "customer_id": customer_ids,
            "age": age,
            "income": income,
            "country": rng.choice(COUNTRIES, size=n_rows, p=COUNTRY_WEIGHTS),
            "product_category": rng.choice(CATEGORIES, size=n_rows, p=CATEGORY_WEIGHTS),
            "order_amount": order_amount,
            "email": emails,
            "order_date": order_dates,
        }
    )


def corrupt(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Apply every fault listed in ``FAULTS`` to a copy of ``df``."""
    rng = np.random.default_rng(seed)
    df = df.copy()
    n = len(df)

    def pick(fraction: float) -> np.ndarray:
        return rng.choice(n, size=int(n * fraction), replace=False)

    # Nulls: a column suddenly has many missing values.
    df.loc[pick(0.30), "income"] = np.nan

    # Unit change: upstream switched from dollars to cents.
    df["order_amount"] = (df["order_amount"] * 100).round(2)

    # New category: a value the model never saw during training.
    df.loc[pick(0.08), "product_category"] = "crypto"

    # Mean shift: the customer population got older.
    df["age"] = (df["age"] + rng.normal(8, 2, size=n)).clip(18, 90).round().astype(int)

    # Duplicates: some order ids repeated.
    dup_rows = pick(0.02)
    df.loc[dup_rows, "order_id"] = df["order_id"].iloc[(dup_rows + 1) % n].to_numpy()

    # Broken format: emails missing the "@".
    bad = pick(0.05)
    df.loc[bad, "email"] = df.loc[bad, "email"].str.replace("@", "_at_", regex=False)

    return df


def write_sample_data(out_dir: str | Path, n_rows: int = 5_000) -> dict[str, Path]:
    """Write reference.csv, current.csv and faults.json into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reference = generate_orders(n_rows, seed=42, start_date="2026-01-01")
    # Different seed and later dates: a new batch from the same process, then broken.
    current = corrupt(generate_orders(n_rows, seed=7, start_date="2026-04-01"), seed=7)

    paths = {
        "reference": out_dir / "reference.csv",
        "current": out_dir / "current.csv",
        "faults": out_dir / "faults.json",
    }
    reference.to_csv(paths["reference"], index=False)
    current.to_csv(paths["current"], index=False)
    paths["faults"].write_text(json.dumps(FAULTS, indent=2) + "\n")
    return paths
