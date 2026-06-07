"""Serviciu de antrenare modele pentru curs valutar BNR."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from backend.database import get_connection
from backend.services.plot_service import generate_forecast_plot
from src.data.data_loader import load_raw, preprocess, split_train_val_test
from src.features.features import build_features
from src.models.models import (
    tune_sarima,
    tune_prophet,
    tune_xgboost,
    select_best_model,
    save_model,
    compute_metrics,
)

# optional faster evaluation path
from src.evaluation.evaluate import evaluate_best_model
try:
    import xgboost as xgb
except Exception:
    xgb = None
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

LOG = logging.getLogger(__name__)


def run_training(
    csv_path: Optional[Path] = None,
    models_dir: Path = Path("models"),
    reports_dir: Path = Path("reports"),
    n_splits: int = 2,
    bootstrap: int = 10,
    tuner: str = "grid",
    n_trials: int = 0,
    timeout: Optional[int] = None,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """
    Antrenează modele (SARIMA, Prophet, XGBoost) pe date de curs valutar și salvează
    rezultatele în tabela training_runs din SQLite.

    Args:
        csv_path: Path la fișierul CSV cu date. Dacă None, găsește cel mai recent din data/
        models_dir: Director pentru salvare modele
        reports_dir: Director pentru rapoarte
        n_splits: Număr de split-uri în TimeSeriesSplit
        bootstrap: Iterații bootstrap pentru CI (doar XGBoost)
        tuner: "grid" pentru GridSearch sau "optuna" pentru Optuna
        n_trials: Numărul de trial-uri în Optuna
        timeout: Timeout în secunde pentru Optuna
        seed: Random seed pentru reproducibilitate

    Returns:
        Dict cu cheile: mae, rmse, mape, model_name, created_at, status

    Raises:
        ValueError: Dacă nu se găsesc date sau antrenarea eșuează
    """
    try:
        LOG.info("START fast run_training")

        # 1. Load data from SQLite rates table for EUR
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT date, value FROM rates WHERE currency = ? ORDER BY date ASC", ("EUR",))
            rows = cur.fetchall()

        if rows:
            df_rates = pd.DataFrame(rows, columns=["date", "value"])
            df_rates["date"] = pd.to_datetime(df_rates["date"], errors="coerce")
            df_rates = df_rates.dropna(subset=["date"]).set_index("date").sort_index()
            LOG.info("Loaded %d rows from rates table", len(df_rates))
        else:
            # fallback to CSV if DB empty
            LOG.info("No rows in rates table, fallback to CSV")
            if csv_path is None:
                csv_files = list(Path("data").glob("*_from_2020*.csv"))
                if not csv_files:
                    raise ValueError("Nu există date în tabela rates și nici CSV în data/")
                csv_path = max(csv_files, key=lambda p: p.stat().st_mtime)
            df_raw = load_raw(csv_path)
            df = preprocess(df_raw)
            df_rates = df[[]].copy()
            df_rates["value"] = df["rate"]
            LOG.info("Loaded %d rows from CSV %s", len(df_rates), csv_path)

        if df_rates.empty or len(df_rates) < 5:
            return {"status": "error", "message": "Date insuficiente pentru antrenare."}

        # 2. Build simple features
        df_feat = df_rates.copy()
        df_feat["lag_1"] = df_feat["value"].shift(1)
        df_feat["lag_2"] = df_feat["value"].shift(2)
        df_feat["lag_3"] = df_feat["value"].shift(3)
        df_feat["rm7"] = df_feat["value"].rolling(window=7, min_periods=1).mean()
        df_feat["rm14"] = df_feat["value"].rolling(window=14, min_periods=1).mean()

        df_feat = df_feat.dropna()
        LOG.info("Features built, final rows after dropna: %d", len(df_feat))

        if len(df_feat) <= 14:
            return {"status": "error", "message": "Date insuficiente după creare features pentru a avea test set de 14 zile."}

        # 5. Split last 14 as test
        test = df_feat.iloc[-14:]
        train = df_feat.iloc[:-14]

        X_train = train.drop(columns=["value"]).values
        y_train = train["value"].values
        X_test = test.drop(columns=["value"]).values
        y_test = test["value"].values

        # 6. Train model (XGBoost if available, else RandomForest)
        model = None
        model_name = None
        params = {}
        if xgb is not None:
            try:
                model = xgb.XGBRegressor(
                    n_estimators=50,
                    max_depth=3,
                    learning_rate=0.05,
                    subsample=0.9,
                    objective="reg:squarederror",
                    random_state=seed,
                    verbosity=0,
                )
                model.fit(X_train, y_train)
                model_name = "XGBoost"
                params = {"n_estimators": 50, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.9}
                LOG.info("Trained XGBoost model")
            except Exception as e:
                LOG.warning("XGBoost training failed, fallback: %s", e)
                model = None

        if model is None:
            # fallback to RandomForest
            try:
                model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=seed)
                model.fit(X_train, y_train)
                model_name = "RandomForest"
                params = {"n_estimators": 50, "max_depth": 5}
                LOG.info("Trained RandomForest model")
            except Exception as e:
                LOG.exception("Fallback model training failed: %s", e)
                return {"status": "error", "message": f"Model training failed: {e}"}

        # 7. Metrics on test
        y_pred = model.predict(X_test)
        metrics = compute_metrics(y_test, y_pred)
        mae = metrics.get("MAE")
        rmse = metrics.get("RMSE")
        mape = metrics.get("MAPE")
        created_at = datetime.now().isoformat()

        # save model artifact
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / f"best_model_{model_name}.pkl"
        save_model(model, model_path)

        # 8. Save training run
        training_run_saved = False
        forecast_saved = False
        forecast_date = None
        predicted_value = None

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO training_runs (model_name, parameters_json, mae, rmse, mape, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (model_name, json.dumps(params), mae, rmse, mape, created_at),
            )
            conn.commit()
            training_run_saved = True

            # 9. Forecast next day using last raw values
            try:
                last_dates = df_rates.index.sort_values()
                last_date = last_dates[-1]
                # build next features
                vals = df_rates["value"].values
                if len(vals) >= 3:
                    next_lag_1 = float(vals[-1])
                    next_lag_2 = float(vals[-2])
                    next_lag_3 = float(vals[-3])
                else:
                    # fallback use repeated last
                    next_lag_1 = float(vals[-1])
                    next_lag_2 = float(vals[-1])
                    next_lag_3 = float(vals[-1])

                rm7 = float(pd.Series(vals).tail(7).mean())
                rm14 = float(pd.Series(vals).tail(14).mean())

                X_next = [[next_lag_1, next_lag_2, next_lag_3, rm7, rm14]]
                predicted_value = float(model.predict(X_next)[0])
                forecast_date = (pd.to_datetime(last_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

                # 10. Save forecast
                cur.execute(
                    "INSERT INTO forecasts (forecast_date, currency, predicted_value, model_name, mae_14_days, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (forecast_date, "EUR", predicted_value, model_name, mae, created_at),
                )
                conn.commit()
                forecast_saved = True
            except Exception as e:
                LOG.exception("Failed to save forecast: %s", e)

        plot_generated = False
        plot_path = None
        try:
            plot_path = generate_forecast_plot(reports_dir=reports_dir, model_name=model_name)
            plot_generated = True
            LOG.info("Generated plot: %s", plot_path)
        except Exception as e:
            LOG.warning("Could not generate forecast plot after training: %s", e)

        # 11. Return response
        return {
            "status": "ok",
            "model_name": model_name,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "created_at": created_at,
            "training_run_saved": training_run_saved,
            "forecast_saved": forecast_saved,
            "forecast_date": forecast_date,
            "predicted_value": predicted_value,
            "plot_generated": plot_generated,
            "plot_file": plot_path.name if plot_path is not None else None,
        }

    except Exception as e:
        LOG.exception("Eroare în fast run_training: %s", e)
        return {"status": "error", "message": str(e)}
