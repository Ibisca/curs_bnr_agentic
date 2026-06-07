# Conceptul tool-urilor locale pentru chatbot

Acest document descrie tool-urile locale create pentru chatbotul de curs valutar și integrarea lor cu Gemini prin tool calling formal.

## TOOL_REGISTRY - Registry formal pentru tool-uri

Toate tool-urile disponibile sunt gestionate printr-un registry central în `frontend/chatbot_tools.py`:

```python
TOOL_REGISTRY = {
    "get_latest_forecast": get_latest_forecast,
    "get_latest_rates": get_latest_rates,
    "get_latest_training_run": get_latest_training_run,
    "trigger_scrape": trigger_scrape,
}
```

## Tool-uri implementate

### 1. get_latest_forecast
- **Descripție**: Aduce ultima prognoză EUR/RON din baza de date prin endpoint-ul `/api/forecast/latest`.
- **Parametri**: fără parametri
- **Caz de utilizare**: "Care este ultima prognoză?", "Cât va fi euro mâine?", "Ce estimare avem pentru EUR/RON?"
- **Tool principal de examen**: da, deoarece aduce ultima prognoză din `forecasts` table.

### 2. get_latest_rates
- **Descripție**: Aduce ultimele cursuri EUR/RON din baza de date prin endpoint-ul `/api/rates`.
- **Parametri**: `limit` (integer, opțional, default 7)
- **Caz de utilizare**: "Care sunt ultimele cursuri EUR?", "Arata mi cursurile", "Cum a evoluat euro?"

### 3. get_latest_training_run
- **Descripție**: Aduce ultima rulare de antrenare și metricile modelului (MAE, RMSE, MAPE) prin endpoint-ul `/api/runs?limit=1`.
- **Parametri**: fără parametri
- **Caz de utilizare**: "Ce model a fost antrenat ultima dată?", "Care sunt metricile?", "Cum e performanța?"

### 4. trigger_scrape
- **Descripție**: Actualizează datele BNR apelând endpoint-ul `/api/scrape`.
- **Parametri**: fără parametri
- **Caz de utilizare**: "Actualizează datele BNR", "Refresh date", "Preia noi cursuri"

## Tool Calling Formal cu Gemini - JSON-based Tool Routing

### Fluxul de execuție

1. **User Message** -> Utilizatorul cere ceva
2. **Tool Selection (JSON)** -> Gemini primește prompt care cere JSON cu tool routing și răspunde cu:
   ```json
   {
     "tool_name": "get_latest_forecast",
     "args": {}
   }
   ```
3. **Tool Execution** -> `execute_tool_call(tool_name, args)` execută tool-ul local din registry
4. **Tool Result Reformulation** -> Gemini primește rezultatul și reformulează în limba română pentru claritate
5. **Response to User** -> Utilizatorul primește răspunsul reformulat cu `source = "gemini_tools"`

### GEMINI_TOOL_DECLARATIONS

Fiecare tool are o declarație formală cu descriere și parametri:

```python
GEMINI_TOOL_DECLARATIONS = [
    {
        "name": "get_latest_forecast",
        "description": "Aduce ultima prognoză EUR/RON...",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    # ... etc
]
```

### execute_tool_call(tool_name, args)

Funcția care execută tool-uri selectate de Gemini:
- Validează dacă tool_name există în TOOL_REGISTRY
- Pentru `get_latest_rates`, citește parametrul `limit` (default 7)
- Pentru alte tool-uri, le apelează fără parametri
- Returnează `{"status": "ok", "tool_name": ..., "result": ...}` sau error

### Avantaje tool calling formal

- ✅ Gemini decide alegerea tool-ului, nu keyword matching local
- ✅ Parametri formali pentru tool-uri
- ✅ Răspunsuri reformulate automat de Gemini
- ✅ Fallback local sigur dacă Gemini eșuează
- ✅ Transparent: source = "gemini_tools" arată că tool-ul a fost ales formal

## Decizia chatbotului (legacy fallback)

Dacă `answer_with_gemini_tools_or_local_fallback()` eșuează, funcția `answer_with_local_tools(user_message)` decide care tool să folosească pe baza keyword matching local:
- prognoză -> `get_latest_forecast`
- cursuri -> `get_latest_rates`
- model/metrici -> `get_latest_training_run`
- actualizare -> `trigger_scrape`

## Gemini și reformulare LLM

Gemini este folosit în 2 moduri:

1. **Tool Selection**: Alege care tool local să se apeleze pe baza cererii utilizatorului
2. **Result Reformulation**: Reformulează rezultatul tool-ului în limba română clar și natural

Tool-urile locale aduc datele reale din API-ul FastAPI, iar Gemini primește acest context pentru reformulare fără să inventeze date noi.
