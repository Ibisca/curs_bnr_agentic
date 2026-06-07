"""Tool-uri locale pentru chatbotul de curs valutar."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
except ImportError:
    genai = None

API_BASE_URL = "http://localhost:7772"


def get_latest_forecast() -> Dict[str, Any]:
    """Returnează ultima prognoză din baza de date prin API-ul backend."""
    url = f"{API_BASE_URL}/api/forecast/latest"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        return {"error": f"Eroare la preluarea prognozei: {error}"}


def get_latest_rates(limit: int = 7) -> List[Dict[str, Any]]:
    """Returnează ultimele cursuri EUR/RON din backend."""
    url = f"{API_BASE_URL}/api/rates?limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        return [{"error": f"Eroare la preluarea cursurilor: {error}"}]


def get_latest_training_run() -> Dict[str, Any]:
    """Returnează ultima rulare de antrenare din backend."""
    url = f"{API_BASE_URL}/api/runs?limit=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        runs = response.json()
        if isinstance(runs, list) and runs:
            return runs[0]
        return {"error": "Nu s-a găsit nicio rulare de antrenare."}
    except requests.RequestException as error:
        return {"error": f"Eroare la preluarea ultimei rulări: {error}"}


def trigger_scrape() -> Dict[str, Any]:
    """Pornește actualizarea datelor BNR prin endpointul de scraping."""
    url = f"{API_BASE_URL}/api/scrape"
    try:
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        return {"error": f"Eroare la actualizarea datelor: {error}"}


# ============================================================================
# TOOL REGISTRY - Registry formal pentru tool-uri disponibile
# ============================================================================

TOOL_REGISTRY = {
    "get_latest_forecast": get_latest_forecast,
    "get_latest_rates": get_latest_rates,
    "get_latest_training_run": get_latest_training_run,
    "trigger_scrape": trigger_scrape,
}

# ============================================================================
# GEMINI TOOL DECLARATIONS - Scheme formale pentru Gemini tool calling
# ============================================================================

GEMINI_TOOL_DECLARATIONS = [
    {
        "name": "get_latest_forecast",
        "description": (
            "Aduce ultima prognoză EUR/RON din baza de date prin endpoint-ul /api/forecast/latest. "
            "Folosește acest tool atunci când utilizatorul cere prognoză, estimare pentru EUR, "
            "sau previziuni pentru curs valutar."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_latest_rates",
        "description": (
            "Aduce ultimele cursuri EUR/RON din baza de date prin endpoint-ul /api/rates. "
            "Folosește acest tool când utilizatorul cere cursuri recente, valori actuale EUR "
            "sau istoric de cursuri."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Numărul de cursuri de returnat. Default 7.",
                    "default": 7,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_latest_training_run",
        "description": (
            "Aduce ultima rulare de antrenare și metricile modelului (MAE, RMSE, MAPE) "
            "prin endpoint-ul /api/runs?limit=1. Folosește când utilizatorul cere informații "
            "despre model, performanță sau última antrenare."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "trigger_scrape",
        "description": (
            "Actualizează datele BNR apelând endpoint-ul /api/scrape. "
            "Folosește când utilizatorul cere o actualizare a datelor, refresh sau scraping."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ============================================================================
# FORMATTER - Formatează rezultatele tool-urilor în text natural
# ============================================================================

def format_tool_result(tool_name: str, tool_result: Dict[str, Any], user_message: str) -> str:
    """
    Formatează rezultatul tool-ului în text natural, în limba română.
    
    Args:
        tool_name: Numele tool-ului (get_latest_forecast, get_latest_rates, etc.)
        tool_result: Dicționarul brut returnat de tool (sau lista pentru rates)
        user_message: Mesajul utilizatorului (pentru context)
    
    Returns:
        Text natural formatat în limba română, fără dict brut
    """
    # Handle list results (e.g., get_latest_rates)
    if isinstance(tool_result, list):
        # D) get_latest_rates - handle list
        if tool_name == "get_latest_rates":
            if not tool_result:
                return "Nu s-au găsit cursuri disponibile."
            
            lines = ["Ultimele cursuri EUR/RON:"]
            for rate in tool_result:
                if isinstance(rate, dict) and not rate.get("error"):
                    date = rate.get("date", "Data necunoscută")
                    value = rate.get("value", 0.0)
                    lines.append(f"{date}: {value:.4f}")
            
            return "\n".join(lines)
        
        # Fallback for other list-based tools
        return str(tool_result)
    
    # Handle dict results
    if not isinstance(tool_result, dict):
        return str(tool_result)
    
    # Gestionează erori
    if tool_result.get("error"):
        return tool_result.get("error")
    
    # A) get_latest_training_run
    if tool_name == "get_latest_training_run":
        model_name = tool_result.get("model_name", "Necunoscut")
        created_at = tool_result.get("created_at", "Data necunoscută")
        mae = tool_result.get("mae", 0.0)
        rmse = tool_result.get("rmse", 0.0)
        mape = tool_result.get("mape", 0.0)
        
        # Formatare: "Ultimul model antrenat este XGBoost, rulat la 2026-06-07T22:57:23.459969. Metricile obținute sunt: MAE=0.0469, RMSE=0.0486, MAPE=0.8946."
        return (
            f"Ultimul model antrenat este {model_name}, rulat la {created_at}. "
            f"Metricile obținute sunt: MAE={mae:.4f}, RMSE={rmse:.4f}, MAPE={mape:.4f}."
        )
    
    # B) trigger_scrape
    if tool_name == "trigger_scrape":
        inserted = tool_result.get("inserted", 0)
        skipped = tool_result.get("skipped", 0)
        status = tool_result.get("status", "necunoscut")
        
        # Formatare: "Actualizare date finalizată. S-au inserat X cursuri noi și s-au sărit Y duplicate."
        return (
            f"Actualizare date finalizată. S-au inserat {inserted} cursuri noi și s-au sărit {skipped} duplicate."
        )
    
    # C) get_latest_forecast
    if tool_name == "get_latest_forecast":
        predicted_value = tool_result.get("predicted_value", 0.0)
        forecast_date = tool_result.get("forecast_date", "Data necunoscută")
        model_name = tool_result.get("model_name", "Modelul")
        mae_14_days = tool_result.get("mae_14_days", 0.0)
        
        return (
            f"Ultima prognoză pentru EUR/RON este {predicted_value:.4f} "
            f"pentru data {forecast_date}, folosind modelul {model_name}. "
            f"MAE pentru 14 zile: {mae_14_days:.4f}."
        )
    
    # Fallback
    return str(tool_result)


def execute_tool_call(tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execută un tool local pe baza numelui și argumentelor primite de la Gemini.
    
    Args:
        tool_name: Numele tool-ului din TOOL_REGISTRY
        args: Dicționar cu argumentele tool-ului
    
    Returns:
        Rezultatul tool-ului sau {"status": "error", "message": "..."}
    """
    if args is None:
        args = {}
    
    if tool_name not in TOOL_REGISTRY:
        return {
            "status": "error",
            "message": f"Tool necunoscut: {tool_name}. Disponibile: {list(TOOL_REGISTRY.keys())}",
        }
    
    tool_func = TOOL_REGISTRY[tool_name]
    
    try:
        # Special handling pentru get_latest_rates care acceptă parametru limit
        if tool_name == "get_latest_rates":
            limit = args.get("limit", 7)
            if not isinstance(limit, int):
                limit = 7
            result = tool_func(limit=limit)
        else:
            # Celelalte tool-uri nu au parametri
            result = tool_func()
        
        return {
            "status": "ok",
            "tool_name": tool_name,
            "result": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "message": f"Eroare la execuția tool-ului: {str(e)[:200]}",
        }


