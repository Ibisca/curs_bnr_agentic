"""
Scraper pentru https://www.cursbnr.ro/curs-valutar-bnr

Cerinte:
- parametrul valuta este numele exact al valutei asa cum apare in <select name="currency"> (ex: "Euro")
- dataStart este setata la 22/02/2020
- extrage tabelul cu id="table-currencies"
- salveaza CSV in folderul data/
- include retry, tratare erori si mesaje clare in consola

Folosire:
python -m src.scraping.scraper "Nume Valuta"

"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Config
URL = "https://www.cursbnr.ro/curs-valutar-bnr"
DATA_START = "22/02/2020"
TIMEOUT = 10  # seconds for requests
RETRY_TOTAL = 3


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_session_with_retries(total: int = RETRY_TOTAL, backoff_factor: float = 0.3) -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def find_form_and_prepare_payload(soup: BeautifulSoup, currency_name: str) -> Optional[Dict[str, str]]:
    """Găsește formularul de pe pagină și construiește payload-ul cu currency și dataStart.

    Returnează dict cu: method, action (url), payload dict
    """
    form = soup.find("form")
    if not form:
        logging.error("Nu am găsit niciun formular pe pagină pentru a trimite cererea.")
        return None

    method = (form.get("method") or "get").lower()
    action = form.get("action") or URL

    # Construim payload cu toate input/select existente, păstrând valorile implicite
    payload: Dict[str, str] = {}

    # inputs
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        payload[name] = value

    # selects
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        # dacă este select pentru currency, căutăm opțiunea cu text exact
        if name == "currency":
            found = False
            for option in sel.find_all("option"):
                # comparăm textul (fără whitespace leading/trailing)
                if option.text.strip() == currency_name:
                    payload[name] = option.get("value", option.text.strip())
                    found = True
                    break
            if not found:
                # returnează lista de opțiuni disponibile pentru feedback
                available = [o.text.strip() for o in sel.find_all("option")]
                logging.error("Valuta '%s' nu a fost găsită în lista de opțiuni.", currency_name)
                logging.info("Opțiuni disponibile: %s", ", ".join(available))
                return None
        else:
            # păstrăm valoarea implicită
            # pentru alte select-uri, alegem prima opțiune sau valoarea curentă
            value = sel.get("value")
            if not value:
                first_opt = sel.find("option")
                if first_opt and first_opt.get("value"):
                    payload[name] = first_opt.get("value")
                elif first_opt:
                    payload[name] = first_opt.text.strip()

    # Setăm explicit dataStart conform cerinței
    # Căutăm câmpul numit dataStart
    if "dataStart" in payload:
        payload["dataStart"] = DATA_START
    else:
        # uneori este input fără valoare implicită; adăugăm oricum
        payload["dataStart"] = DATA_START

    return {"method": method, "action": action, "payload": payload}


def parse_table_to_records(soup: BeautifulSoup) -> List[Dict[str, str]]:
    table = soup.find("table", id="table-currencies")
    if table is None:
        logging.error("Tabelul cu id='table-currencies' nu a fost găsit în răspuns.")
        raise ValueError("table-currencies not found")

    headers = []
    thead = table.find("thead")
    if thead:
        for th in thead.find_all("th"):
            headers.append(th.text.strip())
    else:
        # fallback: prima linie
        first_row = table.find("tr")
        if first_row:
            for cell in first_row.find_all(["th", "td"]):
                headers.append(cell.text.strip())

    records: List[Dict[str, str]] = []
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if not cols:
            continue
        if headers and len(headers) == len(cols):
            record = {headers[i]: cols[i].text.strip() for i in range(len(cols))}
        else:
            # numerically index columns
            record = {str(i): cols[i].text.strip() for i in range(len(cols))}
        records.append(record)

    return records


def save_records_to_csv(records: List[Dict[str, str]], currency_name: str) -> Path:
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_currency = currency_name.replace(" ", "_")
    filename = data_dir / f"{safe_currency}_from_2020-02-22_{timestamp}.csv"

    df = pd.DataFrame(records)
    df.to_csv(filename, index=False)
    logging.info("Salvat CSV: %s", filename)
    return filename


def run(currency_name: str) -> int:
    logging.info("Start scraping pentru valuta: %s", currency_name)
    session = create_session_with_retries()

    try:
        logging.info("Cerere initiala GET la %s", URL)
        resp = session.get(URL, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logging.exception("Eroare la cererea initiala GET: %s", e)
        return 2

    soup = BeautifulSoup(resp.text, "lxml")
    form_info = find_form_and_prepare_payload(soup, currency_name)
    if form_info is None:
        logging.error("Nu pot continua fara payload valid.")
        return 3

    method = form_info["method"]
    action = form_info["action"]
    payload = form_info["payload"]

    try:
        logging.info("Trimitere cerere %s la %s cu dataStart=%s", method.upper(), action, DATA_START)
        if method == "post":
            resp2 = session.post(action, data=payload, timeout=TIMEOUT)
        else:
            resp2 = session.get(action, params=payload, timeout=TIMEOUT)
        resp2.raise_for_status()
    except Exception as e:
        logging.exception("Eroare la trimiterea formularului: %s", e)
        return 4

    soup2 = BeautifulSoup(resp2.text, "lxml")
    try:
        records = parse_table_to_records(soup2)
    except ValueError:
        logging.error("Nu s-au extras date din tabel.")
        return 5

    if not records:
        logging.warning("Tabelul a fost găsit, dar nu conține rânduri de date.")
        return 6

    try:
        save_records_to_csv(records, currency_name)
    except Exception:
        logging.exception("Eroare la salvarea CSV-ului.")
        return 7

    logging.info("Scraping finalizat cu succes pentru %s", currency_name)
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape exchange rates from cursbnr.ro for a given currency (exact name).")
    parser.add_argument("currency", help="Exact currency name as shown in <select name=\"currency\"> (e.g. 'Euro')")
    return parser.parse_args(argv)


def main() -> None:
    setup_logging()
    args = parse_args()
    exit_code = run(args.currency)
    if exit_code != 0:
        logging.error("Task terminat cu cod de eroare: %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
