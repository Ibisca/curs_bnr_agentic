# Instrucțiuni pentru agentul AI

## 1. Scopul documentului
Acest document centralizează instrucțiunile transmise agentului AI pe parcursul dezvoltării proiectului final AIE. Instrucțiunile au fost folosite drept sursă pentru deciziile de implementare și pentru planurile salvate în folderul `agentic_docs`.

Proiectul final este o aplicație pentru curs valutar BNR cu următoarele componente principale:
- frontend: Streamlit
- backend: FastAPI
- scraper pentru date BNR
- bază de date: SQLite
- parte de reantrenare modele
- grafic de forecast (Plotly)
- chatbot cu tool-uri
- integrare Google Gemini LLM și fallback local

## 2. Reguli generale pentru agent
- Lucrează incremental, fișier cu fișier; evită schimbări mari într-un singur pas.
- Cere aprobare explicită înainte de modificări majore (refactorizare, schimbare arhitecturală, rulare Optuna/training lung).
- Nu rula training costisitor sau Optuna fără acordul utilizatorului.
- Nu face commit-uri fără confirmarea utilizatorului.
- Folosește type hints pentru toate funcțiile noi sau modificate.
- Adaugă docstrings în limba română pentru funcții și clase noi/modificate.
- Respectă PEP8 pentru stil și gruparea importurilor conform ghidului.
- Pentru importuri multiple folosește paranteze și linii separate, de exemplu:

```py
from typing import (
    Dict,
    List,
    Optional,
)
```

- Tratează erorile controlat; în UI afișează mesaje scurte, fără traceback-uri brute.
- Nu afișa chei API în UI, loguri sau documentație publică.
- Păstrează fișierul `.env` în `.gitignore`.
- Păstrează un mecanism de fallback local dacă LLM extern (Gemini) nu este disponibil.
- Evită modificările inutile ale backend-ului dacă problema este în frontend.
- Asigură-te că aplicația rămâne funcțională după fiecare etapă de lucru.

## 3. Instrucțiuni pentru scraping
- Realizează scraping pentru cursul valutar BNR.
- Sursa primară: site-ul oficial (cursbnr.ro / pagină curs-valutar-bnr) și tabelul HTML corespunzător.
- Data de început pentru import inițial: 22/02/2020.
- Extrage datele din tabelul HTML al cursurilor valutare și normalizează coloanele (date, currency, value).
- Salvează inițial datele într-un fișier CSV cu encoding UTF-8 pentru inspecție.
- Codul scraperului este scris în Python și trebuie să includă dependințe clare (`requests`, `beautifulsoup4`, `pandas` etc.).
- Propune și documentează dependențele în `requirements.txt` sau în notițe.
- Integrează ulterior scraperul în backend prin endpoint-ul `POST /api/scrape` care poate actualiza datele istorice.
- Datele extrase se salvează în SQLite; previne duplicatele prin constrângere unică pe `(date, currency)`.

## 4. Instrucțiuni pentru antrenarea modelelor
- Creează un plan pentru antrenarea a trei modele de prognoză: XGBoost, SARIMA și Prophet.
- Problema formulată: prognoza cursului de schimb pentru ziua următoare.
- Folosește validare specifică seriilor temporale (time series cross-validation / rolling windows).
- Calculează și păstrează metrici relevante: MAE, RMSE, MAPE.
- Salvează modelul cel mai performant (artefact serializat) în folderul `models/`.
- Testează performanța pe ultimele 14 zile (backtest) și raportează metricile.
- Prezintă prognoza într-un grafic Plotly, cu valori observate, prezise și, dacă este posibil, interval de încredere.
- Pentru XGBoost: creează feature-uri de tip lag (1..n), medii mobile pe 7 și 14 zile și altele relevante.
- Parametri XGBoost de investigat: `n_estimators`, `max_depth`, `learning_rate`/`eta`, `gamma`, `subsample`.
- Pentru SARIMA: explorează valori pentru `order` și `seasonal_order` și documentează selecția.
- Pentru Prophet: construiește procedure pentru experimentare (GridSearch) a parametrilor relevanți.
- Propune metode de optimizare: GridSearch și Optuna; Optuna trebuie configurat pentru salvarea studiilor.

## 5. Instrucțiuni pentru structura proiectului
- Restructurează proiectul conform bunelor practici Python, organizând codul în pachete clare.
- Structura recomandată:
  - `backend/`
  - `frontend/`
  - `src/`
  - `data/`
  - `models/`
  - `reports/`
  - `agentic_docs/`
  - `archive_original_project/`
