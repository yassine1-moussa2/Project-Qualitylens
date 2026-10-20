# Step 2: The profiler

Code: [`src/qualitylens/profile/profiler.py`](../src/qualitylens/profile/profiler.py) ·
Tests: [`tests/test_profiler.py`](../tests/test_profiler.py)

## What it does

`profile_dataframe(df)` summarizes each column of a DataFrame into a `ColumnProfile` and collects
them in a `DatasetProfile`:

| Field | All columns | Numeric | Datetime | Categorical / boolean |
|---|---|---|---|---|
| `kind`, `dtype` | ✓ | | | |
| `count`, `null_count`, `null_pct` | ✓ | | | |
| `n_unique` | ✓ | | | |
| `min`, `max` | | ✓ | ✓ (ISO string) | |
| `mean`, `std` | | ✓ | | |
| `quantiles` (p1, p25, p50, p75, p99) | | ✓ | | |
| `histogram` (`bin_edges`, `counts`) | | ✓ | | |
| `top_values` (20 most frequent) | | | | ✓ |

`DatasetProfile.to_dict()` gives a plain dict that can be saved as JSON, and the reports in step 5
will be built on it.

## Why a separate profiling step

Quality rules and drift tests both need the same numbers. A `not_null` rule needs `null_pct`, a
`range` rule needs `min`/`max`, and PSI needs the histogram. If the stats are computed once, the
checks stay tiny and every check reads the same numbers. The profile is also small enough to store
for every run, and that history is what the trend charts in step 6 will use.

## Column kinds

`infer_kind` looks at the pandas dtype:

- `bool` → **boolean** (tested first, because pandas also counts bools as numeric)
- int / float → **numeric**
- datetime → **datetime**
- everything else → **categorical**

A CSV stores dates as text, so pandas reads them as strings and the profiler would call them
categorical. Use `--parse-dates order_date` on the CLI (or `parse_dates=` in `load_table`) so
they are read as dates. Parquet files keep real date types, so they don't need this.

ID columns such as `order_id` come out as "numeric", which is technically true but not useful for
drift. Later, the config will let you mark columns to ignore or override their kind.

## The key detail: shared histogram bins

A histogram depends on its bin edges. If the reference has `age` bins `[18, 25, 32, ...]` and the
current batch picks its own bins `[22, 30, 38, ...]`, you can't compare bin 3 with bin 3.

So when you profile a new batch, you pass the reference profile:

```python
ref = profile_dataframe(reference_df)
cur = profile_dataframe(current_df, reference=ref)   # reuses ref's bin edges
```

There is one more trap. `np.histogram` **silently drops** values outside the edges. In our sample
data `order_amount` was multiplied by 100, so nearly every current value falls beyond the
reference's last edge. Without a fix, the current histogram would be almost empty and look
"different" for the wrong reason, with the counts not adding up to the row count. The profiler
clips values into the outer bins instead, so the shift shows up correctly:

```
order_amount counts (current, reference bins): [0, 0, 1, 2, 3, 3, 6, 6, 2, 4977]
```

Almost everything piles into the last bin, and that is what PSI will flag in step 4.

## What the profiler already catches by itself

Even before any rule exists, profiling `data/current.csv` shows several faults:

- `income.null_pct` ≈ 0.30
- `product_category.top_values` contains `crypto`
- `order_amount.mean` ≈ 7,000 instead of ≈ 70
- `age.mean` ≈ 46 instead of ≈ 38

Steps 3 and 4 turn these observations into automatic pass/fail decisions with thresholds.

## Try it

```bash
uv run qualitylens profile data/current.csv --reference data/reference.csv \
    --parse-dates order_date --out current_profile.json
```
