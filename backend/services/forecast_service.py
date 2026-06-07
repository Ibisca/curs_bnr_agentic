"""Serviciu pentru extragerea ultimei prognoze din baza de date."""

from typing import Any, Dict, Optional

from backend.database import get_connection


def get_latest_forecast() -> Dict[str, Any]:
    """Returnează cea mai recentă prognoză din tabelul forecasts."""
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, forecast_date, currency, predicted_value, model_name, mae_14_days, created_at
                FROM forecasts
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
    except Exception:
        return {"message": "Nu există prognoze salvate încă."}
    if row is None:
        return {"message": "Nu există prognoze salvate încă."}
    return dict(row)
