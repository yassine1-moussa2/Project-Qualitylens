"""Profile: per-column statistics for a DataFrame.

The profile is the shared input for everything downstream. Quality rules read
null rates and min/max from it; drift tests compare a reference profile with a
current one. Computing stats once, here, keeps the checks small.
"""

from qualitylens.profile.profiler import ColumnProfile, DatasetProfile, profile_dataframe

__all__ = ["ColumnProfile", "DatasetProfile", "profile_dataframe"]
