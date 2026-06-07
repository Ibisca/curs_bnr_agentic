# Plan implementare frontend/backend minimal

## Fișiere create

- `backend/__init__.py`
- `backend/main.py`
- `backend/database.py`
- `backend/schemas.py`
- `backend/services/__init__.py`
- `backend/services/rates_service.py`
- `backend/services/forecast_service.py`
- `backend/services/runs_service.py`
- `frontend/app.py`
- `data/curs_bnr_app.sqlite` (creare automată la prima conexiune)

## Tabele SQLite create

- `rates`
- `training_runs`
- `forecasts`

## Endpoint-uri disponibile

- `GET /`
- `GET /api/health`
- `GET /api/rates?limit=20`
- `GET /api/forecast/latest`
- `GET /api/runs?limit=5`
- `POST /api/init-db`
- `POST /api/scrape`

## Cum se pornește backend-ul

```powershell
python -m uvicorn backend.main:app --reload --port 7772
```

## Cum se pornește frontend-ul

```powershell
streamlit run frontend/app.py
```

## Ce NU a fost implementat încă

- Integrarea scraperului real în endpoint-ul `POST /api/scrape`
- Dashboard Optuna
- Retraining complex automat
- Chatbot LLM
- Integrarea completă a pipeline-ului de antrenare în backend