def _normalize_text(text: str) -> str:
    """Normalizează textul pentru compararea intențiilor."""
    mapping = {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ş": "s",
        "ț": "t",
        "ţ": "t",
    }
    normalized = text.lower().strip()
    for original, replacement in mapping.items():
        normalized = normalized.replace(original, replacement)
    return normalized


def answer_with_local_tools(user_message: str) -> str:
    """Răspunde la întrebări folosind tool-urile locale definite în acest modul."""
    if not user_message or not user_message.strip():
        return "Te rog scrie o întrebare despre prognoză, cursuri, modelul de antrenare sau actualizare date."

    text = _normalize_text(user_message)

    future_indicators = [
        "prognoza",
        "forecast",
        "previziune",
        "estimare",
        "estimat",
        "cat va fi",
        "va fi",
        "peste",
        "maine",
        "urmatoarea",
        "viitor",
    ]
    historic_rates_keywords = [
        "ultimele cursuri",
        "istoric",
        "cursuri recente",
        "arata cursurile",
        "ultimele valori eur",
        "curs",
        "rate",
        "eur",
    ]
    training_keywords = ["antrenare", "model", "metrici", "mae", "rmse", "mape"]
    scrape_keywords = ["actualizeaza", "scrape", "scraping", "preia date"]

    if any(keyword in text for keyword in future_indicators):
        forecast = get_latest_forecast()
        if forecast.get("error"):
            return forecast["error"]
        note = ""
        if any(keyword in text for keyword in ["cat va fi", "va fi", "peste", "maine", "urmatoarea", "viitor"]):
            note = (
                "Modelul salvat oferă ultima prognoză disponibilă în baza de date, "
                "nu o prognoză multi-step exactă pentru perioada cerută. "
            )
        return (
            f"{note}Ultima prognoză pentru EUR/RON este {forecast.get('predicted_value'):.4f} "
            f"pentru data {forecast.get('forecast_date')} folosind modelul {forecast.get('model_name')}."
        )

    if any(keyword in text for keyword in scrape_keywords):
        result = trigger_scrape()
        if result.get("error"):
            return result["error"]
        inserted = result.get("inserted")
        skipped = result.get("skipped")
        status = result.get("status")
        return (
            f"Actualizare date: status={status}. "
            f"S-au inserat {inserted} cursuri și s-au sărit {skipped} duplicate."
        )

    if any(keyword in text for keyword in training_keywords):
        run = get_latest_training_run()
        if run.get("error"):
            return run["error"]
        return (
            f"Ultima rulare a fost modelul {run.get('model_name')} la {run.get('created_at')}. "
            f"MAE={run.get('mae'):.4f}, RMSE={run.get('rmse'):.4f}, MAPE={run.get('mape'):.4f}."
        )

    if any(keyword in text for keyword in historic_rates_keywords):
        rates = get_latest_rates(limit=7)
        if isinstance(rates, list) and rates and isinstance(rates[0], dict) and rates[0].get("error"):
            return rates[0]["error"]
        if not rates:
            return "Nu s-au găsit cursuri disponibile."
        lines = ["Ultimele cursuri EUR/RON:"]
        for rate in rates:
            lines.append(f"{rate.get('date')}: {rate.get('value')}")
        return "\n".join(lines)

    return (
        "Pot ajuta cu prognoza, ultimele cursuri EUR, ultima antrenare a modelului sau cu actualizarea datelor BNR. "
        "Te rog reformulează întrebarea."
    )


