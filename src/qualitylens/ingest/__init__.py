"""Ingest: turn a file (CSV or Parquet) into a pandas DataFrame.

Every other module works on DataFrames, so this is the only place that needs
to know about file formats. Database tables will be added here later.
"""

from qualitylens.ingest.loaders import load_table

__all__ = ["load_table"]
