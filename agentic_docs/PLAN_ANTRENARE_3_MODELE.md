# Plan pentru antrenarea a 3 modele de prognoză a cursului de schimb (ziua următoare)

## Obiectiv
- Prezice valoarea cursului de schimb pentru ziua următoare folosind seria istorică colectată.
- Antrenați și comparați 3 modele diferite: SARIMA, Prophet, XGBoost. Alegeți cel mai performant model, salvați-l și testați-l pe ultimele 2 săptămâni din perioada de observații.
- Produceți un raport de antrenare cu metrici relevante și o vizualizare Plotly a prognozei incluzând interval de încredere.

## Dataset & structură
- Date intrare: fișier CSV rezultat din scraping-ul tabelului `#table-currencies` (coloane minime: `date`, `currency`, `rate`).
- Perioadă observată: toată perioada disponibilă în CSV; rezervă ultimele 14 zile pentru test final.
- Precondiții: date ordenate cronologic, un singur rând/valută/zi sau agregare la nivel de zi.

## Curățare și preprocesare (pas cu pas)
1. Validare: verificați valori lipsă, dubluri, date invalide.
2. Tratamente:
   - Eliminare sau imputare a valorilor lipsă (linear interpolate sau forward-fill pentru serii temporale).
   - Conversie dată în tip datetime și setare ca index de serie temporală.
   - Filtrare/normalizare curs după necesitate (de exemplu log-transform dacă distribuția e skewed).
3. Resample (dacă există intrări multiple pe zi): luați media/mediana la nivel zilnic.
4. Split temporal:
  - Train/validation/test: Rezervați ultimele 14 zile pentru test final.
  - Pentru validare și tuning folosiți validare încrucișată specifică seriilor temporale (walk-forward / expanding-window validation) implementată cu `sklearn.model_selection.TimeSeriesSplit` sau o strategie custom de "rolling-origin":
    - Configurați `K` folds (ex: K=5) sau definiți ferestre expandate; pentru fiecare fold: `train` = toate observațiile până la t_i, `validation` = următoarea fereastră (ex: următoarele N zile).
    - Păstrați ordinea temporală (nu amestecați/schimbați rândurile) și folosiți `gap`/`max_train_size` după necesitate pentru a evita leak.
    - Agregați metrici (mean, std) peste folds pentru selecția hiperparametrilor și early stopping.
  - Alternative: TimeSeriesCV cu parametri personalizați (pas de salt, dimensiune fereastră) sau o abordare walk-forward care reantrenează modelul incremental pentru fiecare pas de validare.

## Feature engineering
- Funcții de timp: zi a săptămânii, luni, zi în an, indicator zi lucrătoare/weekend, sărbători (opțional).
- Lag features: rate lag-1, lag-2, lag-7, lag-14.
- Rolling statistics: rolling mean/std pe ferestre 3/7/14 zile.
- Expanding stats (cumulativ): expanding mean.
- Seasonal indicators: sin/cos pentru componente sezoniere (ex: anuală) dacă e nevoie.
- Volatilitate: rolling volatility.
- Moving averages: includeți mediile mobile pe 7 și 14 zile (`ma_7`, `ma_14`) ca feature-uri pentru modelele bazate pe machine learning (ex: XGBoost).
- Pentru modele statistice (ARIMA/Prophet) reduceți feature set la cele necesare.

## Modele propuse (trei variante)
1. Model determinist-statistic: ARIMA/SARIMA
  - Motivație: bun pentru componente autoregresive și sezoniere clare.
  - Configurare: identificare p,d,q și sezonal P,D,Q folosind ACF/PACF sau automatizare (pmdarima.auto_arima).
  - Output: forecast + prediction intervals (built-in).

2. Model tipastic/automatizat: Prophet (sau similar)
  - Motivație: ușor de folosit pentru serii cu trend și sezonalitate; oferă intervale de încredere.
  - Configurare: include sezonalitate zilnică/săptămânală/anuală, holidays dacă sunt relevante.
  - Grid search recomandat pentru hiperparametrii importanți:
    - `changepoint_prior_scale`: [0.001, 0.01, 0.1, 0.5]
    - `seasonality_prior_scale`: [0.01, 0.1, 1.0, 10.0]
    - `seasonality_mode`: ['additive', 'multiplicative']
    - `holidays_prior_scale`: [0.01, 0.1, 1.0]
    - `changepoint_range`: [0.8, 0.9]

3. Model tree-based: XGBoost (Gradient Boosted Trees)
  - Motivație: performanță bună pe feature-uri tabulare, folosește lag-uri și statistici rolling eficient.
  - Features recomandate: lag-uri (1,2,7,14), mediile mobile `ma_7` și `ma_14`, rolling mean/std, funcții de timp.
  - Hyperparametri de explorat:
    - `eta` (learning rate)
    - `gamma` (min loss reduction to make a further partition)
    - `subsample`
    - `n_estimators`: [50, 100, 200]
    - `max_depth`: [4, 5, 6]
  - Metodă: TimeSeriesSplit pentru validare, scalare/encoding după necesitate, grid/search sau Bayesian tuning pe parametrii de mai sus.


