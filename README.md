# QualityLens

Data quality and drift monitoring for ML models and data pipelines.

ML models and data pipelines usually fail without crashing. A column starts arriving with 30% nulls, a unit
changes from dollars to cents, or user behavior shifts until the training data no longer matches
reality. The outputs just get worse. QualityLens watches for these failures.

It answers two separate questions:

| Question | Example problems | How it is checked |
|---|---|---|
| **Data quality**: is this batch broken? | nulls, duplicates, out-of-range values, schema changes, broken formats | explicit **rules** you write |
| **Drift**: is this batch different from what we expect? | shifted mean, new category, changed correlation | **statistical tests** against a reference dataset (training data, last month...) |

## Architecture

```
 Reference data ─┐
                 ├─► Profiler ─► Checks engine ─► Results store ─► Dashboard
 New batch ──────┘   (stats)     ├ quality rules   (SQLite/       + Alerts
                                 └ drift tests      Postgres)
```

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.14 for you).

```bash
uv sync                                   # install dependencies
uv run qualitylens sample-data            # write data/reference.csv, data/current.csv, data/faults.json
uv run qualitylens profile data/current.csv --reference data/reference.csv --parse-dates order_date
uv run pytest                             # run the test suite
```

## Project structure

```
qualitylens/
├── pyproject.toml
├── src/qualitylens/
│   ├── sample_data.py # synthetic datasets with injected faults (ground truth)   ✅
│   ├── ingest/        # load CSV/Parquet into DataFrames                          ✅
│   ├── profile/       # per-column stats: dtype, nulls, min/max, histograms      ✅
│   ├── quality/       # rules: not_null, range, unique, allowed_values, schema   ⏳
│   ├── drift/         # PSI, KS test, chi-square, Jensen-Shannon                 ⏳
│   ├── report/        # result objects, JSON + HTML reports                      ⏳
│   ├── store/         # run history                                              ⏳
│   ├── alerts/        # Slack/email when a check fails                           ⏳
│   └── cli.py         # `qualitylens <command>`                                  ✅ (partial)
├── configs/checks.yaml  # declarative checks (draft format)
├── tests/               # tests built on the synthetic faults
├── data/                # generated sample data
├── docs/                # detailed explanation of each build step
└── dashboard/           # Streamlit app (later)
```

## Build steps

Each step has a detailed write-up in [`docs/`](docs/). The short version:

### 1. Sample data with known faults ✅ ([details](docs/01-sample-data.md))

You can't test a monitoring tool without data where you already know what is wrong. `sample_data.py`
generates a clean **reference** orders table and a **current** table from the same generator, then
breaks the current one on purpose:

| Column | Injected fault | Should be caught by |
|---|---|---|
| `income` | 30% nulls | quality: `not_null` |
| `order_amount` | dollars → cents (×100) | quality: `range`, drift: PSI/KS |
| `product_category` | new category `crypto` | quality: `allowed_values`, drift: chi-square |
| `age` | mean +8 years | drift: PSI/KS |
| `order_id` | 2% duplicates | quality: `unique` |
| `email` | 5% malformed | quality: `regex` |

This table is also written to `data/faults.json` and is the ground truth for every later test.

### 2. Profiler ✅ ([details](docs/02-profiler.md))

The profiler turns a DataFrame into a `DatasetProfile`: one `ColumnProfile` per column with its kind
(numeric / categorical / datetime / boolean), null rate, unique count, min/max, mean/std, quantiles,
a histogram (numeric) or top values (categorical). Every later check reads from this profile, so
statistics are computed only once.

When you profile a new batch, you pass the reference profile so the batch is binned with the
**same histogram edges**. Two histograms can only be compared bin by bin if they share edges, and
PSI in step 4 depends on that.

### 3. Quality rules ⏳

Small functions such as `not_null`, `unique`, `range`, `allowed_values` and `regex`. Each returns a
result object (`passed`, the observed value, the threshold, a few failing examples). The rules are
listed in `configs/checks.yaml`, so you can add a check without changing any code.

### 4. Drift detection ⏳

This step compares the current batch against the reference:

- **PSI** (Population Stability Index), numeric columns: `Σ (cur% − ref%) · ln(cur% / ref%)` over the
  histogram bins. Below 0.1 means stable, 0.1 to 0.2 means moderate shift, and **above 0.2 is the
  usual alarm level**.
- **KS test** (Kolmogorov–Smirnov), numeric columns: the largest gap between the two cumulative
  distributions. A small p-value means the samples probably come from different distributions.
  With large samples even tiny shifts become "significant", so read the statistic as well as
  the p-value.
- **Chi-square**, categorical columns: tests whether the category frequencies changed. A brand-new
  category is the extreme case.
- **Jensen–Shannon distance**: a symmetric similarity score bounded between 0 and 1 that works on any
  histogram. It is useful for dashboards.

### 5. Reports ⏳

Every run writes one JSON result. Step 5 also renders an HTML summary from it, with a pass/fail
table and the histograms side by side.

### 6. Persistence and history ⏳

Every run is stored in SQLite (Postgres later). A single run tells you whether today's batch is
bad. History shows **drift over time**, and that trend is the real value of the tool.

### 7. Dashboard and alerts ⏳

A Streamlit app to browse runs and trends, plus a webhook (Slack/email) when a check fails.

### Later

Scheduling (cron/Airflow), comparison with Great Expectations / Evidently, streaming mode.