- Proiectul inițial trebuie arhivat în `archive_original_project/`.
- Mută documentele `.md` relevante în `agentic_docs/`.
- Creează un plan de refactorizare `Refactorizare_cod.md` în `agentic_docs/`.
- Păstrează `requirements.txt` și descrie pașii de instalare în `README.md`.
- Păstrează toate instrucțiunile și planurile generate în `agentic_docs/`.

## 6. Instrucțiuni pentru backend
- Backend: FastAPI.
- Port implicit: `7772`.
- Conexiune la SQLite.
- Endpoint-uri minim acceptate:
  - `GET /api/health`
  - `GET /api/rates`
  - `GET /api/rates/stats`
  - `GET /api/forecast/latest`
  - `GET /api/runs`
  - `POST /api/init-db`
  - `POST /api/import-rates`
  - `POST /api/scrape`
  - `POST /api/retrain`
- Backend-ul trebuie să inițializeze baza de date dacă este necesar și să returneze răspunsuri JSON controlate (fără 500 pentru stări normale precum tabele goale).
- Endpoint-ul `POST /api/scrape` trebuie să actualizeze datele BNR.
- Endpoint-ul `POST /api/retrain` trebuie să ruleze o variantă rapidă și stabilă de reantrenare, să salveze o înregistrare în `training_runs`, o prognoză în `forecasts` și metricile modelului.

## 7. Instrucțiuni pentru baza de date SQLite
- Folosește SQLite pentru stocarea datelor istorice și a metadatelor.
- Tabele principale:
  - `rates` (date, currency, value, created_at)
  - `training_runs` (model_name, parameters_json, mae, rmse, mape, created_at)
  - `forecasts` (forecast_date, currency, predicted_value, model_name, mae_14_days, created_at)
- Previno duplicatele în `rates` cu constrângere unică pe `(date, currency)`.
- Include funcții/endpoint-uri de curățare și verificare a duplicatelor.

## 8. Instrucțiuni pentru frontend
- Frontend: Streamlit.
- Structură în tab-uri: `Dashboard`, `Date & Scraping`, `Model & Reantrenare`, `Optuna`, `Chatbot`.
- Dashboard afișează: status backend, prognoza curentă, KPI MAE pe ultimele 14 zile, graficul forecast-ului, istoricul recent al cursului.
- `Date & Scraping`: permite import CSV, actualizare prin scraping, vizualizarea ultimelor cursuri.
- `Model & Reantrenare`: permite reantrenarea modelului (rapidă), afișarea metricilor și a ultimelor rulări.
- `Optuna`: afișează fișiere/studii Optuna existente sau un mesaj controlat dacă nu sunt disponibile.
- `Chatbot`: interfața de conversație; tratează erorile cu mesaje scurte, fără traceback-uri.
- Tabelele din UI trebuie să ocolească coloanele tehnice inutile și să fie lizibile.

## 9. Instrucțiuni pentru grafice
- Grafic principal: forecast-ul celui mai bun model, realizat cu Plotly.
- Graficul trebuie să includă: valorile observate, valorile prezise, backtest pe ultimele 14 zile și interval de încredere dacă este disponibil.
- Salvează graficul principal în `reports/` ca fișier HTML.
- Frontend-ul afișează întotdeauna cel mai recent fișier HTML din `reports/` (ordonat după `mtime`).
- Grafice secundare permise: evoluția recentă a cursului EUR/RON și evoluția metricilor modelului.

## 10. Instrucțiuni pentru Optuna
- Propune optimizare cu Optuna și GridSearch.
- Experimentele Optuna trebuie salvate (studiile și rezultatele) pentru analiză ulterioară.
- Frontend-ul trebuie să arate fișiere/studii relevante sau un mesaj controlat.
- Optuna NU se rulează fără acordul explicit al utilizatorului.

## 11. Instrucțiuni pentru Git
- Descrie pașii pentru publicarea pe GitHub și crearea repo-ului.
- Documentează pașii și păstrează un fișier cu instrucțiuni pentru publicare.
- Nu face commit fără acord.
- `.env` NU se urcă pe GitHub.
- `.gitignore` trebuie să includă minim:
  - `.env`
  - `frontend/.env`
  - `**/__pycache__/`
  - `*.pyc`
- În arhiva finală nu include: `.env`, `.git`, `__pycache__`, chei API reale.