## Metodologie de antrenare și validare
- Cross-validation: folosiți TimeSeriesSplit (walk-forward validation) sau expanding-window CV pentru tuning.
- Hyperparameter tuning:
  - SARIMA/ARIMA: explorați diferite seturi pentru `order` și `seasonal_order`; exemple recomandate de valori:
    - `order` (p,d,q): p in [0,1,2,3,4], d in [0,1,2], q in [0,1,2,3]
    - `seasonal_order` (P,D,Q,s): P in [0,1,2], D in [0,1], Q in [0,1,2], s = sezonality period (ex: 7 pentru săptămânal, 12/365 pentru lunar/anual după necesitate)
    - Utilizați `pmdarima.auto_arima` pentru a restrânge spațiul sau un grid search restrâns pe aceste intervale.
  - Prophet: folosiți grid search pe hiperparametrii importanți; exemple recomandate:
    - `changepoint_prior_scale`: [0.001, 0.01, 0.1, 0.5]
    - `seasonality_prior_scale`: [0.01, 0.1, 1.0, 10.0]
    - `seasonality_mode`: ['additive', 'multiplicative']
    - `holidays_prior_scale`: [0.01, 0.1, 1.0]
    - `changepoint_range`: [0.8, 0.9]
  - XGBoost: explorați parametrii specifici:
    - `eta` (learning rate)
    - `gamma`
    - `subsample`
    - `n_estimators`: [50, 100, 200]
    - `max_depth`: [4, 5, 6]
  - Early stopping pe setul de validare pentru modelele iterative (de ex. XGBoost) sau la antrenarea rețelelor neuronale, după caz.

## Metrici pentru evaluare
- Metrici principale:
  - MAE (Mean Absolute Error)
  - RMSE (Root Mean Squared Error)
  - MAPE (Mean Absolute Percentage Error) — cu atenție la valori foarte mici
- Metrici suplimentare:
  - R2 (pentru referință)
  - Coverage al intervalelor de predicție (proporția observațiilor reale care cad în intervalul de încredere)
  - Prediction interval width (lățimea medie a intervalelor) — trade-off între acoperire și precizie
- Raportați metricile pe setul de validare și pe testul final (ultimele 14 zile).

## Interval de încredere (confidence interval)
- ARIMA/Prophet: folosesc intervale de predicție native.
- XGBoost / tree-based: estimați incertitudinea prin:
  - Ensembles / bootstrap: antrenați K modele pe subsample-uri (sau folosiți bootstrapping) și folosiți percentila inferențelor pentru intervale.
  - Quantile regression (antrenați modele pentru quantile separate, ex: 0.025, 0.975) sau folosiți implementări care suportă quantile.
  - Conformal prediction: calibrați intervalele pe setul de validare pentru acoperire garantată empiric.
- Target: produce interval la nivel ~95% (sau parametrizabil).

## Selectarea modelului final și salvare
1. Comparați performanța pe setul de validare folosind MAE/RMSE/coverage.
2. Alegeți modelul care oferă cel mai bun trade-off (ex: MAE cel mai mic + acoperire rezonabilă a CI).
3. Retrainați modelul selectat pe întregul set de antrenament+validare (toată perioada înainte de ultimele 14 zile) dacă e justificat.
4. Salvați modelul:
   - ARIMA/Prophet: serializare (pickle) sau metoda specifică bibliotecii.
   - XGBoost: salvați modelul cu `joblib` sau `pickle` și păstrați artefactele (feature list, scaler, config.json).
5. Documentați versiunea modelului, hiperparametrii și seed folosit pentru reproducibilitate.

## Test final pe ultimele 2 săptămâni
- Rulați modelul salvat pe ultimele 14 zile (forecast țintă: predicție ziua următoare în mod iterativ sau direct, în funcție de setup).
- Măsurați aceleași metrici (MAE, RMSE, MAPE, coverage).
- Raportați eroarea zilnică și medii pe cele 14 zile.

## Vizualizare (Plotly)
- Plotați serie istorică (ultimele N zile, ex: 90 zile), predicțiile pentru perioada test (14 zile) și intervalele de încredere (banda semi-translucentă).
- Includeți hover info: dată, valoare observată, predicție, CI lower/upper.
- Adăugați subplot pentru erori (observed - predicted) pe perioada test.

## Raport de antrenare (conținut recomandat)
- Rezumat executiv: ce s-a făcut, ce modele, ce metrici.
- Descriere date: sursă, perioadă, curățări importante.
- Feature engineering aplicat.
- Setări de training și hyperparametri pentru fiecare model.
- Tabel comparativ al metricilor (train/validation/test) pentru toate modelele.
- Grafice:
  - Learning curves (train vs val loss) pentru XGBoost (sau diagnosticele de training) și diagnostic Prophet (changepoints, components).
  - Feature importance / SHAP pentru XGBoost.
  - Forecast vs Observed + CI (Plotly) pentru test final.
  - Distribuția erorilor.
- Decizie: model ales și justificare.
- Pași următori și recomandări (ex: pipeline de reantrenare, monitorizare drift).

## Reproducibilitate și operare
- Salvați:
  - fișier `requirements.txt` sau environment.yml
  - script/Notebook de antrenare (versiune + seed)
  - model serializat + artefacte (scaler, config.json)
  - small README cu comenzi de rulare
- Recomandare: folosiți experiment tracking (MLflow, Weights & Biases) pentru log metrici și artefacte.

## Calendar estimativ (orientativ)
- Pregătire date & EDA: 0.5–1 zi
- Feature engineering + splits: 0.5 zi
- Antrenare modele & tuning (paralelizabil): 1–2 zile
- Evaluare finală, retraining, salvare model: 0.5 zi
- Raport și vizualizări: 0.5 zi

## Livrabile
- Fișier Markdown cu acest plan (acesta).
- Specificație CSV de intrare și schema coloane.
- Lista de artefacte rezultate după antrenare (model, scaler, config, raport, grafic Plotly interactic).

---

Dacă dorești, pot:
- genera un notebook/șablon de antrenare (fără date sensibile) pe baza acestui plan,
- sau pot rula pașii efectiv (scraping -> antrenare) dacă-mi confirmi accesul la date și mediul de execuție.
