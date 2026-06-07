"""Serviciu pentru extragerea ultimelor rulări din baza de date."""

from typing import Any, Dict, List

from backend.database import get_connection


def get_latest_runs(limit: int = 5) -> List[Dict[str, Any]]:
    """Returnează ultimele rulări de antrenare din tabelul training_runs."""
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, model_name, parameters_json, mae, rmse, mape, created_at"
                " FROM training_runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []
