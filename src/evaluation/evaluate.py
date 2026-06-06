"""Evaluate the best model on the final 14 days and prepare forecast results.

Responsibilities:
- load data CSV and preprocess
- split last 14 days as test set
- load best saved model (auto-detect or via --model)
- generate predictions for test period
- compute metrics (MAE, RMSE, MAPE)
- produce prediction intervals (model-native for SARIMA/Prophet, bootstrap for XGBoost)
- save predictions CSV in `data/` and prepare data suitable for Plotly visualization

Usage:
python -m src.evaluation.evaluate --csv data/HRK_...csv [--model models/best_model_X.pkl] [--bootstrap 50]
"""
from __future__ import annotations

import argparse
import glob
import logging
import math
import os
import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from src.data.data_loader import load_raw, preprocess, split_train_val_test
from src.features.features import build_features
from src.models.models import compute_metrics

try:
    import xgboost as xgb
except Exception:
    xgb = None

try:
    from prophet import Prophet
except Exception:
    Prophet = None

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAXResults
except Exception:
    SARIMAXResults = None


LOG = logging.getLogger(__name__)


def load_model(path: Path) -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        return joblib.load(path)
    except Exception:
        with open(path, "rb") as f:
            return pickle.load(f)


def find_latest_best_model(models_dir: Path = Path("models")) -> Optional[Path]:
    models_dir = Path(models_dir)
    if not models_dir.exists():
        return None
    files = list(models_dir.glob("best_model_*.pkl"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def predict_sarima(model: Any, steps: int, test_index: pd.DatetimeIndex) -> pd.DataFrame:
    # model is SARIMAXResults
    pred = model.get_forecast(steps=steps)
    mean = pred.predicted_mean
    ci = pred.conf_int(alpha=0.05)
    df = pd.DataFrame({"pred": mean, "lower": ci.iloc[:, 0], "upper": ci.iloc[:, 1]})
    # align index
    df.index = test_index
    return df


def predict_prophet(model: Any, test_index: pd.DatetimeIndex) -> pd.DataFrame:
    # model is Prophet fitted
    df_future = pd.DataFrame({"ds": test_index})
    forecast = model.predict(df_future)
    df = pd.DataFrame({"pred": forecast["yhat"].values, "lower": forecast.get("yhat_lower", np.nan), "upper": forecast.get("yhat_upper", np.nan)})
    df.index = test_index
    return df


def predict_xgboost_with_ci(trained_params: Dict[str, Any], train_df: pd.DataFrame, test_df: pd.DataFrame, bootstrap: int = 50) -> pd.DataFrame:
    """Produce predictions and bootstrap-based prediction intervals for XGBoost.

    trained_params: dict of parameters to pass to XGBRegressor constructor
    train_df: DataFrame with features and 'rate' column
    test_df: DataFrame with features and 'rate' column (rate may contain true values)

    Returns DataFrame indexed by test_df.index with columns pred, lower, upper
    """
    if xgb is None:
        raise ImportError("xgboost not available")

    X_train = train_df.drop(columns=["rate"]).values
    y_train = train_df["rate"].values
    X_test = test_df.drop(columns=["rate"]).values

    preds = np.zeros((bootstrap, len(X_test)))
    n = len(X_train)
    rng = np.random.RandomState(42)

    for i in range(bootstrap):
        idx = rng.randint(0, n, size=n)
        X_b = X_train[idx]
        y_b = y_train[idx]
        model = xgb.XGBRegressor(**trained_params, verbosity=0)
        model.fit(X_b, y_b)
        preds[i] = model.predict(X_test)

    mean_pred = preds.mean(axis=0)
    lower = np.percentile(preds, 2.5, axis=0)
    upper = np.percentile(preds, 97.5, axis=0)

    df = pd.DataFrame({"pred": mean_pred, "lower": lower, "upper": upper}, index=test_df.index)
    return df


def prepare_plot_df(train: pd.DataFrame, test: pd.DataFrame, pred_df: pd.DataFrame) -> pd.DataFrame:
    """Combine observed and predicted into a single DataFrame for plotting with Plotly.

    Columns: date(index), observed (test.rate), predicted, lower, upper
    Also include historical train series if desired in plotting code.
    """
    df_plot = pd.DataFrame(index=train.index.union(test.index))
    df_plot["observed"] = pd.concat([train["rate"], test["rate"]]).reindex(df_plot.index)
    # fill predicted only for test index
    df_plot = df_plot.assign(predicted=np.nan, lower=np.nan, upper=np.nan)
    df_plot.loc[pred_df.index, "predicted"] = pred_df["pred"].values
    df_plot.loc[pred_df.index, "lower"] = pred_df["lower"].values
    df_plot.loc[pred_df.index, "upper"] = pred_df["upper"].values
    return df_plot


def save_predictions(pred_df: pd.DataFrame, model_name: str, csv_dir: Path = Path("data")) -> Path:
    csv_dir.mkdir(parents=True, exist_ok=True)
    filename = csv_dir / f"predictions_{model_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pred_df_out = pred_df.copy()
    pred_df_out = pred_df_out.reset_index().rename(columns={"index": "date"})
    pred_df_out.to_csv(filename, index=False)
    LOG.info("Saved predictions to %s", filename)
    return filename


def evaluate_best_model(csv_path: Path, model_path: Optional[Path] = None, bootstrap: int = 50) -> Tuple[Path, Dict[str, float]]:
    """Main entry point: load data, preprocess, load model, predict on last 14 days, compute metrics, save predictions, return path and metrics"""
    df_raw = load_raw(csv_path)
    df = preprocess(df_raw)

    train, val, test = split_train_val_test(df, test_days=14)
    if test.empty:
        raise ValueError("Test set (last 14 days) is empty")

    if model_path is None:
        model_path = find_latest_best_model()
    if model_path is None:
        raise FileNotFoundError("No model found in models/ and no --model provided")

    LOG.info("Using model file: %s", model_path)
    model = load_model(model_path)

    model_name = Path(model_path).stem.replace("best_model_", "")

    # Prepare predictions depending on model type/name
    if "SARIMA" in model_name.upper() or SARIMAXResults and isinstance(model, SARIMAXResults):
        LOG.info("Detected SARIMA model; using SARIMA prediction path")
        pred_df = predict_sarima(model, steps=len(test), test_index=test.index)
    elif "PROPHET" in model_name.upper() or (Prophet is not None and isinstance(model, Prophet)):
        LOG.info("Detected Prophet model; using Prophet prediction path")
        pred_df = predict_prophet(model, test.index)
    elif "XGBOOST" in model_name.upper() or (xgb is not None and hasattr(model, "predict") and hasattr(model, "get_booster")):
        LOG.info("Detected XGBoost model; building features for train+test and running bootstrap CI")
        # build features on full data (train + test) to ensure lags available
        df_full = pd.concat([train, test]).sort_index()
        df_feat_full = build_features(df_full, drop_na=False, fill_method="ffill")
        # split back
        train_feat = df_feat_full.loc[train.index].dropna()
        test_feat = df_feat_full.loc[test.index].dropna()
        if test_feat.empty:
            # try without dropping na and forward fill
            df_feat_full = build_features(df_full, drop_na=False, fill_method="ffill")
            train_feat = df_feat_full.loc[train.index]
            test_feat = df_feat_full.loc[test.index]
        # extract model params if possible
        trained_params = {}
        try:
            trained_params = model.get_params()
            # remove attributes that are not accepted by constructor
            for k in list(trained_params.keys()):
                if k in ("objective", "verbosity"):
                    # keep objective
                    continue
        except Exception:
            trained_params = {}
        # keep only relevant params as per models tune defaults
        allowed = ["learning_rate", "gamma", "subsample", "n_estimators", "max_depth"]
        params = {k: trained_params[k] for k in trained_params if k in allowed}
        # map learning_rate -> eta
        if "learning_rate" in params:
            params["learning_rate"] = params.pop("learning_rate")
        # fallback defaults
        defaults = {"learning_rate": 0.1, "gamma": 0, "subsample": 1.0, "n_estimators": 100, "max_depth": 6}
        for k, v in defaults.items():
            params.setdefault(k, v)
        pred_df = predict_xgboost_with_ci(params, train_feat, test_feat, bootstrap=bootstrap)
    else:
        # unknown model type: try generic predict if it supports get_forecast or predict
        LOG.info("Unknown model type; attempting generic predict on test index")
        try:
            if hasattr(model, "get_forecast"):
                pred_df = predict_sarima(model, steps=len(test), test_index=test.index)
            elif hasattr(model, "predict"):
                # prepare features
                df_full = pd.concat([train, test]).sort_index()
                df_feat_full = build_features(df_full, drop_na=False, fill_method="ffill")
                test_feat = df_feat_full.loc[test.index].dropna()
                preds = model.predict(test_feat.drop(columns=["rate"]).values)
                pred_df = pd.DataFrame({"pred": preds, "lower": np.nan, "upper": np.nan}, index=test_feat.index)
            else:
                raise RuntimeError("Model does not support known predict interfaces")
        except Exception as e:
            LOG.exception("Generic prediction failed: %s", e)
            raise

    # Align predictions with true test values
    # Some methods may return predictions for subset of test index; join accordingly
    pred_df = pred_df.reindex(test.index)

    # compute metrics on rows where we have predictions and true values
    mask = ~pred_df["pred"].isna() & ~test["rate"].isna()
    if not mask.any():
        raise RuntimeError("No overlapping predictions and true values to compute metrics")

    y_true = test.loc[mask, "rate"].values
    y_pred = pred_df.loc[mask, "pred"].values
    metrics = compute_metrics(y_true, y_pred)

    LOG.info("Evaluation on last %d days: %s", len(y_true), metrics)

    # Save predictions
    save_df = pd.DataFrame({"date": pred_df.index, "observed": test["rate"].reindex(pred_df.index).values, "pred": pred_df["pred"].values, "lower": pred_df["lower"].values, "upper": pred_df["upper"].values})
    out_path = Path("data") / f"evaluation_predictions_{model_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_df.to_csv(out_path, index=False)
    LOG.info("Saved evaluation predictions to %s", out_path)

    # Prepare plot data
    plot_df = prepare_plot_df(train, test, pred_df)
    plot_path = Path("data") / f"plot_data_{model_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    plot_df.reset_index().rename(columns={"index": "date"}).to_csv(plot_path, index=False)
    LOG.info("Saved plot-ready data to %s", plot_path)

    return out_path, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="path to CSV file with data (raw scraped)")
    parser.add_argument("--model", required=False, help="path to saved model (optional). If not provided, the latest model in models/ will be used")
    parser.add_argument("--bootstrap", type=int, default=50, help="number of bootstrap re-trains for XGBoost CI")
    args = parser.parse_args()

    model_path = Path(args.model) if args.model else None
    csv_path = Path(args.csv)
    try:
        out_csv, metrics = evaluate_best_model(csv_path, model_path, bootstrap=args.bootstrap)
        logging.info("Done. Predictions saved to %s. Metrics: %s", out_csv, metrics)
    except Exception as e:
        logging.exception("Evaluation failed: %s", e)
        raise
