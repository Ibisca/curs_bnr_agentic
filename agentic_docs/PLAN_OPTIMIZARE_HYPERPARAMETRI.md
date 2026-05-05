# Plan de optimizare a hiperparametrilor — SARIMA / Prophet / XGBoost

Scop
- Propunere detaliată pentru optimizarea hiperparametrilor modelelor existente în proiect (SARIMA, Prophet, XGBoost).
- Sunt incluse două variante de optimizare: GridSearch (determinist, exhaustiv pe spații mici) și Optuna (căutare eficientă, cu pruning).
- Planul este adaptat la structura actuală a proiectului și include fișierele ce trebuie modificate/adiționate.

Context proiect
- Cod existent: `src/models/models.py` implementează tune_sarima, tune_prophet, tune_xgboost folosind TimeSeriesSplit și grid combinatoric.
- Pipeline actual: `src/pipeline/train_pipeline.py` apelează tune_* și urmează să folosească rezultatele pentru salvare/evaluare.

Rezumat decizii (recomandări)
- GridSearch (recomandat pentru):
  - Prophet — spațiul de hiperparametri este mic și discret (changepoint_prior_scale, seasonality_prior_scale, mode, holidays_prior_scale, changepoint_range). GridSearch e robust și ușor de interpretat.
  - SARIMA — dacă se folosește un set restrâns de `orders` și `seasonal_orders` (discrete), GridSearch/scan exhaustiv rămâne potrivit; recomand însă restrângerea spațiului inițial cu heuristici (auto_arima) înainte de grid.
- Optuna (recomandat pentru):
  - XGBoost — spațiu mare, combină hiperparametri continui și discreți (eta, gamma, subsample, colsample_bytree, n_estimators, max_depth, min_child_weight, reg_alpha/reg_lambda). Optuna oferă tuning eficient, pruning și posibilitate de optimizare multi-criteriu.

Motivație
- XGBoost antrenează rapid pe seturi tabulare și se beneficiază de pruning (Optuna) pentru a economisi timp în combinații slabe.
- SARIMA e costisitor per-fit; un grid restrâns sau o etapă de pre-filtrare (pmdarima.auto_arima) reduce riscul explorării inutile.
- Prophet are un set clar de valori recomandate — grid-ul e simplu și replicabil.

Detalii — Variantă GridSearch
1. Principiu
   - Pentru fiecare model definim un grid discret de valori; folosim `TimeSeriesSplit` (walk‑forward / expanding window) pentru a estima performanța medie pe folduri.
   - Metrică pentru selecție: MAE (primary), RMSE (tie-breaker), raportați și MAPE.
2. SARIMA
   - Grid input: liste restrânse pentru `order` și `seasonal_order` (de ex. p in [0,1,2], d in [0,1], q in [0,1,2]; P in [0,1], D in [0,1], Q in [0,1], s=[7]).
   - Workflow: (a) rulați grid cu TimeSeriesSplit (n_splits=3..5), (b) selectați combinația cu MAE mediu minim, (c) retrain pe întregul set de antrenament (excluzând ultimele 14 observații) și evaluați pe test.
3. Prophet
   - Grid input: folosiți setul deja din plan (`changepoint_prior_scale`, `seasonality_prior_scale`, `seasonality_mode`, `holidays_prior_scale`, `changepoint_range`).
   - Workflow: aceleași reguli CV; alegere pe MAE mediu.
4. XGBoost (Grid)
   - Grid input redus (pentru reproducibilitate): `eta` in [0.01,0.1], `gamma` in [0,0.1], `subsample` in [0.7,1.0], `n_estimators` in [100,200], `max_depth` in [4,6].
   - Workflow: TimeSeriesSplit, scor MAE; dacă spațiul devine mare, treceți la Optuna.

Detalii — Variantă Optuna (recomandată pentru XGBoost)
1. Principiu
   - Definim un studiu Optuna cu funcție obiectiv care: construiește features (folosind `build_features`), împarte date cu TimeSeriesSplit, antrenează XGBoost cu parametrii propusi de trial, aplică pruning pe baza performanței pe fold-urile timpurii/val și returnează scorul (MAE mediu) ca valoare de optimizat.
   - Folosiți `optuna.samplers.TPESampler()` și `optuna.pruners.MedianPruner()` sau `SuccessiveHalvingPruner` pentru eficiență.
2. Hiperparametri sugerați pentru search (exemple):
   - `learning_rate` (eta): log-uniform 1e-4 – 0.3
   - `gamma`: log-uniform 1e-8 – 10
   - `subsample`: uniform 0.5 – 1.0
   - `colsample_bytree`: uniform 0.5 – 1.0
   - `max_depth`: int 3 – 10
   - `min_child_weight`: log-uniform 1e-3 – 10
   - `reg_alpha`, `reg_lambda`: log-uniform 1e-8 – 10
   - `n_estimators`: int 50 – 1000, dar folosiți early_stopping_rounds pe un set de validare intern pentru a limita numărul de arbori.
