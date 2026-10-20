"""Drift: statistical tests that answer "is this batch different?" (step 4).

Planned tests, comparing a current batch against a reference dataset:
PSI and Kolmogorov-Smirnov for numeric columns, chi-square for categorical
ones, Jensen-Shannon distance as a bounded similarity score.
"""
