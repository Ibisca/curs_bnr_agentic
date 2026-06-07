"""Aplicație FastAPI minimală pentru Curs BNR."""

from typing import Any, Dict, List
from datetime import datetime

from fastapi import FastAPI

from backend.database import init_db, get_rates_stats
from backend.schemas import (
    ForecastSchema,
    MessageSchema,
    RateSchema,
    RunSchema,
    StatusSchema,
)
from backend.services.forecast_service import get_latest_forecast
from backend.services.plot_service import generate_forecast_plot
from backend.services.rates_service import get_latest_rates, insert_rates_batch
from backend.services.runs_service import get_latest_runs
from backend.services.import_service import import_all_csv_files
from backend.services.training_service import run_training
from src.scraping.scraper import fetch_xml_years_eur, create_session_with_retries

app = FastAPI(title="Curs BNR API")


@app.on_event("startup")
def startup_event() -> None:
    """Inițializează baza de date la pornirea aplicației."""
    init_db()


@app.get("/", response_model=Dict[str, str])
def root() -> Dict[str, str]:
    """Returnează un mesaj simplu că API-ul rulează."""
    return {"message": "API Curs BNR rulează"}


@app.get("/api/health", response_model=StatusSchema)
def health() -> StatusSchema:
    """Returnează statusul de sănătate al API-ului."""
    return StatusSchema(status="ok")


@app.get("/api/rates", response_model=List[RateSchema])
def read_rates(limit: int = 20) -> List[RateSchema]:
    """Returnează ultimele cursuri din tabela rates, fără duplicate."""
    return [RateSchema(**rate) for rate in get_latest_rates(limit=limit)]


@app.get("/api/rates/stats")
def rates_stats() -> Dict[str, int]:
    """Returnează statistici despre tabela rates."""
    return get_rates_stats()


@app.get("/api/forecast/latest", response_model=ForecastSchema)
def read_latest_forecast() -> ForecastSchema:
    """Returnează ultima prognoză din tabela forecasts."""
    forecast = get_latest_forecast()
    return ForecastSchema(**forecast)


@app.get("/api/runs", response_model=List[RunSchema])
def read_runs(limit: int = 5) -> List[RunSchema]:
    """Returnează ultimele rulări de antrenare."""
    return [RunSchema(**run) for run in get_latest_runs(limit=limit)]


@app.post("/api/init-db")
def create_database() -> Dict[str, Any]:
    """Creează baza de date, curăță duplicatele și returnează statistici."""
    init_db()
    stats = get_rates_stats()
    return {
        "status": "ok",
        "message": "Baza de date a fost inițializată și s-au curățat duplicatele.",
        **stats,
    }


@app.post("/api/import-rates")
def import_rates() -> Dict[str, Any]:
    """Importează cursurile din fișierele CSV din folderul data/."""
    result = import_all_csv_files()
    return result


@app.post("/api/scrape")
def scrape_rates() -> Dict[str, Any]:
    """Apelează scraperul real BNR pentru EUR și salvează datele în SQLite."""
    try:
        session = create_session_with_retries()
        raw_records = fetch_xml_years_eur(session, start_date="22/02/2020")
        if not raw_records:
            return {
                "status": "info",
                "message": "Scraperul nu a returnat date.",
                "inserted": 0,
                "skipped": 0,
            }

        formatted_records = []
        for record in raw_records:
            try:
                date_str = record.get("Data", "")
                value_str = record.get("Valoare EUR (exprimată in lei)", "")
                if not date_str or not value_str:
                    continue
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                iso_date = date_obj.strftime("%Y-%m-%d")
                rate_value = float(value_str.replace(",", "."))
                formatted_records.append({
                    "date": iso_date,
                    "currency": "EUR",
                    "value": rate_value,
                })
            except (ValueError, KeyError):
                continue

        result = insert_rates_batch(formatted_records)
        return {
            "status": "ok",
            "message": f"S-au importat {result['inserted']} cursuri EUR, {result['skipped']} duplicate.",
            "inserted": result["inserted"],
            "skipped": result["skipped"],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Eroare la scraping: {str(e)}",
            "inserted": 0,
            "skipped": 0,
        }


@app.post("/api/retrain")
def retrain() -> Dict[str, Any]:
    """Antrenează modele și salvează metricile în baza de date."""
    result = run_training(tuner="grid", n_splits=2, bootstrap=10, n_trials=0, timeout=None)
    if result["status"] == "ok":
        return {
            "status": "ok",
            "message": result.get("message", f"Antrenare finalizată. Model: {result.get('model_name') or 'necunoscut'}"),
            "mae": result["mae"],
            "rmse": result["rmse"],
            "mape": result["mape"],
            "model_name": result["model_name"],
            "created_at": result["created_at"],
            "training_run_saved": result.get("training_run_saved", False),
            "forecast_saved": result.get("forecast_saved", False),
        }
    return {
        "status": "error",
        "message": result.get("message", "Eroare în antrenare"),
        "training_run_saved": result.get("training_run_saved", False),
        "forecast_saved": result.get("forecast_saved", False),
    }


@app.post("/api/generate-plot")
def generate_plot() -> Dict[str, Any]:
    """Regenerază doar graficul forecast pe baza datelor curente din SQLite."""
    try:
        plot_path = generate_forecast_plot()
        return {
            "status": "ok",
            "message": "Plot generat cu succes.",
            "plot_file": plot_path.name,
            "plot_path": str(plot_path),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Nu s-a putut genera graficul: {str(e)}",
        }