## 12. Instrucțiuni pentru chatbot
- Chatbot integrat în frontend; răspunde natural în limba română despre cursuri valutare.
- Chatbotul folosește funcții din aplicație ca tool-uri (tool registry).
- Tool-urile principale documentate:
  - `get_latest_forecast` → `GET /api/forecast/latest`
  - `get_latest_rates` → `GET /api/rates`
  - `get_latest_training_run` → `GET /api/runs?limit=1`
  - `trigger_scrape` → `POST /api/scrape`
- Chatbotul decide ce tool să folosească în funcție de întrebarea utilizatorului.
- Dacă LLM-ul nu este disponibil, folosește fallback local.
- Chatbotul afișează sursa răspunsului: `GEMINI TOOLS`, `GEMINI`, `LOCAL`, `LOCAL FALLBACK`.

## 13. Instrucțiuni pentru tool-uri și tool registry
- Trebuie să existe `TOOL_REGISTRY` și o funcție `execute_tool_call`.
- Tool-urile trebuie documentate cu nume, descriere și parametri.
- Tool-ul principal de examen: `get_latest_forecast`.
- Tool-urile trebuie documentate în `concept_tool.md`.
- Gemini trebuie să poată rula tool routing; la eșec se folosește fallback local.
- Răspunsurile nu trebuie să afișeze dict-uri brute; formatează rezultatele natural în limba română.

## 14. Instrucțiuni pentru LLM și .env
- LLM principal: Google Gemini.
- Configurarea se face prin fișier `.env` în rădăcina proiectului.
- Variabile exemple în `.env` (nu le include reale):
  - `GEMINI_API_KEY=...`
  - `GEMINI_MODEL=gemini-flash-latest`
- `.env` nu se urcă pe GitHub.
- Dacă Gemini returnează quota exceeded / 429 RESOURCE_EXHAUSTED, aplicația trebuie să afișeze un mesaj scurt și controlat către utilizator.
- Cheile API nu trebuie afișate în UI sau în loguri publice.

## 15. Instrucțiuni pentru arhiva finală
- Arhiva finală (livrabil) trebuie să conțină: `backend/`, `frontend/`, `src/`, `data/`, `models/`, `reports/`, `agentic_docs/`, `requirements.txt`, `README.md`, `.gitignore`, `.env.example`.
- Arhiva nu trebuie să conțină: `.env`, `.git`, `__pycache__`, chei API reale.
- Documentele agentice și planurile trebuie să fie în `agentic_docs/`.

## 16. Lista prompturilor de bază folosite
Instrucțiunile de mai sus au fost derivate din prompturile principale folosite pe parcursul dezvoltării. Exemple de prompturi folosite:
- Prompt 1: plan scraping curs BNR
- Prompt 2: plan antrenare 3 modele
- Prompt 3: validare încrucișată pentru serii temporale
- Prompt 4: implementare pe rând cu aprobare
- Prompt 5: feature-uri XGBoost și extindere SARIMA
- Prompt 6: GridSearch Prophet
- Prompt 7: instalare requirements
- Prompt 8: reguli Gemini.md
- Prompt 11: restructurare proiect
- Prompt 12: arhivare proiect inițial și agentic_docs
- Prompt 13: plan optimizare GridSearch/Optuna
- Prompt 14: rulare Optuna și salvare experimente
- Prompt 16-18: GitHub (pași publicare)
- Prompt 19-21: formatare, verificare, commit
- Prompt 22-23: aplicație frontend/backend
- Prompt 24-29: chatbot, tool-uri, concept_tool.md, plan_implementare_chatbot.md, .env

## 17. Legătura cu planurile existente
Planurile rezultate în urma discuțiilor sunt salvate în `agentic_docs/` și includ (printre altele):
- `PLAN_SCRAPING.md`
- `PLAN_ANTRENARE_3_MODELE.md`
- `PLAN_OPTIMIZARE_HYPERPARAMETRI.md`
- `Refactorizare_cod.md`
- `plan_implementare_frontend_backend.md`
- `plan_import_scraper_sqlite.md`
- `concept_tool.md`
- `plan_implementare_chatbot.md`
- `INSTRUCTIUNI_LLM_CONFIG.md`
- `idei_de_imbunatatire.md`
- `RAPORT_FINAL_FAZA4.md`
- `verificare_corectii_importuri.md`

## IMPORTANT - restricții și bune practici în lucru
- Nu modifica fișiere de cod fără aprobare.
- Nu rula aplicația, training-ul sau Optuna fără acord explicit.
- Nu face commit fără confirmare.

---

Fișier creat: `agentic_docs/INSTRUCTIUNI_AGENT.md`
