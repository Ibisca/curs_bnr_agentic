# Plan Import, Scraper și SQLite

## Fișiere create

- `backend/services/import_service.py` - Serviciu pentru importul datelor din CSV în SQLite

## Fișiere modificate

- `backend/database.py` - Adaugat UNIQUE(date, currency) la tabela rates
- `backend/services/rates_service.py` - Adaugate funcții `insert_rate()` și `insert_rates_batch()`
- `backend/main.py` - Adaugate endpoint-urile `/api/import-rates` și actualizat `/api/scrape`
- `frontend/app.py` - Adaugate butoane pentru import și scraping

## Cum funcționează importul din CSV

1. Serviciul `import_service.py` caută fișiere CSV în folderul `data/`
2. Detectează codul valutei din numele fișierului (de exemplu: `EUR_from...` → `EUR`)
3. Detectează coloanele de dată și valoare din CSV:
   - Data: coloană care conține "Data"
   - Valoare: coloană care conține "Valoare" sau "Value"
4. Convertește datele din format `dd.mm.yyyy` la `YYYY-MM-DD`
5. Convertește valorile la float
6. Inserează în tabela `rates` evitând duplicatele cu constrângerea `UNIQUE(date, currency)`

## Cum funcționează endpoint-ul `/api/scrape`

- POST /api/scrape importează datele existente din fișierele CSV în SQLite
- Returnează rezumat: numărul de cursuri importate și duplicate ignorate
- Comportament sigur: funcționează cu fișierele CSV existente din proiect

## Cum se evita duplicatele

- Tabela `rates` are constrângere `UNIQUE(date, currency)`
- Funcția `insert_rate()` returnează `True` dacă s-a inserat, `False` dacă era duplicat
- Funcția `insert_rates_batch()` numără insertările și duplicate separate

## Endpoint-uri disponibile

### POST /api/import-rates
Importează cursuri din fișierele CSV existente în data/.

**Răspuns:**
```json
{
  "status": "ok",
  "total_inserted": 100,
  "total_skipped": 50,
  "files_processed": 1,
  "details": [...]
}
```

### POST /api/scrape
Importează cursuri și returnează mesaj descriptiv.

**Răspuns:**
```json
{
  "status": "ok",
  "message": "S-au importat 100 cursuri, 50 duplicate.",
  "inserted": 100,
  "skipped": 50
}
```

### GET /api/rates?limit=20
Returnează ultimele cursuri din tabelul rates.

**Răspuns:**
```json
[
  {
    "id": 1,
    "date": "2026-04-21",
    "currency": "EUR",
    "value": 4.97,
    "created_at": "2026-06-06T..."
  }
]
```

## Comenzi de pornire

### Backend (terminal 1)
```powershell
python -m uvicorn backend.main:app --reload --port 7772
```

### Frontend (terminal 2)
```powershell
streamlit run frontend/app.py
```

## Testare endpoint-uri

```bash
# Verifică health
curl http://localhost:7772/api/health

# Inițializează baza de date
curl -X POST http://localhost:7772/api/init-db

# Importă date din CSV
curl -X POST http://localhost:7772/api/import-rates

# Citește cursuri
curl http://localhost:7772/api/rates?limit=20

# Actualizează prin scraping
curl -X POST http://localhost:7772/api/scrape
```

## Note

- Importul automător pe startup nu s-a implementat încă (va fi în faza următoare)
- Scraperul real de la cursbnr.ro nu s-a integrat direct (folosim CSV-uri existente)
- LLM tools, chatbot, și dashboard Optuna nu sunt implementate
- Frontend are butoane pentru acțiuni manuale
