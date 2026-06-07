"""Serviciu pentru generarea graficelor forecast din baza de date."""

from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

from backend.database import get_connection
from backend.services.forecast_service import get_latest_forecast
from src.visualization import build_figure, save_figure


def _load_eur_rates() -> pd.DataFrame:
    """Încarcă toate ratele EUR din SQLite, ordonate crescător după dată."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT date, value FROM rates WHERE currency = ? ORDER BY date ASC",
            ("EUR",),
        )
        rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=["date", "value"])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    return df


def generate_forecast_plot(reports_dir: Path = Path("reports"), model_name: str = "XGBoost") -> Path:
    """Generează un fișier HTML cu graficul forecast bazat pe datele curente din SQLite."""
    df_rates = _load_eur_rates()
    if df_rates.empty:
        raise ValueError("Nu există date EUR în tabela rates pentru a genera graficul.")

    forecast = get_latest_forecast()
    forecast_date = forecast.get("forecast_date")
    predicted_value = forecast.get("predicted_value")
    forecast_model_name = forecast.get("model_name") or model_name

    plot_df = pd.DataFrame(index=df_rates.index)
    plot_df["observed"] = df_rates["value"].astype(float)
    plot_df["predicted"] = float("nan")

    # Include ultima prognoză salvată în forecasts, dacă există și are o dată validă.
    if forecast_date and predicted_value is not None:
        forecast_ts = pd.to_datetime(forecast_date, errors="coerce")
        if not pd.isna(forecast_ts):
            plot_df.loc[forecast_ts, "predicted"] = float(predicted_value)

    plot_df = plot_df.sort_index()

    # Build figure with highlight on last 14 zile
    title = f"Forecast plot EUR/RON - {forecast_model_name}"
    fig = build_figure(plot_df, title=title, highlight_last_n=14)

    out_path = save_figure(fig, reports_dir, forecast_model_name)
    return out_path


def get_latest_rate_date() -> Optional[str]:
    """Returnează ultima dată disponibilă pentru EUR din tabela rates."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM rates WHERE currency = ?",
            ("EUR",),
        )
        row = cursor.fetchone()
    if not row:
        return None
    return row[0]
