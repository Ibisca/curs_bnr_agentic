"""Optuna-based hyperparameter tuning for XGBoost (TimeSeriesSplit).

This module exposes `optuna_tune_xgboost(df_features, n_splits=3, n_trials=50, timeout=None, random_state=None)`
which returns a `CVResult`-like object (from `src.models.models.CVResult`) containing the trained final model,
best_params and in-sample metrics. It also saves a results JSON in `models/` with timestamp.

Design notes:
- import `optuna` inside the function to avoid top-level import errors when Optuna is not installed.
- uses sklearn TimeSeriesSplit for CV and MAE as objective.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

try:
    import xgboost as xgb
except Exception:
    xgb = None


LOG = logging.getLogger(__name__)


def _compute_mae(y_true, y_pred):
    return float(mean_absolute_error(y_true, y_pred))


def optuna_tune_xgboost(
    df_features: pd.DataFrame,
    n_splits: int = 3,
    n_trials: int = 50,
    timeout: Optional[int] = None,
    random_state: Optional[int] = None,
):
    """Tune XGBoost with Optuna using TimeSeriesSplit CV.

    Parameters
    - df_features: DataFrame indexed by datetime containing 'rate' and feature columns
    - n_splits: number of TimeSeriesSplit folds
    - n_trials: number of Optuna trials
    - timeout: timeout in seconds for Optuna (optional)
    - random_state: seed for reproducibility

    Returns a CVResult-like dict with keys: name, best_params, metrics, model
    Also saves results to `models/optuna_xgboost_results_<timestamp>.json`.
    """
    # lazy import optuna to avoid hard dependency at module import time
    try:
        import optuna
    except Exception:
        raise ImportError("optuna is required for Optuna tuning. Install optuna or use grid tuner.")

    if xgb is None:
        raise ImportError("xgboost is required for XGBoost tuning. Install xgboost.")

    if "rate" not in df_features.columns:
        raise ValueError("df_features must contain 'rate' column")

    X = df_features.drop(columns=["rate"]).values
    y = df_features["rate"].values

    tscv = TimeSeriesSplit(n_splits=n_splits)

    def objective(trial: "optuna.trial.Trial") -> float:
        # suggest params
        params = {
            "learning_rate": trial.suggest_loguniform("learning_rate", 1e-4, 0.3),
            "gamma": trial.suggest_loguniform("gamma", 1e-8, 10.0),
            "subsample": trial.suggest_uniform("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_uniform("colsample_bytree", 0.5, 1.0),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_child_weight": trial.suggest_loguniform("min_child_weight", 1e-3, 10.0),
            "reg_alpha": trial.suggest_loguniform("reg_alpha", 1e-8, 10.0),
            "reg_lambda": trial.suggest_loguniform("reg_lambda", 1e-8, 10.0),
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        }

        cv_scores = []
        fold_idx = 0
        for train_idx, val_idx in tscv.split(X):
            fold_idx += 1
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            model = xgb.XGBRegressor(
                objective="reg:squarederror",
                learning_rate=params["learning_rate"],
                gamma=params["gamma"],
                subsample=params["subsample"],
                colsample_bytree=params["colsample_bytree"],
                max_depth=int(params["max_depth"]),
                min_child_weight=params["min_child_weight"],
                reg_alpha=params["reg_alpha"],
                reg_lambda=params["reg_lambda"],
                n_estimators=int(params["n_estimators"]),
                verbosity=0,
                n_jobs=1,
                random_state=random_state,
            )

            model.fit(X_train, y_train)
            pred = model.predict(X_val)
            mae = _compute_mae(y_val, pred)
            cv_scores.append(mae)

            # report intermediate result to Optuna and allow pruning
            trial.report(float(np.mean(cv_scores)), fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return float(np.mean(cv_scores))

    sampler = optuna.samplers.TPESampler(seed=random_state) if random_state is not None else optuna.samplers.TPESampler()
    pruner = optuna.pruners.MedianPruner()
    study = optuna.create_study(direction="minimize", sampler=sampler, pruner=pruner)
    study.optimize(objective, n_trials=n_trials, timeout=timeout)

    best_params = study.best_params
    best_score = float(study.best_value)

    # retrain final model on full data
    final_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        learning_rate=best_params.get("learning_rate", 0.1),
        gamma=best_params.get("gamma", 0),
        subsample=best_params.get("subsample", 1.0),
        colsample_bytree=best_params.get("colsample_bytree", 1.0),
        max_depth=int(best_params.get("max_depth", 6)),
        min_child_weight=best_params.get("min_child_weight", 1.0),
        reg_alpha=best_params.get("reg_alpha", 0.0),
        reg_lambda=best_params.get("reg_lambda", 1.0),
        n_estimators=int(best_params.get("n_estimators", 100)),
        verbosity=0,
        n_jobs=1,
        random_state=random_state,
    )
    final_model.fit(X, y)

    # compute in-sample metrics
    in_sample_pred = final_model.predict(X)
    in_sample_mae = _compute_mae(y, in_sample_pred)

    # save results
    out_dir = Path("models")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    res_path = out_dir / f"optuna_xgboost_results_{timestamp}.json"
    payload = {
        "best_params": best_params,
        "best_score": best_score,
        "in_sample_mae": in_sample_mae,
        "n_trials": n_trials,
        "timestamp": timestamp,
    }
    try:
        res_path.write_text(json.dumps(payload, indent=2))
        LOG.info("Saved Optuna results to %s", res_path)
    except Exception:
        LOG.exception("Failed to save Optuna results to %s", res_path)

    # create a minimal CVResult-like object
    try:
        from src.models.models import CVResult, compute_metrics

        metrics = {"MAE": in_sample_mae}
        result = CVResult(name="XGBoost-Optuna", best_params=best_params, metrics=metrics, model=final_model)
    except Exception:
        # fallback dict
        result = {"name": "XGBoost-Optuna", "best_params": best_params, "metrics": {"MAE": in_sample_mae}, "model": final_model}

    return result
