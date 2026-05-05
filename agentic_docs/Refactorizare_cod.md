# Refactorizare cod — sumar scurt

Am restructurat proiectul pentru claritate și modularitate, mutând modulele în subpachete sub `src/`.

Ce s-a făcut:
- Am creat subpachete: `src/scraping`, `src/data`, `src/features`, `src/models`, `src/evaluation`, `src/visualization`, `src/pipeline`.
- Fiecare modul original a fost copiat în subpachetul corespunzător păstrând logica (ex: `scraper.py`, `data_loader.py`, `features.py`, `models.py`, `evaluate.py`, `plotly_viz.py`, `train_pipeline.py`).
- Am adăugat wrapper-e/`__init__.py` pentru compatibilitate API și pentru a păstra importurile existente.
- Am corectat probleme minore descoperite în proces:
  - Unterminated triple-quoted string în wrapperul top-level `src/data_loader.py` (fixat)
  - Mesaje argparse cu diacritice care cauzau erori pe unele medii — am înlocuit text non-ASCII cu texte ASCII în descrieri/help.
- Am creat un snapshot arhivat al codului original în `archive_original_project/src/` (conține copiile modulelor originale). Acest folder păstrează versiunea veche înainte de refactor.

Aspecte practice:
- Pip install: folosiți `pip install -r requirements.txt` înainte de rulare (opțional `plotly` pentru vizualizări interactive).
- Rulare:
  - Scraper: `python -m src.scraping.scraper "Euro"`
  - Pipeline complet: `python -m src.pipeline.train_pipeline --csv <data_csv>`
  - Evaluare: `python -m src.evaluation.evaluate --csv <data_csv> --model models/best_model_X.pkl`
  - Vizualizare: `python -m src.visualization.plotly_viz --plot-csv <plot_csv> --out-dir reports`

Limitări cunoscute:
- Dependințe opționale: `plotly`, `prophet`, `statsmodels`, `xgboost` pot lipsi; codul tratează importuri opțional și va produce avertismente sau excepții la rulare dacă lipsesc.
- Am păstrat logica inițială fără refactorizare semnificativă; dacă doriți, pot aplica refactorizări suplimentare (docstrings, typing, testare unitară).

Doriți să finalizez arhivarea (zip) și să actualizez `README.md` cu instrucțiuni concise de utilizare? Hvis da, pot continua.