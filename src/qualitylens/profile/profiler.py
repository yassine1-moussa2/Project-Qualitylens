from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

ColumnKind = Literal["numeric", "categorical", "datetime", "boolean"]

# How many most-frequent values to keep for categorical columns.
TOP_K = 20
DEFAULT_BINS = 10


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    kind: ColumnKind
    count: int
    null_count: int
    null_pct: float
    n_unique: int
    # Numeric and datetime columns
    min: Any = None
    max: Any = None
    # Numeric only
    mean: float | None = None
    std: float | None = None
    quantiles: dict[str, float] = field(default_factory=dict)
    histogram: dict[str, list[float]] = field(default_factory=dict)
    # Categorical and boolean only
    top_values: dict[str, int] = field(default_factory=dict)


@dataclass
class DatasetProfile:
    n_rows: int
    n_columns: int
    columns: dict[str, ColumnProfile]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_kind(series: pd.Series) -> ColumnKind:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    return "categorical"


def _numeric_stats(values: pd.Series, bin_edges: list[float] | None) -> dict[str, Any]:
    if values.empty:
        return {}

    # Reusing the reference bin edges for the current batch is what makes two
    # histograms comparable, which PSI needs in step 4.
    if bin_edges is None:
        edges = np.histogram_bin_edges(values, bins=DEFAULT_BINS)
        counts, edges = np.histogram(values, bins=edges)
    else:
        # np.histogram silently drops values outside the edges. Clip them into
        # the outer bins instead, otherwise a batch that moved far away from
        # the reference would look empty rather than drifted.
        edges = np.asarray(bin_edges)
        counts, edges = np.histogram(values.clip(edges[0], edges[-1]), bins=edges)

    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "quantiles": {f"p{int(q * 100)}": float(values.quantile(q)) for q in (0.01, 0.25, 0.5, 0.75, 0.99)},
        "histogram": {"bin_edges": [float(e) for e in edges], "counts": [int(c) for c in counts]},
    }


def profile_column(series: pd.Series, bin_edges: list[float] | None = None) -> ColumnProfile:
    kind = infer_kind(series)
    count = len(series)
    null_count = int(series.isna().sum())
    non_null = series.dropna()

    profile = ColumnProfile(
        name=str(series.name),
        dtype=str(series.dtype),
        kind=kind,
        count=count,
        null_count=null_count,
        null_pct=null_count / count if count else 0.0,
        n_unique=int(non_null.nunique()),
    )

    if kind == "numeric":
        for key, value in _numeric_stats(non_null.astype(float), bin_edges).items():
            setattr(profile, key, value)
    elif kind == "datetime" and not non_null.empty:
        profile.min = non_null.min().isoformat()
        profile.max = non_null.max().isoformat()
    else:
        top = non_null.astype(str).value_counts().head(TOP_K)
        profile.top_values = {str(k): int(v) for k, v in top.items()}

    return profile


def profile_dataframe(
    df: pd.DataFrame, reference: DatasetProfile | None = None
) -> DatasetProfile:
    """Compute a ``DatasetProfile`` for every column of ``df``.

    Pass the reference profile when profiling a new batch, so numeric
    histograms use the same bin edges as the reference.
    """
    columns = {}
    for name in df.columns:
        bin_edges = None
        if reference is not None and name in reference.columns:
            bin_edges = reference.columns[name].histogram.get("bin_edges")
        columns[str(name)] = profile_column(df[name], bin_edges=bin_edges)

    return DatasetProfile(n_rows=len(df), n_columns=len(df.columns), columns=columns)
