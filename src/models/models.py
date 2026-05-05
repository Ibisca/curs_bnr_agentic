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


# ------------------ SARIMA ------------------
def tune_sarima(
    series: pd.Series,
    orders: Iterable[Tuple[int, int, int]] = ((0, 1, 1), (1, 1, 1)),
    seasonal_orders: Iterable[Tuple[int, int, int, int]] = ((0, 0, 0, 0),),
    n_splits: int = 5,
) -> CVResult:
    """Grid-search SARIMA using TimeSeriesSplit.

    series: pd.Series indexed by datetime
    orders: iterable of (p,d,q)
    seasonal_orders: iterable of (P,D,Q,s)

    Returns CVResult with best params and fitted model on full train data (not including final test set).
    """
    if SARIMAX is None:
        raise ImportError("statsmodels is required for SARIMA. Install statsmodels.")

    tscv = time_series_cv_splits(n_splits=n_splits)
    best_score = float("inf")
    best_cfg = None
    best_seasonal = None

    # Prepare numpy array
    y = series.dropna().astype(float)
    if y.empty:
        raise ValueError("Empty series for SARIMA tuning")

    logging.info("Start SARIMA grid search: orders=%s seasonal=%s", orders, seasonal_orders)

    for order in orders:
        for seasonal_order in seasonal_orders:
            cv_metrics = []
            try:
                for train_idx, val_idx in tscv.split(y):
                    y_train = y.iloc[train_idx]
                    y_val = y.iloc[val_idx]
                    # Fit SARIMAX
                    try:
                        model = SARIMAX(y_train, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
                        res = model.fit(disp=False)
                        # Forecast horizon
                        steps = len(y_val)
                        pred = res.get_forecast(steps=steps).predicted_mean
                        pred.index = y_val.index
                        metrics = compute_metrics(y_val.values, pred.values)
                        cv_metrics.append(metrics["MAE"])  # use MAE for selection
                    except Exception as e:
                        logging.debug("SARIMA fit/forecast failed for order=%s seasonal=%s: %s", order, seasonal_order, e)
                        cv_metrics.append(float("inf"))
                        break
                mean_cv = np.mean(cv_metrics)
                logging.info("SARIMA order=%s seasonal=%s mean MAE=%.4f", order, seasonal_order, mean_cv)
                if mean_cv < best_score:
                    best_score = mean_cv
                    best_cfg = order
                    best_seasonal = seasonal_order
            except Exception as e:
                logging.exception("Error during SARIMA grid iteration: %s", e)
                continue

    if best_cfg is None:
        raise RuntimeError("No valid SARIMA configuration found")

    logging.info("Best SARIMA: order=%s seasonal=%s (MAE=%.4f)", best_cfg, best_seasonal, best_score)
    # retrain on full series
    final_model = SARIMAX(y, order=best_cfg, seasonal_order=best_seasonal, enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)

    # compute in-sample fit metrics
    in_sample_pred = final_model.fittedvalues
    metrics = compute_metrics(y.values, in_sample_pred.values)

    return CVResult(name="SARIMA", best_params={"order": best_cfg, "seasonal_order": best_seasonal}, metrics=metrics, model=final_model)


# ------------------ Prophet ------------------
def tune_prophet(
    series: pd.Series,
    grid: Optional[Dict[str, Iterable[Any]]] = None,
    n_splits: int = 5,
) -> CVResult:
    if Prophet is None:
        raise ImportError("prophet library is required. Install prophet.")

    if grid is None:
        grid = {
            "changepoint_prior_scale": [0.001, 0.01, 0.1, 0.5],
            "seasonality_prior_scale": [0.01, 0.1, 1.0, 10.0],
            "seasonality_mode": ["additive", "multiplicative"],
            "holidays_prior_scale": [0.01, 0.1, 1.0],
            "changepoint_range": [0.8, 0.9],
        }

    # Build list of param combinations
    from itertools import product

    keys = list(grid.keys())
    combos = list(product(*(grid[k] for k in keys)))

    tscv = time_series_cv_splits(n_splits=n_splits)
    y = series.dropna().astype(float)
    df_all = y.reset_index().rename(columns={"date": "ds", "rate": "y"}) if "date" in y.index.name else y.reset_index().rename(columns={y.index.name or "index": "ds", 0: "y"})

    # But simpler: create df with index to column conversion
    df_prophet = pd.DataFrame({"ds": y.index, "y": y.values})

    best_score = float("inf")
    best_params: Dict[str, Any] = {}

    logging.info("Start Prophet grid search: %d combos", len(combos))

    for combo in combos:
        params = dict(zip(keys, combo))
        cv_scores = []
        try:
            for train_idx, val_idx in tscv.split(df_prophet):
                train_df = df_prophet.iloc[train_idx]
                val_df = df_prophet.iloc[val_idx]
                m = Prophet(
                    changepoint_prior_scale=params.get("changepoint_prior_scale", 0.05),
                    seasonality_prior_scale=params.get("seasonality_prior_scale", 10.0),
                    seasonality_mode=params.get("seasonality_mode", "additive"),
                    holidays_prior_scale=params.get("holidays_prior_scale", 10.0),
                    changepoint_range=params.get("changepoint_range", 0.8),
                )
                # fit
                m.fit(train_df)
                # predict
                future = val_df[["ds"]]
                forecast = m.predict(future)
                y_true = val_df["y"].values
                y_pred = forecast["yhat"].values
                metrics = compute_metrics(y_true, y_pred)
                cv_scores.append(metrics["MAE"])  # select by MAE
            mean_cv = np.mean(cv_scores)
            logging.info("Prophet params=%s mean MAE=%.4f", params, mean_cv)
            if mean_cv < best_score:
                best_score = mean_cv
                best_params = params
        except Exception as e:
            logging.debug("Prophet combo failed %s: %s", params, e)
            continue

    if not best_params:
        raise RuntimeError("No valid Prophet parameters found")

    logging.info("Best Prophet params=%s (MAE=%.4f)", best_params, best_score)

    # Retrain on full series
    m_final = Prophet(
        changepoint_prior_scale=best_params.get("changepoint_prior_scale", 0.05),
        seasonality_prior_scale=best_params.get("seasonality_prior_scale", 10.0),
        seasonality_mode=best_params.get("seasonality_mode", "additive"),
        holidays_prior_scale=best_params.get("holidays_prior_scale", 10.0),
        changepoint_range=best_params.get("changepoint_range", 0.8),
    )
    m_final.fit(df_prophet)
    # in-sample predict
    in_sample = m_final.predict(df_prophet[["ds"]])
    metrics = compute_metrics(df_prophet["y"].values, in_sample["yhat"].values)

    return CVResult(name="Prophet", best_params=best_params, metrics=metrics, model=m_final)


# ------------------ XGBoost ------------------
def tune_xgboost(
    df_features: pd.DataFrame,
    param_grid: Optional[Dict[str, Iterable[Any]]] = None,
    n_splits: int = 5,
    metric_to_select: str = "MAE",
) -> CVResult:
    if xgb is None:
        raise ImportError("xgboost is required for XGBoost model. Install xgboost.")

    # df_features: indexed by datetime, must contain 'rate'
    if "rate" not in df_features.columns:
        raise ValueError("df_features must contain 'rate' column")

    X = df_features.drop(columns=["rate"]).values
    y = df_features["rate"].values

    if param_grid is None:
        param_grid = {
            "eta": [0.01, 0.1],
            "gamma": [0, 0.1],
            "subsample": [0.7, 1.0],
            "n_estimators": [50, 100, 200],
            "max_depth": [4, 5, 6],
        }

    # build combos
    from itertools import product

    keys = list(param_grid.keys())
    combos = list(product(*(param_grid[k] for k in keys)))

    tscv = time_series_cv_splits(n_splits=n_splits)
    best_score = float("inf")
    best_params: Dict[str, Any] = {}

    logging.info("Start XGBoost grid search: %d combos", len(combos))

    # Need indexable arrays for tscv
    for combo in combos:
        params = dict(zip(keys, combo))
        cv_scores = []
        try:
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                model = xgb.XGBRegressor(
                    objective="reg:squarederror",
                    learning_rate=params.get("eta", 0.1),
                    gamma=params.get("gamma", 0),
                    subsample=params.get("subsample", 1.0),
                    n_estimators=int(params.get("n_estimators", 100)),
                    max_depth=int(params.get("max_depth", 6)),
                    verbosity=0,
                )
                model.fit(X_train, y_train)
                pred = model.predict(X_val)
                metrics = compute_metrics(y_val, pred)
                cv_scores.append(metrics[metric_to_select])
            mean_cv = np.mean(cv_scores)
            logging.info("XGB params=%s mean %s=%.4f", params, metric_to_select, mean_cv)
            if mean_cv < best_score:
                best_score = mean_cv
                best_params = params
        except Exception as e:
            logging.debug("XGBoost combo failed %s: %s", params, e)
            continue

    if not best_params:
        raise RuntimeError("No valid XGBoost parameters found")

    logging.info("Best XGBoost params=%s (cv %s=%.4f)", best_params, metric_to_select, best_score)

    # retrain final model on full data
    final_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        learning_rate=best_params.get("eta", 0.1),
        gamma=best_params.get("gamma", 0),
        subsample=best_params.get("subsample", 1.0),
        n_estimators=int(best_params.get("n_estimators", 100)),
        max_depth=int(best_params.get("max_depth", 6)),
        verbosity=0,
    )
    final_model.fit(X, y)
    in_sample_pred = final_model.predict(X)
    metrics = compute_metrics(y, in_sample_pred)

    return CVResult(name="XGBoost", best_params=best_params, metrics=metrics, model=final_model)


