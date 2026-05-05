"""Data loading and preprocessing utilities.

Functions
- load_raw(csv_path): loads CSV into DataFrame
- preprocess(df): detects date and rate columns, converts types, sorts and returns cleaned df with index datetime and column `rate`
- split_train_val_test(df, test_days=14, val_days=None): splits by time, returns (train, val, test)

Designed for the scraped CSVs in `data/`.
"""
from __future__ import annotations

from typing import Optional, Tuple
from pathlib import Path
import logging

import pandas as pd


def load_raw(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logging.error("Fișierul nu există: %s", csv_path)
        raise FileNotFoundError(csv_path)

    df = pd.read_csv(csv_path)
    logging.info("Am încărcat %d rânduri din %s", len(df), csv_path)
    return df


def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
    candidates = [c for c in df.columns if c.lower().startswith("date") or c.lower().startswith("data")]
    if candidates:
        return candidates[0]
    # fallback: find first column that can parse to datetime
    for c in df.columns:
        try:
            pd.to_datetime(df[c].dropna().iloc[0])
            return c
        except Exception:
            continue
    return None


def _detect_rate_column(df: pd.DataFrame, date_col: str) -> Optional[str]:
    # prefer columns with common names
    for name in df.columns:
        low = name.lower()
        if low in ("rate", "curs", "valoare", "valoarea", "value"):
            return name
    # otherwise choose first numeric column that is not date
    for name in df.columns:
        if name == date_col:
            continue
        try:
            pd.to_numeric(df[name].dropna().iloc[0])
            return name
        except Exception:
            continue
    return None


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Returnează DataFrame cu index datetime și o coloană `rate` numerică.

    - Detectează coloana de dată și coloană de curs/rate.
    - Convertește data la datetime și curs la float (punct zecimal '.' sau ',').
    - Sortează după dată și elimină duplicate.
    """
    df = df.copy()

    date_col = _detect_date_column(df)
    if not date_col:
        logging.error("Nu am putut detecta coloana de dată în CSV")
        raise ValueError("date column not detected")

    rate_col = _detect_rate_column(df, date_col)
    if not rate_col:
        logging.error("Nu am putut detecta coloana de curs/valoare în CSV")
        raise ValueError("rate column not detected")

    # Normalize column names
    df = df.rename(columns={date_col: "date", rate_col: "rate"})

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])  # drop rows with invalid date

    # Normalize rate strings: replace comma with dot, remove non-numeric
    def _to_float(x):
        if pd.isna(x):
            return None
        if isinstance(x, str):
            s = x.strip().replace("\xa0", "").replace(" ", "")
            s = s.replace(",", ".")
            # remove any non-numeric characters except dot and minus
            import re

            s = re.sub(r"[^0-9.\-]", "", s)
            try:
                return float(s)
            except Exception:
                return None
        try:
            return float(x)
        except Exception:
            return None

    df["rate"] = df["rate"].apply(_to_float)
    df = df.dropna(subset=["rate"])  # drop rows with invalid rate

    df = df.sort_values("date").drop_duplicates(subset=["date"])  # keep first occurrence per date
    df = df.set_index("date")

    logging.info("Preprocesare finalizata: %d rânduri curate." , len(df))
    return df[["rate"]]


def split_train_val_test(df: pd.DataFrame, test_days: int = 14, val_days: Optional[int] = None) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
    """Împarte df pe train / (val) / test pe ultimele observații.

    test set = ultimele `test_days` observații (nu zile calendaristice).
    if `val_days` este specificat, validation = ultimele `val_days` observații din rest, altfel None.
    Evită folosirea lui `df.last(...)` și folosește `tail()` pentru selecție precisă.
    """
    if df.empty:
        raise ValueError("DataFrame gol")

    # select exact last N rows for test set
    if test_days <= 0:
        raise ValueError("test_days trebuie să fie > 0")

    test = df.tail(test_days)
    rest = df.iloc[: len(df) - len(test)]

    if val_days and val_days > 0:
        val = rest.tail(val_days)
        train = rest.iloc[: len(rest) - len(val)]
    else:
        val = None
        train = rest

    logging.info(
        "Split: train=%d, val=%s, test=%d",
        len(train),
        f"{len(val)}" if val is not None else "None",
        len(test),
    )
    return train, val, test


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="path to CSV file")
    args = parser.parse_args()
    df_raw = load_raw(args.csv)
    df = preprocess(df_raw)
    train, val, test = split_train_val_test(df)
    print(df.head())
