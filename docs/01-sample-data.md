# Step 1: Sample data with known faults

Code: [`src/qualitylens/sample_data.py`](../src/qualitylens/sample_data.py) ·
Tests: [`tests/test_sample_data.py`](../tests/test_sample_data.py)

## Why start here

A monitoring tool is a detector, and you can only measure a detector against cases where you
already know the answer. If you start from real production data, you never know whether a check
that passed means the data is fine or the check is broken. So before writing any check, we build
datasets where every problem is **put there on purpose and written down**.

## Why synthetic instead of a Kaggle CSV

A public CSV works too, and swapping one in later is easy. A generator has three advantages
for now:

- **Reproducible**: the same seed always gives the same table, so test results stay stable.
- **Controllable**: the "true" distributions are known, e.g. age ~ Normal(38, 11). When drift
  detection reports a shift of about 8 years, we know it is right.
- **No download**: tests run offline and in CI.

## The dataset

An e-commerce orders table with columns of every kind the tool must handle:

| Column | Kind | Generated as |
|---|---|---|
| `order_id` | numeric id | sequential, must be unique |
| `customer_id` | numeric id | random integers |
| `age` | numeric | Normal(38, 11), clipped to 18–90 |
| `income` | numeric, skewed | Log-normal (most incomes are modest, a few are very large) |
| `country` | categorical | 6 countries with fixed weights |
| `product_category` | categorical | 5 categories with fixed weights |
| `order_amount` | numeric, skewed | Gamma(2, 35) + 1, in dollars |
| `email` | text with a format | `user<id>@example.com` |
| `order_date` | datetime | random day in a 90-day window |

## Reference vs current

- **Reference** (`seed=42`, starting January): what "normal" looks like. In real life this is
  usually the model's training data or last month's data.
- **Current** (`seed=7`, starting April): a new batch from the *same* process, so without the
  corruption it would differ only by random sampling noise. Then `corrupt()` breaks it.

Using a different seed matters. If current were a corrupted copy of the reference, the drift tests
would never see natural sampling noise, and we could not check that they **don't** raise false
alarms on healthy data.

## The injected faults

Each fault imitates a real-world failure:

| Fault | Real-world cause | Type of check that should catch it |
|---|---|---|
| `income` 30% null | upstream join broke, or a form field became optional | quality: not_null |
| `order_amount` ×100 | an API switched from dollars to cents | quality: range, and drift |
| `product_category` gets `crypto` | a new product line launched | quality: allowed_values, and drift |
| `age` mean +8 | marketing reached an older audience | drift only: every value is still valid |
| `order_id` 2% duplicates | a retry loaded the same rows twice | quality: unique |
| `email` 5% malformed | a frontend change broke validation | quality: regex |

The `age` fault is the important one. **No rule fails**, because every age is still between 18 and
90. Only a statistical comparison with the reference can catch it, and that shows why drift
detection exists as a separate tool next to quality rules.

## Try it

```bash
uv run qualitylens sample-data      # writes data/reference.csv, data/current.csv, data/faults.json
```