# ------------------ Utilities ------------------
def select_best_model(results: List[CVResult], metric: str = "MAE") -> CVResult:
    best = None
    best_val = float("inf")
    for r in results:
        v = r.metrics.get(metric)
        if v is None:
            continue
        if v < best_val:
            best_val = v
            best = r
    if best is None:
        raise ValueError("No models with the requested metric found")
    logging.info("Selected best model: %s with %s=%.4f", best.name, metric, best_val)
    return best


def save_model(obj: Any, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # prefer joblib for sklearn/xgboost, pickle for statsmodels/prophet
    try:
        joblib.dump(obj, path)
    except Exception:
        with open(path, "wb") as f:
            pickle.dump(obj, f)
    logging.info("Model salvat: %s", path)
    return path


if __name__ == "__main__":
    import argparse
    from src.data_loader import load_raw, preprocess, split_train_val_test
    from src.features import build_features

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="cale către fișierul CSV preprocesat")
    args = parser.parse_args()

    df_raw = load_raw(args.csv)
    df = preprocess(df_raw)
    train, val, test = split_train_val_test(df, test_days=14)

    # build features for XGBoost using train only
    df_feat = build_features(train, drop_na=True)

    results: List[CVResult] = []
    # SARIMA
    try:
        res_sarima = tune_sarima(train["rate"], orders=[(0, 1, 1), (1, 1, 1), (2, 1, 2)], seasonal_orders=[(0, 0, 0, 0), (1, 0, 1, 7)], n_splits=3)
        results.append(res_sarima)
    except Exception as e:
        logging.exception("SARIMA training failed: %s", e)

    # Prophet
    try:
        res_prophet = tune_prophet(train["rate"], n_splits=3)
        results.append(res_prophet)
    except Exception as e:
        logging.exception("Prophet training failed: %s", e)

    # XGBoost
    try:
        res_xgb = tune_xgboost(df_feat, n_splits=3)
        results.append(res_xgb)
    except Exception as e:
        logging.exception("XGBoost training failed: %s", e)

    for r in results:
        logging.info("Model %s in-sample metrics: %s", r.name, r.metrics)

    if results:
        best = select_best_model(results, metric="MAE")
        save_model(best.model, Path("models") / f"best_model_{best.name}.pkl")
        logging.info("Best model saved: %s", best.name)
    else:
        logging.error("No models trained successfully.")
