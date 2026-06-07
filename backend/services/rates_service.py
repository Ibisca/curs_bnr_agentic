"""Serviciu pentru extragerea și inserarea cursurilor din baza de date."""

from datetime import datetime
from typing import Any, Dict, List

from backend.database import get_connection


def get_latest_rates(limit: int = 20) -> List[Dict[str, Any]]:
    """Returnează ultimele cursuri din tabelul rates, fără duplicate pe date+currency."""
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT r.id, r.date, r.currency, r.value, r.created_at
                FROM rates r
                INNER JOIN (
                    SELECT date, currency, MIN(id) AS min_id
                    FROM rates
                    GROUP BY date, currency
                ) unique_rates
                ON r.id = unique_rates.min_id
                ORDER BY r.date DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def insert_rate(date: str, currency: str, value: float) -> bool:
    """Inserează un curs în tabela rates. Returnează True dacă s-a inserat, False dacă era duplicat."""
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT OR IGNORE INTO rates (date, currency, value, created_at) VALUES (?, ?, ?, ?)",
                (date, currency, value, created_at),
            )
            connection.commit()
        return cursor.rowcount == 1
    except Exception:
        return False


def insert_rates_batch(rates_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """Inserează o listă de cursuri. Returnează contor de insertări și duplicate."""
    inserted = 0
    skipped = 0
    with get_connection() as connection:
        cursor = connection.cursor()
        for rate in rates_list:
            cursor.execute(
                "INSERT OR IGNORE INTO rates (date, currency, value, created_at) VALUES (?, ?, ?, ?)",
                (
                    rate["date"],
                    rate["currency"],
                    rate["value"],
                    datetime.now().isoformat(),
                ),
            )
            if cursor.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        connection.commit()

    return {"inserted": inserted, "skipped": skipped}

