from pathlib import Path

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".parquet", ".pq"}


def load_table(path: str | Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    """Load a CSV or Parquet file into a DataFrame.

    ``parse_dates`` only matters for CSV: Parquet already stores real date types,
    but in a CSV every date is just text until we tell pandas otherwise.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        if parse_dates:
            columns = pd.read_csv(path, nrows=0).columns
            missing = [c for c in parse_dates if c not in columns]
            if missing:
                raise ValueError(
                    f"Date column(s) {missing} not found in {path}. "
                    f"Available columns: {', '.join(columns)}"
                )
        return pd.read_csv(path, parse_dates=parse_dates or False)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)

    raise ValueError(
        f"Unsupported file type '{suffix}' for {path}. "
        f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
    )
