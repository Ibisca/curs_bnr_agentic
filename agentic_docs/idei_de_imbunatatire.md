# Variante de model final
- cel mai bun model este cel care are cele mai bune rezultate la testele de performanta
- ensemble model: o medie ponderata a predictiilor celor mai bune modele
- adaugarea de noi modele: lstm
- optimizarea parametrilor modelului folosind optuna

# Refactoring
- aplicatie front end cu streamlit si back end cu fastapi

## Front end
- dashboard cu grafice si tabele aferente modelului antrenat si salvat si folosit ca model default
- posibilitatea de a selecta valuta si data si de a specifica pasi de transformare a datelor daca e cazul (ex. la xgboost sa poti selecta numarul de arbori, la lstm sa poti selecta numarul de epoci, etc.)
- tab cu:
    - selectarea unuia sau mai multor modele antrenate pentru inspectie (grafice si tabele)
    - rezultatele antrenarii
    - rezultatele evaluarii
    - rezultatele compararii
    - selectarea si salvearea modelului final si activarea ca model default

- tab cu integrarea optuna-dashboard pentru antrenarea si optimizarea parametrilor modelului (sau cu link catre dashboard-ul optuna?)

## Back end
- API REST cu endpoint-uri pentru predictii
- API REST cu endpoint-uri pentru grafice
- API REST cu endpoint-uri pentru tabele
- API REST cu endpoint-uri pentru antrenare (ar trebui reantrenare la cerere, cu posibilitatea de a selecta modelul si data, sau toate modelele, cu posibilitatea de a salva modelul antrenat)
- API REST cu endpoint-uri pentru evaluare (ar trebui evaluare la cerere, cu posibilitatea de a selecta modelul si data, sau toate modelele, cu posibilitatea de a salva modelul antrenat)
- API REST cu endpoint-uri pentru comparare (ar trebui comparare la cerere, cu posibilitatea de a selecta modelul si data, sau toate modelele, cu posibilitatea de a salva modelul antrenat)
- API REST cu endpoint-uri pentru selectarea modelului final (ar trebui selectare la cerere, cu posibilitatea de a selecta modelul si data, sau toate modelele, cu posibilitatea de a salva modelul antrenat)

## De analizat
- cauta date economice care ar putea fi adaugate ca feature-uri in model: istoric dobanda de referinta BNR, istoric inflatie, istoric PIB, istoric somaj, etc.