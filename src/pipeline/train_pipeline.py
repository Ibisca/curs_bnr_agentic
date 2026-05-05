"""Orchestrare end-to-end pentru pregătire date, antrenare modele, selectie si evaluare.

Flux:
- Încarcă CSV raw
- Preprocesează
- Construiește feature-uri
- Antrenează SARIMA, Prophet, XGBoost (cu TimeSeriesSplit)
- Selectează cel mai bun model (MAE)
- Salvează modelul în `models/`
- Evaluează pe ultimele 14 zile (folosind `src.evaluation`)
- Pregătește fișierele pentru plot și apelează vizualizarea Plotly

Exemple de rulare (în terminal):

# Rulează pipeline complet pe fișierul HRK CSV
python -m src.pipeline.train_pipeline --csv data/HRK_-_Kuna_croată_from_2020-02-22_20260420_215328.csv

# Rulează cu număr redus de bootstrap (mai rapid pentru test)
python -m src.pipeline.train_pipeline --csv data/HRK_-_Kuna_croată_from_2020-02-22_20260420_215328.csv --bootstrap 20

"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from src.data_loader import load_raw, preprocess, split_train_val_test
from src.features import build_features
from src.models import (
    tune_sarima,
    tune_prophet,
    tune_xgboost,
    select_best_model,
    save_model,
    CVResult,
)
from src.evaluate import evaluate_best_model, find_latest_best_model
from src.plotly_viz import load_plot_data, build_figure, save_figure


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOG = logging.getLogger(__name__)


def run_pipeline(
    csv_path: Path,
    models_dir: Path = Path("models"),
    reports_dir: Path = Path("reports"),
    n_splits: int = 3,
    bootstrap: int = 50,
    tuner: str = "grid",
    n_trials: int = 50,
    timeout: Optional[int] = None,
    seed: Optional[int] = None,
) -> None:
    LOG.info("Start pipeline for CSV: %s", csv_path)

    # Load and preprocess
    df_raw = load_raw(csv_path)
    df = preprocess(df_raw)

    # split
    train, val, test = split_train_val_test(df, test_days=14)

    # build features for XGBoost using train only, keep rows with no NaN
    df_feat_train = build_features(train, drop_na=True, fill_method="ffill")

    results: list[CVResult] = []

    # SARIMA tuning
    try:
        sarima_res = tune_sarima(train["rate"], orders=[(0, 1, 1), (1, 1, 1), (2, 1, 2)], seasonal_orders=[(0, 0, 0, 0), (1, 0, 1, 7)], n_splits=n_splits)
        results.append(sarima_res)
    except Exception as e:
        LOG.exception("SARIMA tuning failed: %s", e)

    # Prophet tuning
    try:
        prophet_res = tune_prophet(train["rate"], n_splits=n_splits)
        results.append(prophet_res)
    except Exception as e:
        LOG.exception("Prophet tuning failed: %s", e)

    # XGBoost tuning (GridSearch or Optuna)
    try:
        if tuner and tuner.lower() == "optuna":
            try:
                from src.tuning.optuna_tuner import optuna_tune_xgboost

                LOG.info("Running Optuna tuning for XGBoost: n_trials=%s, n_splits=%s", n_trials, n_splits)
                xgb_res = optuna_tune_xgboost(df_feat_train, n_splits=n_splits, n_trials=n_trials, timeout=timeout, random_state=seed)
            except Exception as e:
                LOG.exception("Optuna tuner failed or not available: %s", e)
                # fallback to grid search
                xgb_res = tune_xgboost(df_feat_train, n_splits=n_splits)
        else:
            xgb_res = tune_xgboost(df_feat_train, n_splits=n_splits)

        results.append(xgb_res)
    except Exception as e:
        LOG.exception("XGBoost tuning failed: %s", e)

    if not results:
        LOG.error("No models trained successfully; aborting pipeline")
        return

    # Log metrics
    for r in results:
        LOG.info("Model %s metrics (in-sample): %s", r.name, r.metrics)

    # Select best model by MAE
    best = select_best_model(results, metric="MAE")

    # Save best model artifact
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"best_model_{best.name}.pkl"
    save_model(best.model, model_path)

    # Evaluate best model on last 14 days and save predictions
    eval_csv, metrics = evaluate_best_model(csv_path, model_path, bootstrap=bootstrap)
    LOG.info("Evaluation metrics on last 14 days: %s", metrics)

    # Load plot-ready CSV (created by evaluate.py)
    plot_csvs = list(Path("data").glob("plot_data_*"))
    if not plot_csvs:
        LOG.error("No plot_data files found in data/. Expected evaluate.py to produce plot_data_*.csv")
        return
    # pick latest
    plot_csv = sorted(plot_csvs, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    df_plot = load_plot_data(plot_csv)
    fig = build_figure(df_plot, title=f"Forecast - {best.name}", highlight_last_n=14)
    save_figure(fig, reports_dir, best.name)
    LOG.info("Pipeline finished successfully. Reports saved to %s", reports_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate SARIMA/Prophet/XGBoost pipeline for FX series")
    parser.add_argument("--csv", required=True, help="path to CSV file (raw scraped)")
    parser.add_argument("--models-dir", default="models", help="directory to save models")
    parser.add_argument("--reports-dir", default="reports", help="directory for reports/plots")
    parser.add_argument("--n-splits", type=int, default=3, help="number of TimeSeriesSplit splits for tuning")
    parser.add_argument("--bootstrap", type=int, default=50, help="bootstrap iterations for XGBoost CI (evaluate step)")
    parser.add_argument("--tuner", choices=["grid", "optuna"], default="grid", help="Which tuning method to use for XGBoost")
    parser.add_argument("--n-trials", type=int, default=50, help="Number of Optuna trials (if tuner=optuna)")
    parser.add_argument("--timeout", type=int, default=None, help="Optuna timeout in seconds (optional)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        Path(args.csv),
        Path(args.models_dir),
        Path(args.reports_dir),
        n_splits=args.n_splits,
        bootstrap=args.bootstrap,
        tuner=args.tuner,
        n_trials=args.n_trials,
        timeout=args.timeout,
        seed=args.seed,
    )