3. Implementare Optuna specifics
   - folosiți pruning callback (Optuna XGBoostPruningCallback) sau implementați early stopping pe fiecare fit și raportați cel mai bun scor.
   - rulați multiple trial-uri (ex: 50–200) în funcție de resurse.

Validare pentru serii temporale (common rules)
- Folosiți `TimeSeriesSplit` (sklearn) sau o strategie expanding-window (rolling-origin): păstrăm ordinea temporală, fără shuffling.
- Pentru GridSearch: folosiți același `tscv.split()` pentru a calcula scoruri pe fiecare combinație.
- Pentru Optuna: în funcția obiectiv, faceți CV folosind aceleași split-uri și returnați scorul mediu pe fold-uri; pentru pruning, folosiți un scor pe primul fold/etape intermediare.
- Evitați leakage: nu folosiți date din validare pentru calculul statisticilor care sunt aplicate train+val (aplicați transformările numai pe train sau aplicați transformările în pipeline compatibil cu scikit-learn care rulează `fit` pe train și `transform` pe val/test).

Metrici și criterii de selecție
- Metrică principală: MAE (Mean Absolute Error) — robustă pentru magnitudini ale cursurilor.
- Metrici secundare: RMSE (penalizează erori mari), MAPE (utile pentru raport), Coverage pentru intervale de predicție (SARIMA/Prophet) — raportați % observații acoperite.
- Selecție finală: alegeți modelul cu cel mai mic MAE mediu pe folds; în caz de rezultate apropiate, folosiți RMSE sau coverage pentru a alege (ex: preferați model cu puțin mai mare MAE dar CI coverage mai bun).

Fișiere ce trebuie modificate / adăugate
- Modificări recomandate (cod):
  1. `src/models/models.py`
     - Păstrați funcțiile GridSearch actuale pentru SARIMA și Prophet (ușoare ajustări pentru parametri și toleranță la erori).
     - Refactor: extrageți logica XGBoost actuală într-o funcție separată care acceptă fie `param_grid` (Grid) fie un `tuner` (Optuna). Sau adăugați o funcție `tune_xgboost_optuna(...)` care implementează Optuna.
  2. `src/tuning/optuna_tuner.py` (nou, recomandat)
     - Implementați interfața Optuna generică pentru XGBoost (funcție obiectiv, pruning callback, raportare/logging). Acest modul poate expune `optuna_tune_xgboost(df_features, n_trials, n_splits, timeout=None, seed=None)`.
  3. `src/pipeline/train_pipeline.py`
     - Adăugați opțiune CLI pentru a alege metoda de tuning (`--tuner grid|optuna` sau `--use-optuna`), parametrizabil `--n-trials`.
     - Apelați noile funcții în funcție de alegere.
  4. `requirements.txt`
     - Dacă decideți să folosiți Optuna, adăugați `optuna` în requirements (opțional `optuna-dashboard`).
  5. `agentic_docs/PLAN_OPTIMIZARE_HYPERPARAMETRI.md` (acest fișier) — documentație plan.
- Fișiere adiționale opționale:
  - `config/tuning.yaml` pentru setări implicite (grid values, optuna settings, n_trials, timeout).
  - script helper `scripts/run_tuning.py` pentru rulare directă a tuning-ului (separate de pipeline).

Estimări de resurse și timpi
- Grid SARIMA: cost mare per combinație; recomand testare cu spațiu mic (zeci de combinații) sau folosirea `pmdarima.auto_arima` pentru a sugera porțiuni.
- Grid Prophet: relativ rapid; grid mic (de zeci de combinații) e OK.
- Optuna XGBoost: 50–200 trial-uri; fiecare trial rulează CV TimeSeriesSplit (n_splits=3) — reglați `n_trials` în funcție de resurse.

Pași de implementare propusi (după aprobare)
1. Adaug `agentic_docs/PLAN_OPTIMIZARE_HYPERPARAMETRI.md` (acest fișier).
2. Creez `src/tuning/optuna_tuner.py` cu implementarea Optuna pentru XGBoost.
3. Extind `src/models/models.py` sau extrag părți pentru a folosi noul tuner.
4. Adaug opțiuni CLI în `src/pipeline/train_pipeline.py` și un `scripts/run_tuning.py` simplu.
5. Actualizez `requirements.txt` (adaug `optuna` dacă aprobi Optuna ca dependență).
6. Rulez un test scurt pe EUR dataset cu `--n-trials=10` pentru validare funcțională.

Cerere aprobare
- Am salvat acest plan în `agentic_docs/PLAN_OPTIMIZARE_HYPERPARAMETRI.md`.
- Te rog confirmă (OK / modificări solicitate) înainte să încep implementarea efectivă (creare fișiere, adăugare `optuna` în `requirements.txt`, modificare `train_pipeline`).

