"""Conexiune SQLite pentru backend."""

import sqlite3
from pathlib import Path
from typing import Dict

DB_PATH = Path("data") / "curs_bnr_app.sqlite"


def get_connection() -> sqlite3.Connection:
    """Returnează o conexiune SQLite cu factory de rânduri configurat."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def cleanup_rate_duplicates() -> Dict[str, int]:
    """Curăță duplicatele din tabela rates, păstrând primul id pentru fiecare date+currency."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM rates")
        total_before = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM (SELECT date, currency FROM rates GROUP BY date, currency)"
        )
        unique_before = cursor.fetchone()[0]
        cursor.execute(
            """
            DELETE FROM rates
            WHERE id NOT IN (
                SELECT MIN(id) FROM rates GROUP BY date, currency
            )
            """
        )
        deleted = cursor.rowcount
        connection.commit()
        cursor.execute("SELECT COUNT(*) FROM rates")
        total_after = cursor.fetchone()[0]

    return {
        "total_rows_before": total_before,
        "unique_date_currency_before": unique_before,
        "total_rows_after": total_after,
        "duplicate_rows_deleted": deleted,
    }


def get_rates_stats() -> Dict[str, int]:
    """Returnează statistici despre tabela rates: total_rows, unique_date_currency, duplicate_rows."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM rates")
        total_rows = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM (SELECT date, currency FROM rates GROUP BY date, currency)"
        )
        unique_date_currency = cursor.fetchone()[0]

    return {
        "total_rows": total_rows,
        "unique_date_currency": unique_date_currency,
        "duplicate_rows": total_rows - unique_date_currency,
    }


def init_db() -> None:
    """Creează tabelele în baza de date dacă nu există și curăță duplicatele din rates."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                currency TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(date, currency)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                parameters_json TEXT,
                mae REAL,
                rmse REAL,
                mape REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forecast_date TEXT NOT NULL,
                currency TEXT NOT NULL,
                predicted_value REAL NOT NULL,
                model_name TEXT NOT NULL,
                mae_14_days REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

    cleanup_rate_duplicates()

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_rates_date_currency ON rates(date, currency)"
        )
        connection.commit()
