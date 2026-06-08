# AIE_CursValutar — Proiect Final

Aplicație pentru colectarea, stocarea, analizarea și prognozarea cursului valutar EUR/RON, realizată pentru proiectul final AIE.

Proiectul include:

* backend FastAPI;
* frontend Streamlit;
* bază de date SQLite;
* scraper pentru date BNR;
* import CSV;
* reantrenare model la cerere;
* istoric rulări de antrenare;
* prognoze salvate în baza de date;
* grafic Plotly pentru forecastul celui mai bun model;
* chatbot incorporat cu Gemini LLM, tool registry și fallback local;
* documente agentice și planuri de implementare salvate în `agentic_docs/`.

---

## 1. Cerința proiectului

Cerința principală a fost realizarea unei aplicații frontend/backend care să includă:

* scraper pentru colectarea cursului valutar;
* parte de reantrenare modele;
* grafic cu forecastul celui mai bun model;
* chatbot incorporat;
* tool definit care aduce ultima prognoză din baza de date la o cerere în limbaj natural;
* instrucțiuni pentru agent și planuri de implementare salvate.

Toate aceste componente sunt incluse în proiect.

---

## 2. Structura proiectului

```text
AIE_Tema3_CursValutar/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   └── services/
│       ├── forecast_service.py
│       ├── import_service.py
│       ├── plot_service.py
│       ├── rates_service.py
│       ├── runs_service.py
│       └── training_service.py
│
├── frontend/
│   ├── app.py
│   └── chatbot_tools.py
│
├── src/
│   ├── scraping/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   ├── visualization/
│   └── pipeline/
│
├── data/
│   ├── curs_bnr_app.sqlite
│   ├── CSV-uri curs valutar
│   └── fișiere de evaluare/predicții
│
├── models/
│   ├── best_model_XGBoost.pkl
│   └── rezultate Optuna
│
├── reports/
│   ├── forecast_plot_*.html
│   └── forecast_plot_*.json
│
├── agentic_docs/
│   ├── INSTRUCTIUNI_AGENT.md
│   ├── PLAN_SCRAPING.md
│   ├── PLAN_ANTRENARE_3_MODELE.md
│   ├── PLAN_OPTIMIZARE_HYPERPARAMETRI.md
│   ├── Refactorizare_cod.md
│   ├── plan_implementare_frontend_backend.md
│   ├── plan_import_scraper_sqlite.md
│   ├── concept_tool.md
│   ├── plan_implementare_chatbot.md
│   └── INSTRUCTIUNI_LLM_CONFIG.md
│
├── screenshots/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. Instalare dependențe

Se recomandă folosirea unui mediu virtual.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 4. Configurare fișier `.env`

Pentru funcționalitatea Gemini LLM, creează în rădăcina proiectului un fișier `.env`.

Exemplu:

```env
GEMINI_API_KEY=adauga_cheia_ta_aici
GEMINI_MODEL=gemini-flash-latest
```

Fișierul `.env` nu trebuie urcat pe GitHub și nu trebuie inclus în arhiva finală. În proiect există `.env.example` ca model sigur.

Dacă Gemini nu este disponibil sau limita de request-uri este depășită, chatbotul folosește fallback local și aplicația rămâne funcțională.

---

## 5. Pornire backend FastAPI

Backend-ul rulează pe portul `7772`.

```powershell
python -m uvicorn backend.main:app --reload --port 7772
```

Verificare rapidă:

```powershell
curl http://localhost:7772/api/health
```

Răspuns așteptat:

```json
{"status":"ok"}
```

---

## 6. Pornire frontend Streamlit

Într-un terminal separat, pornește frontend-ul:

```powershell
python -m streamlit run frontend/app.py
```

Aplicația se deschide în browser și include următoarele tab-uri:

* Dashboard;
* Date & Scraping;
* Model & Reantrenare;
* Optuna;
* Chatbot.

---

## 7. Endpoint-uri backend

Backend-ul FastAPI expune următoarele endpoint-uri principale:

| Metodă | Endpoint               | Rol                                            |
| ------ | ---------------------- | ---------------------------------------------- |
| GET    | `/api/health`          | Verifică statusul aplicației                   |
| GET    | `/api/rates`           | Returnează ultimele cursuri valutare           |
| GET    | `/api/rates/stats`     | Returnează statistici despre date și duplicate |
| GET    | `/api/forecast/latest` | Returnează ultima prognoză salvată             |
| GET    | `/api/runs`            | Returnează rulările de antrenare               |
| POST   | `/api/init-db`         | Inițializează baza de date                     |
| POST   | `/api/import-rates`    | Importă cursuri din CSV                        |
| POST   | `/api/scrape`          | Rulează scraperul și actualizează datele       |
| POST   | `/api/retrain`         | Reantrenează modelul și salvează metricile     |
| POST   | `/api/generate-plot`   | Regenerează graficul forecast                  |

---

## 8. Baza de date SQLite

Aplicația folosește SQLite.

Fișier principal:

```text
data/curs_bnr_app.sqlite
```

Tabele principale:

### `rates`

Stochează istoricul cursurilor valutare.

Câmpuri importante:

* `date`;
* `currency`;
* `value`;
* `created_at`.

Pentru a preveni duplicatele, aplicația folosește constrângere unică pentru combinația `date + currency`.

### `training_runs`

Stochează istoricul rulărilor de antrenare.

Câmpuri importante:

* `model_name`;
* `parameters_json`;
* `mae`;
* `rmse`;
* `mape`;
* `created_at`.

### `forecasts`

Stochează prognozele generate de cel mai bun model.

Câmpuri importante:

* `forecast_date`;
* `currency`;
* `predicted_value`;
* `model_name`;
* `mae_14_days`;
* `created_at`.

---

## 9. Scraper BNR

Scraperul colectează datele de curs valutar și le salvează în format CSV sau direct în baza de date prin backend.

Rulare directă scraper:

```powershell
python -m src.scraping.scraper "Euro"
```

Rulare prin backend:

```powershell
curl -X POST http://localhost:7772/api/scrape
```

În frontend, funcția este disponibilă în tab-ul:

```text
Date & Scraping
```

---

## 10. Reantrenare model

Aplicația permite reantrenarea modelului din interfață sau prin backend.

Endpoint:

```powershell
curl -X POST http://localhost:7772/api/retrain
```

Reantrenarea rapidă folosește datele EUR/RON din SQLite, construiește feature-uri de tip lag și rolling mean și antrenează un model XGBoost.

Metrici salvate:

* MAE;
* RMSE;
* MAPE.

Rezultatele sunt salvate în:

* `training_runs`;
* `forecasts`;
* `models/`;
* `reports/`.

---

## 11. Modele utilizate

În proiect au fost avute în vedere mai multe modele pentru prognoză:

* XGBoost;
* SARIMA;
* Prophet.

Pentru optimizare au fost folosite sau planificate:

* GridSearch;
* Optuna.

Modelul final folosit în aplicația rapidă de reantrenare este XGBoost, deoarece oferă un echilibru bun între viteză, stabilitate și acuratețe.

---

## 12. Grafice și rapoarte

Graficele sunt generate cu Plotly și salvate în:

```text
reports/
```

Exemple:

```text
forecast_plot_XGBoost_*.html
forecast_plot_XGBoost_*.json
```

În Dashboard, aplicația afișează:

* prognoza curentă;
* KPI pentru MAE;
* graficul forecast al celui mai bun model;
* evoluția recentă a cursului EUR/RON.

Graficul principal acoperă cerința proiectului privind forecastul celui mai bun model.

---

## 13. Chatbot cu Gemini Tools

Aplicația include un chatbot în tab-ul:

```text
Chatbot
```

Chatbotul folosește:

* Google Gemini LLM;
* tool registry;
* JSON tool routing;
* fallback local.

Tool-uri definite:

| Tool                      | Rol                                           |
| ------------------------- | --------------------------------------------- |
| `get_latest_forecast`     | Aduce ultima prognoză din baza de date        |
| `get_latest_rates`        | Aduce ultimele cursuri EUR/RON                |
| `get_latest_training_run` | Aduce ultima rulare de antrenare și metricile |
| `trigger_scrape`          | Actualizează datele BNR prin scraper          |

Tool-ul principal cerut de proiect este:

```text
get_latest_forecast
```

Acesta apelează endpoint-ul:

```text
GET /api/forecast/latest
```

și aduce ultima prognoză din baza de date SQLite.

Exemplu întrebare:

```text
Care este ultima prognoză?
```

Exemplu comportament:

```text
Mod răspuns: GEMINI TOOLS
```

Dacă Gemini nu este disponibil sau depășește quota, chatbotul folosește fallback local și continuă să răspundă pe baza datelor reale din API.

---

## 14. Documente agentice

Cerința proiectului solicită salvarea instrucțiunilor pentru agent și a planurilor de implementare rezultate în urma discuțiilor.

Acestea sunt salvate în:

```text
agentic_docs/
```

Fișiere importante:

| Fișier                                  | Rol                                          |
| --------------------------------------- | -------------------------------------------- |
| `INSTRUCTIUNI_AGENT.md`                 | Instrucțiunile centrale pentru agentul AI    |
| `PLAN_SCRAPING.md`                      | Plan pentru scraping curs BNR                |
| `PLAN_ANTRENARE_3_MODELE.md`            | Plan pentru antrenarea modelelor             |
| `PLAN_OPTIMIZARE_HYPERPARAMETRI.md`     | Plan pentru GridSearch / Optuna              |
| `Refactorizare_cod.md`                  | Plan pentru restructurarea proiectului       |
| `plan_implementare_frontend_backend.md` | Plan pentru FastAPI + Streamlit + SQLite     |
| `plan_import_scraper_sqlite.md`         | Plan pentru import CSV, scraping și SQLite   |
| `concept_tool.md`                       | Conceptul de tool pentru chatbot             |
| `plan_implementare_chatbot.md`          | Planul de implementare chatbot               |
| `INSTRUCTIUNI_LLM_CONFIG.md`            | Configurare Gemini, `.env` și fallback local |
| `RAPORT_FINAL_FAZA4.md`                 | Raport final de implementare                 |
| `verificare_corectii_importuri.md`      | Raport pentru corectarea importurilor        |

---

## 15. Capturi aplicație

Dacă există folderul `screenshots/`, acesta poate conține capturi din aplicație.

Exemple recomandate:

```text
screenshots/01_dashboard.png
screenshots/02_date_scraping.png
screenshots/03_model_retraining.png
screenshots/04_optuna.png
screenshots/05_chatbot_gemini_tools.png
screenshots/06_agentic_docs.png
```

Exemplu includere în README:

```markdown
![Dashboard](screenshots/01_dashboard.png)
![Chatbot](screenshots/05_chatbot_gemini_tools.png)
```

---

## 16. Testare rapidă

Verificare sintaxă:

```powershell
python -m compileall backend frontend src
```

Verificare backend:

```powershell
curl http://localhost:7772/api/health
curl http://localhost:7772/api/forecast/latest
curl "http://localhost:7772/api/rates?limit=5"
curl "http://localhost:7772/api/runs?limit=5"
```

Pornire completă:

Terminal 1:

```powershell
python -m uvicorn backend.main:app --reload --port 7772
```

Terminal 2:

```powershell
python -m streamlit run frontend/app.py
```

---

## 17. Pregătirea arhivei finale

Arhiva finală trebuie să conțină:

```text
backend/
frontend/
src/
data/
models/
reports/
agentic_docs/
requirements.txt
README.md
.env.example
.gitignore
```

Arhiva finală NU trebuie să conțină:

```text
.env
.git/
__pycache__/
*.pyc
```

Denumire recomandată:

```text
Bisca_Ionut_Andrei_AIE_Tema3_CursValutar_Proiect_Final.zip
```

---

## 18. Observații finale

Proiectul îndeplinește cerința finală:

* aplicație frontend/backend;
* scraper;
* reantrenare modele;
* grafic cu forecastul celui mai bun model;
* chatbot incorporat;
* tool definit pentru ultima prognoză din baza de date;
* instrucțiuni agentice și planuri salvate.

Aplicația este proiectată să rămână funcțională și în cazul în care LLM-ul nu este disponibil, datorită fallback-ului local.
