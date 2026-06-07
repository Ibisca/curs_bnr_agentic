"""Serviciu pentru importul datelor din fișiere CSV în tabela rates."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.services.rates_service import insert_rates_batch


def detect_currency_from_filename(filename: str) -> Optional[str]:
    """Detectează codul valutei din numele fișierului. Ex: EUR_from... -> EUR."""
    match = re.match(r"([A-Z]{3})_", filename)
    if match:
        return match.group(1)
    return None


def parse_date_to_iso(date_str: str) -> Optional[str]:
    """Convertește data din format dd.mm.yyyy la format YYYY-MM-DD."""
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception:
        return None


def find_csv_files_in_data() -> List[Path]:
    """Caută fișiere CSV în folderul data/."""
    data_dir = Path("data")
    if not data_dir.exists():
        return []
    return sorted(list(data_dir.glob("*.csv")))


def import_csv_to_rates(csv_path: Path) -> Dict[str, Any]:
    """Importează datele din fișierul CSV în tabela rates.
    
    Returnează:
    {
        "status": "ok" | "error",
        "inserted": int,
        "skipped": int,
        "source_file": str,
        "message": str (în caz de eroare)
    }
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return {
            "status": "error",
            "inserted": 0,
            "skipped": 0,
            "source_file": str(csv_path),
            "message": f"Nu am putut citi CSV-ul: {str(e)}",
        }

    # Detectează moneda din numele fișierului
    currency = detect_currency_from_filename(csv_path.name)
    if not currency:
        return {
            "status": "error",
            "inserted": 0,
            "skipped": 0,
            "source_file": str(csv_path),
            "message": "Nu am putut detecta moneda din numele fișierului.",
        }

    # Detectează coloanele de dată și valoare
    # Presupunem că coloana cu dată conține cuvintele "Data" sau "date"
    # și coloana cu valoare conține "Valoare" sau "value"
    date_col = None
    value_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "data" in col_lower and date_col is None:
            date_col = col
        if ("valoare" in col_lower or "value" in col_lower) and value_col is None:
            value_col = col

    if not date_col or not value_col:
        return {
            "status": "error",
            "inserted": 0,
            "skipped": 0,
            "source_file": str(csv_path),
            "message": f"Nu am găsit coloanele de dată și valoare. Coloane disponibile: {df.columns.tolist()}",
        }

    # Construiește lista de cursuri pentru inserare
    rates_list: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        date_str = row[date_col]
        value = row[value_col]

        # Sari peste rândurile cu valoare NaN
        if pd.isna(value) or value == "":
            continue

        # Convertește data
        iso_date = parse_date_to_iso(str(date_str))
        if not iso_date:
            continue

        # Convertește valoarea la float
        try:
            value_float = float(value)
        except (ValueError, TypeError):
            continue

        rates_list.append({"date": iso_date, "currency": currency, "value": value_float})

    # Inserează datele
    result = insert_rates_batch(rates_list)

    return {
        "status": "ok",
        "inserted": result["inserted"],
        "skipped": result["skipped"],
        "source_file": str(csv_path),
    }


def import_all_csv_files() -> Dict[str, Any]:
    """Importează datele din toate fișierele CSV din folderul data/.
    
    Returnează rezumat agregat.
    """
    csv_files = find_csv_files_in_data()

    total_inserted = 0
    total_skipped = 0
    results: List[Dict[str, Any]] = []

    for csv_path in csv_files:
        # Sari peste fișiere care nu par să conțină cursuri (ex: prediction files)
        if "prediction" in csv_path.name.lower() or "plot_data" in csv_path.name.lower():
            continue

        result = import_csv_to_rates(csv_path)
        results.append(result)

        if result["status"] == "ok":
            total_inserted += result["inserted"]
            total_skipped += result["skipped"]

    return {
        "status": "ok",
        "total_inserted": total_inserted,
        "total_skipped": total_skipped,
        "files_processed": len(results),
        "details": results,
    }
