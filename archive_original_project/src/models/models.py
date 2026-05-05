"""Model training and evaluation for SARIMA, Prophet, and XGBoost.

Features and data conventions
- Input training data for SARIMA/Prophet: a pandas Series or DataFrame with DatetimeIndex and column `rate`.
- For XGBoost, provide a DataFrame with features (output of `features.build_features`) indexed by datetime and containing `rate`.

This module provides:
- cross-validated grid search using TimeSeriesSplit
- metric reporting (MAE, RMSE, MAPE)
- training final models on full training data with best hyperparameters
- saving models with joblib/pickle

Note: heavy computations (SARIMA grid) may be slow depending on data size.
"""
from __future__ import annotations

import logging
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

# Optional imports that may not be installed in all environments
try:
    import xgboost as xgb
except Exception:  # pragma: no cover - dependency handling
    xgb = None

try:
    from prophet import Prophet
except Exception:  # pragma: no cover
    Prophet = None

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
except Exception:  # pragma: no cover
    SARIMAX = None


@dataclass
class CVResult:
    name: str
    best_params: Dict[str, Any]
    metrics: Dict[str, float]
    model: Any


def mape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    denom = np.where(np.abs(y_true) < 1e-9, 1e-9, np.abs(y_true))
    return np.mean(np.abs((y_true - y_pred) / denom)) * 100.0


def compute_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> Dict[str, float]:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    mape_v = mape(y_true, y_pred)
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape_v}


def time_series_cv_splits(n_splits: int = 5) -> TimeSeriesSplit:
    return TimeSeriesSplit(n_splits=n_splits)

# (rest omitted in archive copy to keep snapshot small)
