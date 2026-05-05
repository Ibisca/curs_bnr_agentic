# AIE_Tema3_CursValutar — README

Scurt ghid pentru rulare și structură proiect

## Instalare dependințe

Recomandat: folosește un virtualenv.

PowerShell (Windows):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install plotly
```

Linux / macOS (bash):
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install plotly
```

Notă: `plotly`, `prophet`, `statsmodels` și `xgboost` sunt opționale pentru anumite etape (vizualizare, Prophet, SARIMA, XGBoost).

## Rulare scraping

Scrapează seria istorică pentru o valută (numele exact din `<select name="currency">`):

```powershell
python -m src.scraping.scraper "Euro"
```

Rezultatul: CSV salvat în `data/` (ex: `EUR_from_2020-02-22_YYYYMMDD_HHMMSS.csv`).

## Rulare pipeline (antrenare + evaluare + raport)

Pipeline complet — antrenează modelele, selectează cel mai bun (XGBoost-Optuna), evaluează și generează plot interactiv:

```powershell
python -m src.pipeline.train_pipeline --csv data/<your_csv>.csv --bootstrap 50 --n-splits 3
```

Opțiuni importante:
- `--csv`: calea către CSV-ul generat de scraper (sau un CSV preprocesat)
- `--bootstrap`: numărul de retrain pentru CI XGBoost la evaluare (50 implicit)
- `--n-splits`: numărul de split-uri TimeSeriesSplit pentru tuning (3 implicit)

## Evaluare pe ultimele 14 zile

Poți rula evaluarea separat dacă ai un model salvat:

```powershell
python -m src.evaluation.evaluate --csv data/<your_csv>.csv --model models/best_model_X.pkl --bootstrap 50
```

Dacă nu specifici `--model`, scriptul va încerca să folosească cel mai recent `models/best_model_*.pkl` din `models/`.

## Generare vizualizare Plotly

Scriptul pentru generarea HTML interactiv folosește fișierele `plot_data_*.csv` produse la evaluare.

```powershell
python -m src.visualization.plotly_viz --plot-csv data/plot_data_<model>_YYYYMMDD_HHMMSS.csv --out-dir reports --model <ModelName>
```

Output: HTML interactiv și JSON în `reports/`.

## Structura finală a proiectului

- [agentic_docs/](agentic_docs/)
  - [idei_de_imbunatatire.md](agentic_docs/idei_de_imbunatatire.md)
  - [PLAN_ANTRENARE_3_MODELE.md](agentic_docs/PLAN_ANTRENARE_3_MODELE.md)
  - [PLAN_OPTIMIZARE_HYPERPARAMETRI.md](agentic_docs/PLAN_OPTIMIZARE_HYPERPARAMETRI.md)
  - [PLAN_SCRAPING.md](agentic_docs/PLAN_SCRAPING.md)
  - [Refactorizare_cod.md](agentic_docs/Refactorizare_cod.md)
- [archive_original_project/](archive_original_project/)
  - src/ (snapshot al codului original înainte de refactor)
- [data/](data/) (output CSV-uri, predicții, plot-ready CSV)
- [models/](models/) (modele salvate și rezultate Optuna, ex: `optuna_xgboost_results_*.json`)
- [notebooks/](notebooks/)
- [reports/](reports/) (HTML/JSON Plotly)
- [src/](src/)
  - scraping/scraper.py
  - data/data_loader.py
  - features/features.py
  - models/models.py
  - evaluation/evaluate.py
  - visualization/plotly_viz.py
  - pipeline/train_pipeline.py
- [requirements.txt](requirements.txt)
- [README.md](README.md)
- [workspace_smoke_test.py](workspace_smoke_test.py)
- full_page.html
- tmp_arhiva.html
- tmp_form.html
- tmp_table.html

## Note și recomandări

- Modelul final obținut este XGBoost-Optuna, optimizat cu Optuna pentru hiperparametri.
- Înainte de rulare, asigură-te că fișierele din `data/` au coloane `date` și `rate` sau sunt în formatul așteptat de `src.data_loader.preprocess()`.
- Dacă lipsește vreo librărie (ex: `prophet`), scripturile vor arunca ImportError pentru modelul respectiv — poți instala pachetul necesar doar când ai nevoie.
- Pentru debug rapid, redu `--n-splits` și `--bootstrap` la valori mici.