# QualityLens

Data quality and drift monitoring for ML models and data pipelines.

Pipelines rarely crash when their data goes bad. A column starts arriving with 30% nulls, a unit
switches from dollars to cents, or users change their behavior until the training data no longer
looks like reality. Nothing fails loudly. The model's outputs just get worse, and nobody notices for
weeks. QualityLens is built to notice.

It asks two different questions about each new batch of data.

| Question | Typical problems | How it's checked |
|---|---|---|
| **Quality**: is the batch broken? | nulls, duplicates, out-of-range values, schema changes, bad formats | rules you write |
| **Drift**: is the batch different? | shifted mean, new category, changed correlation | statistical tests against a reference dataset |

The reference is usually the model's training data or last month's data.

## Architecture

```
 Reference data ─┐
                 ├─► Profiler ─► Checks engine ─► Results store ─► Dashboard
 New batch ──────┘   (stats)     ├ quality rules   (SQLite/       + Alerts
                                 └ drift tests      Postgres)
```

## Quick start

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.14 for you.

```bash
uv sync
uv run qualitylens sample-data
uv run qualitylens profile data/current.csv --reference data/reference.csv --parse-dates order_date
uv run pytest
```

`sample-data` writes `data/reference.csv`, `data/current.csv` and `data/faults.json`. `profile`
prints the statistics of the current batch as JSON.

## Project structure

```
qualitylens/
├── pyproject.toml
├── src/qualitylens/
│   ├── sample_data.py   # synthetic datasets with injected faults      (done)
│   ├── ingest/          # load CSV and Parquet into DataFrames          (done)
│   ├── profile/         # per-column stats and histograms               (done)
│   ├── quality/         # not_null, range, unique, allowed_values...    (planned)
│   ├── drift/           # PSI, KS test, chi-square, Jensen-Shannon      (planned)
│   ├── report/          # JSON and HTML reports                         (planned)
│   ├── store/           # run history                                   (planned)
│   ├── alerts/          # Slack or email when a check fails             (planned)
│   └── cli.py           # the qualitylens command                       (partial)
├── configs/checks.yaml  # declarative checks, draft format
├── tests/
├── data/                # generated sample data, not committed
├── docs/                # one write-up per build step
└── dashboard/           # Streamlit app, later
```

## Build steps

Each finished step has a longer write-up in [`docs/`](docs/).

### 1. Sample data with known faults (done)

You can't judge a detector without cases where you already know the answer. So the first thing the
project does is generate an orders table twice: a clean **reference**, and a **current** batch that
gets broken on purpose.

| Column | Injected fault | Should be caught by |
|---|---|---|
| `income` | 30% nulls | quality: `not_null` |
| `order_amount` | dollars turned into cents (x100) | quality: `range`, drift: PSI and KS |
| `product_category` | new category `crypto` | quality: `allowed_values`, drift: chi-square |
| `age` | mean up by 8 years | drift: PSI and KS |
| `order_id` | 2% duplicates | quality: `unique` |
| `email` | 5% malformed | quality: `regex` |

The same list is saved to `data/faults.json`. Every later test checks against it.

Look at the `age` row. Every age is still between 18 and 90, so no rule will ever fail on it. Only a
comparison with the reference can catch it, which is why drift detection exists at all.

Details: [docs/01-sample-data.md](docs/01-sample-data.md)

### 2. Profiler (done)

The profiler summarizes each column once: its type, null rate, unique count, min and max, mean,
quantiles, and either a histogram (numbers) or the most frequent values (categories). Quality rules
and drift tests both read from this summary instead of recomputing their own numbers.

One detail matters a lot. A new batch is binned with the reference's histogram edges, otherwise you
can't compare the two bin by bin. Values that fall outside those edges go into the first or last bin
instead of being silently dropped. Without that, the x100 change in `order_amount` would make the
histogram look empty rather than shifted.

Details: [docs/02-profiler.md](docs/02-profiler.md)

### 3. Quality rules (planned)

Small functions like `not_null`, `unique`, `range`, `allowed_values` and `regex`. Each one returns
whether it passed, the value it measured, the threshold, and a few failing rows as examples. The
rules live in `configs/checks.yaml`, so adding a check doesn't mean touching the code.

### 4. Drift detection (planned)

Here the current batch is compared with the reference.

**PSI** (Population Stability Index) works on numeric columns. It sums
`(cur% - ref%) * ln(cur% / ref%)` over the histogram bins. Under 0.1 is stable, 0.1 to 0.2 is a
moderate shift, and above 0.2 is the usual alarm level.

The **KS test** (Kolmogorov-Smirnov) measures the biggest gap between the two cumulative
distributions. A small p-value says the samples probably come from different distributions. With
thousands of rows, though, even a tiny shift becomes "significant", so the statistic itself matters
more than the p-value.

**Chi-square** does the same job for categorical columns: did the category frequencies change? A
category that never existed before is the extreme case.

**Jensen-Shannon distance** gives a symmetric score between 0 and 1 for any pair of histograms. It's
handy on a dashboard.

### 5. Reports (planned)

One JSON result per run, and an HTML page built from it with the pass/fail table and the histograms
side by side.

### 6. Run history (planned)

Every run goes into SQLite, and Postgres later. One run tells you if today's batch is bad. A few
months of runs show drift building up over time, and that's where the tool really pays off.

### 7. Dashboard and alerts (planned)

A Streamlit app to browse runs and trends, and a webhook that posts to Slack or sends an email when
a check fails.

### Later

Scheduling with cron or Airflow, a comparison with Great Expectations and Evidently, and a streaming
mode.
