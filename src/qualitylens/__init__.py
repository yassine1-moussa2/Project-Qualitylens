"""QualityLens: data quality and drift monitoring for ML pipelines.

Two questions, two toolkits:

- Data quality: is this batch broken? Checked against explicit rules (``quality``).
- Drift: is this batch different from what we expect? Checked statistically
  against a reference dataset (``drift``).

Both are built on top of the column statistics computed by ``profile``.
"""

__version__ = "0.1.0"
