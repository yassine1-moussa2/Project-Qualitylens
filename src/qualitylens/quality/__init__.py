"""Quality: rule-based checks that answer "is this batch broken?" (step 3).

Planned rules, each returning pass/fail plus details:
not_null, range, unique, allowed_values, regex (format), schema.
Rules are declared in configs/checks.yaml, not hard-coded.
"""
