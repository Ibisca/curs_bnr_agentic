"""Feature engineering utilities for time series forecasting.

Provides functions to create:
- lag features (lag_1, lag_2, ...)
- rolling statistics (rolling_mean_{w}, rolling_std_{w})
- moving averages (ma_7, ma_14)

All functions expect a pandas DataFrame `df` with a DateTimeIndex and a numeric column `rate`.
Missing values created by shifts/rolling can be handled by `fill_method` ('ffill', 'bfill', 'drop')
or by providing a numeric `fill_value`.

Functions return a new DataFrame with the original `rate` column plus new feature columns.
"""
from __future__ import annotations

from typing import Iterable, List, Optional
import logging
from pathlib import Path

import pandas as pd


def _ensure_input(df: pd.DataFrame) -> None:
    if "rate" not in df.columns:
        raise ValueError("DataFrame must contain a 'rate' column")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex")


def create_lag_features(df: pd.DataFrame, lags: Iterable[int]) -> pd.DataFrame:
    """Return a DataFrame with lag features added.

    Parameters
    - df: input DataFrame with `rate` column and DatetimeIndex
    - lags: iterable of positive integers (days) to create lags for

    Returns new DataFrame with columns `lag_{k}` for each k in lags.
    """
    _ensure_input(df)
    df_feat = df.copy()

    for k in sorted(set(int(x) for x in lags)):
        if k <= 0:
            raise ValueError("lags must be positive integers")
        col = f"lag_{k}"
        df_feat[col] = df_feat["rate"].shift(k)
    return df_feat


def create_rolling_features(df: pd.DataFrame, windows: Iterable[int]) -> pd.DataFrame:
    """Add rolling mean and rolling std features for given window sizes (in days).

    Columns added: `roll_mean_{w}`, `roll_std_{w}`
    """
    _ensure_input(df)
    df_feat = df.copy()

    for w in sorted(set(int(x) for x in windows)):
        if w <= 0:
            raise ValueError("window sizes must be positive integers")
        mean_col = f"roll_mean_{w}"
        std_col = f"roll_std_{w}"
        df_feat[mean_col] = df_feat["rate"].rolling(window=w, min_periods=1).mean()
        df_feat[std_col] = df_feat["rate"].rolling(window=w, min_periods=1).std()
    return df_feat


def create_moving_averages(df: pd.DataFrame, windows: Optional[Iterable[int]] = None) -> pd.DataFrame:
    """Add simple moving averages. Default windows = [7, 14].

    Columns added: `ma_{w}`
    """
    if windows is None:
        windows = [7, 14]
    _ensure_input(df)
    df_feat = df.copy()

    for w in sorted(set(int(x) for x in windows)):
        col = f"ma_{w}"
        df_feat[col] = df_feat["rate"].rolling(window=w, min_periods=1).mean()
    return df_feat


def build_features(
    df: pd.DataFrame,
    lags: Optional[Iterable[int]] = (1, 2, 7, 14),
    rolling_windows: Optional[Iterable[int]] = (3, 7, 14),
    ma_windows: Optional[Iterable[int]] = (7, 14),
    fill_method: Optional[str] = "ffill",
    fill_value: Optional[float] = None,
    drop_na: bool = False,
) -> pd.DataFrame:
    """Create a full feature set for modeling.

    Steps:
    - add lag features
    - add rolling mean/std
    - add moving averages
    - handle NaNs created by shift/rolling using `fill_method` or `fill_value`, or drop rows if `drop_na=True`

    Parameters
    - df: input DataFrame with `rate` column and DatetimeIndex
    - lags: iterable of lags to create
    - rolling_windows: iterable of rolling window sizes
    - ma_windows: iterable for moving averages
    - fill_method: 'ffill' | 'bfill' | None. If None, do not fill.
    - fill_value: numeric value to fill NaNs (takes precedence over fill_method if not None)
    - drop_na: if True, drop any rows that still contain NaN after fills

    Returns DataFrame with feature columns.
    """
    df_feat = df.copy()

    if lags:
        df_feat = create_lag_features(df_feat, lags)
    if rolling_windows:
        df_feat = create_rolling_features(df_feat, rolling_windows)
    if ma_windows:
        df_feat = create_moving_averages(df_feat, ma_windows)

    # Handle missing values
    if fill_value is not None:
        logging.info("Filling NaN with fill_value=%s", fill_value)
        df_feat = df_feat.fillna(fill_value)
    elif fill_method in ("ffill", "bfill"):
        logging.info("Filling NaN with method=%s", fill_method)
        df_feat = df_feat.fillna(method=fill_method)
    else:
        logging.info("No fill_method or fill_value provided; leaving NaNs as-is")

    if drop_na:
        before = len(df_feat)
        df_feat = df_feat.dropna()
        after = len(df_feat)
        logging.info("Dropped %d rows containing NaN; remaining %d rows", before - after, after)

    return df_feat


if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser("features")
    parser.add_argument("csv")
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    # try to coerce date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df = df.set_index("date")
    df = df.rename(columns={c: "rate" for c in df.columns if c.lower() in ("rate", "curs", "valoare", "value")})
    df_feat = build_features(df)
    print(df_feat.tail())