def _load_environment() -> None:
    if load_dotenv is not None:
        env_file = Path(__file__).resolve().parent / ".env"
        if env_file.exists():
            load_dotenv(dotenv_path=str(env_file))
        else:
            load_dotenv()


def _get_gemini_api_key() -> Optional[str]:
    _load_environment()
    return os.getenv("GEMINI_API_KEY")


def _get_gemini_model() -> str:
    _load_environment()
    return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _gemini_generate_content(api_key: str, model: str, contents: str) -> tuple[str | None, str, Exception | None]:
    client = genai.Client(api_key=api_key)
    fallback_models = [model, "gemini-flash-latest", "models/gemini-flash-latest"]
    last_error = None
    for candidate in fallback_models:
        try:
            response = client.models.generate_content(model=candidate, contents=contents)
            response_text = getattr(response, "text", None)
            if response_text:
                return response_text, candidate, None
        except Exception as error:
            last_error = error
            message = str(error).lower()
            if "404" in message or "not found" in message or "not supported" in message:
                continue
            return None, candidate, error
    return None, model, last_error


def test_gemini_connection() -> Dict[str, str]:
    """
    Testează conexiunea la Google Gemini cu un request minim.
    Returnează status, model și eventual erori.
    """
    api_key = _get_gemini_api_key()
    model = _get_gemini_model()
    
    if not api_key:
        return {
            "status": "error",
            "model": model,
            "message": "No API key found",
            "error_type": "missing_api_key",
            "error_message": "GEMINI_API_KEY not set in .env",
        }
    
    if genai is None:
        return {
            "status": "error",
            "model": model,
            "message": "Google Gemini SDK not installed",
            "error_type": "missing_module",
            "error_message": "google-genai package not imported",
        }
    
    try:
        response_text, used_model, error = _gemini_generate_content(
            api_key=api_key,
            model=model,
            contents="Răspunde doar cu: conexiune ok",
        )
        if response_text:
            return {
                "status": "ok",
                "model": used_model,
                "message": response_text,
            }
        if error is not None:
            raise error
        return {
            "status": "error",
            "model": used_model,
            "error_type": "empty_response",
            "error_message": "Gemini returned empty response",
        }
    except Exception as e:
        error_str = str(e)
        return {
            "status": "error",
            "model": model,
            "message": "Connection failed",
            "error_type": type(e).__name__,
            "error_message": error_str[:200],
        }


