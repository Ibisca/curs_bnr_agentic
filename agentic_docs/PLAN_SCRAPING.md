la primul promt mi ai zis asaȘ Voi crea un plan de lucru (TODOs) structurat pentru scraping-ul cerut.

Created 7 todos

Plan (sumar & pași)

Obiectiv: Scrape historic cursuri din https://www.cursbnr.ro/curs-valutar-bnr setând dataStart la 22/02/2020 și selectând valuta prin numele din elementul <select name="currency">, apoi extragând rândurile din tabelul id="table-currencies" și salvând într-un CSV.

Pași:

1. Setup environment + deps: creați un mediu Python și instalați dependențele.
2. Implement scraper script: script Python care construiește cererea (GET/POST) și obține pagina răspuns.
3. Add CLI/currency + date params: parametrizare pentru currency (numele exact) și dataStart (ex: 22/02/2020).
4. Parse table #table-currencies: folosiți BeautifulSoup pentru a extrage anteturi și rânduri.
5. Save results to CSV: salvați într-un fișier CSV cu coloane corecte (Data, Valuta, Curs).
6. Add retries & error handling: tratați timeouts, coduri HTTP, și încercări repetate.
7. Write README + usage: instrucțiuni de instalare și exemple de rulare.
Dependențe propuse (minime)

Pachete: requests, beautifulsoup4, lxml, pandas, python-dateutil, tqdm
Opțional (dacă site-ul folosește JS): selenium, webdriver-manager
Instalare rapidă (pip):

Conținut recomandat pentru requirements.txt:
requests
beautifulsoup4
lxml
pandas
python-dateutil
tqdm

optional
selenium
webdriver-manager

Vrei să continui și să scriu scriptul Python complet care:

setează dataStart = "22/02/2020",
acceptă parametrul currency (numele din <select>),
parsează #table-currencies,
salvează output.csv ?