def answer_with_gemini_tools_or_local_fallback(user_message: str) -> Dict[str, str]:
    """
    Folosește Gemini cu tool declarations formale și JSON-based tool routing.
    
    Strategie:
    1. Dacă nu există GEMINI_API_KEY, returnează fallback local
    2. Dacă există cheia, trimite toward Gemini o instrucțiune care cere JSON cu tool routing
    3. Gemini alege tool-ul și returnează JSON {"tool_name": "...", "args": {...}}
    4. Parșează JSON-ul și execută tool-ul prin execute_tool_call()
    5. Reformulează răspunsul tool-ului prin Gemini pentru claritate română
    
    Return:
        {"answer": "...", "source": "gemini_tools" | "gemini" | "local_fallback" | "local", ...}
    """
    if not user_message or not user_message.strip():
        return {
            "answer": "Te rog scrie o întrebare despre prognoză, cursuri, modelul de antrenare sau actualizare date.",
            "source": "local",
        }
    
    api_key = _get_gemini_api_key()
    if not api_key or genai is None:
        return {
            "answer": answer_with_local_tools(user_message),
            "source": "local",
        }
    
    # Step 1: Request Gemini to choose tool and provide parameters
    import json
    
    tool_selection_prompt = (
        "Ești un asistent care alege tool-uri potrivite pentru cereri utilizatorilor.\n\n"
        "Disponibile tool-uri:\n"
        "- 'get_latest_forecast': Pentru cereri despre prognoză EUR/RON, estimări, valori viitoare\n"
        "- 'get_latest_rates': Pentru cereri despre cursuri actuale EUR/RON, valori recente\n"
        "- 'get_latest_training_run': Pentru cereri despre model, metrici (MAE, RMSE, MAPE), antrenare\n"
        "- 'trigger_scrape': Pentru cereri de actualizare date BNR, refresh\n\n"
        "Cererea utilizatorului:\n"
        f"{user_message}\n\n"
        "Răspunde STRICT cu JSON (fără text suplimentar):\n"
        '{"tool_name": "...", "args": {...}}\n\n'
        "De exemplu:\n"
        '{"tool_name": "get_latest_forecast", "args": {}}\n'
        'sau\n'
        '{"tool_name": "get_latest_rates", "args": {"limit": 7}}'
    )
    
    try:
        response_text, used_model, error = _gemini_generate_content(
            api_key=api_key,
            model=_get_gemini_model(),
            contents=tool_selection_prompt,
        )
        
        if not response_text:
            if error:
                raise error
            raise Exception("Gemini nu a returnat răspuns")
        
        # Step 2: Parse JSON tool selection from Gemini
        json_str = response_text.strip()
        # Încearcă să extragi JSON dintr-un text mai lung (cazul în care Gemini adaugă text)
        import re
        json_match = re.search(r'\{[^{}]*?"tool_name"[^{}]*?\}', json_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        
        tool_selection = json.loads(json_str)
        tool_name = tool_selection.get("tool_name", "").strip()
        tool_args = tool_selection.get("args", {})
        
        if not tool_name:
            raise Exception("Gemini nu a selectat un tool valid")
        
        # Step 3: Execute the selected tool
        tool_result = execute_tool_call(tool_name, tool_args)
        
        if tool_result.get("status") == "error":
            return {
                "answer": answer_with_local_tools(user_message),
                "source": "local_fallback",
                "error": tool_result.get("message"),
            }
        
        # Step 4: Get tool data
        tool_data = tool_result.get("result", {})
        
        # Special handling pentru trigger_scrape: returnează direct formatat, fără reformulare Gemini
        if tool_name == "trigger_scrape":
            formatted_answer = format_tool_result(tool_name, tool_data, user_message)
            return {
                "answer": formatted_answer,
                "source": "gemini_tools",
                "tool_used": tool_name,
            }
        
        # For other tools: reformulate using Gemini for clarity
        reformulation_prompt = (
            f"Cererea utilizatorului:\n{user_message}\n\n"
            f"Rezultatul tool-ului '{tool_name}':\n{json.dumps(tool_data, ensure_ascii=False, indent=2)}\n\n"
            "Reformulează răspunsul în limba română clar, concis și natural. "
            "Nu inventa date. Folosește doar informația din rezultat."
        )
        
        reformat_text, _, reformat_error = _gemini_generate_content(
            api_key=api_key,
            model=_get_gemini_model(),
            contents=reformulation_prompt,
        )
        
        if reformat_text:
            return {
                "answer": reformat_text.strip(),
                "source": "gemini_tools",
                "tool_used": tool_name,
            }
        else:
            # Fallback: format tool result locally - nu returna dict brut!
            formatted_answer = format_tool_result(tool_name, tool_data, user_message)
            return {
                "answer": formatted_answer,
                "source": "gemini_tools",
                "tool_used": tool_name,
                "error": "Reformulare Gemini eșuată, format local utilizat",
            }
    
    except json.JSONDecodeError as e:
        return {
            "answer": answer_with_local_tools(user_message),
            "source": "local_fallback",
            "error": f"Gemini nu a returnat JSON valid: {str(e)[:100]}",
        }
    except Exception as e:
        return {
            "answer": answer_with_local_tools(user_message),
            "source": "local_fallback",
            "error": f"Eroare la tool calling: {str(e)[:100]}",
        }


def answer_with_gemini_or_local_tools_with_source(user_message: str) -> Dict[str, str]:
    """
    Folosește tool-urile locale pentru date reale, apoi Gemini pentru reformulare.
    
    Strategie sigură:
    1. Rulează întâi tool-urile locale pentru răspunsul real
    2. Trimite la Gemini pentru reformulare în limba română
    3. Dacă Gemini eșuează, returnează răspunsul local
    """
    if not user_message or not user_message.strip():
        return {
            "answer": "Te rog scrie o întrebare despre prognoză, cursuri, modelul de antrenare sau actualizare date.",
            "source": "local",
        }

    local_answer = answer_with_local_tools(user_message)

    api_key = _get_gemini_api_key()
    if not api_key or genai is None:
        return {
            "answer": local_answer,
            "source": "local",
        }

    prompt = (
        f"Întrebarea utilizatorului:\n{user_message}\n\n"
        f"Răspunsul generat de tool-urile locale:\n{local_answer}\n\n"
        "Reformulează răspunsul în română, clar și natural. Nu inventa valori noi."
    )

    try:
        response_text, used_model, error = _gemini_generate_content(
            api_key=api_key,
            model=_get_gemini_model(),
            contents=prompt,
        )
        if response_text:
            return {
                "answer": response_text.strip(),
                "source": "gemini",
            }
        if error is not None:
            raise error
    except Exception as e:
        return {
            "answer": local_answer,
            "source": "local_fallback",
            "error": str(e),
        }

    return {
        "answer": local_answer,
        "source": "local_fallback",
        "error": "Gemini nu a returnat un răspuns valid.",
    }


def answer_with_llm_or_local_tools_with_source(user_message: str) -> Dict[str, str]:
    """
    Returnează răspunsul chatbotului și sursa folosită.
    
    Strategie cu prioritate:
    1. Încearcă answer_with_gemini_tools_or_local_fallback() cu tool routing formal
    2. Dacă eșuează și nu reușești gemini_tools, cazi înapoi la reformulare simplă (answer_with_gemini_or_local_tools_with_source)
    3. Dacă nu există GEMINI_API_KEY, local

    Return format:
    {
        "answer": "...",
        "source": "gemini_tools" | "gemini" | "local" | "local_fallback",
        "error": "msg_if_exists"
    }
    """
    if not user_message or not user_message.strip():
        return {
            "answer": "Te rog scrie o întrebare despre prognoză, cursuri, modelul de antrenare sau actualizare date.",
            "source": "local",
        }

    gemini_api_key = _get_gemini_api_key()
    
    # Dacă nu există cheia, returnează local
    if not gemini_api_key or genai is None:
        return {
            "answer": answer_with_local_tools(user_message),
            "source": "local",
        }
    
    # Încearcă mai întâi tool calling formal cu Gemini
    tools_result = answer_with_gemini_tools_or_local_fallback(user_message)
    if tools_result.get("source") == "gemini_tools":
        # Reușit cu tool calling formal
        return tools_result
    
    # Dacă tool calling eșuează, cazi înapoi la reformulare simplă
    if tools_result.get("source") in ["local_fallback", "local"]:
        # Încearcă reformularea simplă Gemini
        reformat_result = answer_with_gemini_or_local_tools_with_source(user_message)
        return reformat_result
    
    # Fallback final
    return {
        "answer": answer_with_local_tools(user_message),
        "source": "local_fallback",
        "error": "Ambele metode Gemini au eșuat",
    }



def answer_with_llm_or_local_tools(user_message: str) -> str:
    """
    Încearcă un răspuns LLM și cade înapoi pe tool-urile locale dacă LLM nu este disponibil.
    Returnează doar răspunsul pentru compatibilitate (nu și sursa).
    """
    result = answer_with_llm_or_local_tools_with_source(user_message)
    return result.get("answer", "Eroare la generarea răspunsului.")

