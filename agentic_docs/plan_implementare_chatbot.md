# Plan Implementare Chatbot LLM cu Fallback Local

## Fișiere create/modificate

- `frontend/chatbot_tools.py` - tool-uri locale + TOOL_REGISTRY + tool calling formal + LLM reformulation
- `frontend/app.py` - integrare chatbot în Streamlit cu checkbox LLM, indicator GEMINI TOOLS
- `frontend/.env` - API key + model Gemini
- `agentic_docs/plan_implementare_chatbot.md` - planul și testarea (fișierul curent)

## Arhitectură Actuală - Tool Calling Formal cu Gemini

### Strategie Sigură (Local + Tool Selection + Reformulation)

1. **Tool-uri locale stocate în TOOL_REGISTRY** - dicționar central cu 4 tool-uri
2. **Gemini alege tool-ul** pe baza JSON-based tool routing formal
3. **Tool-ul local execută** prin `execute_tool_call(tool_name, args)`
4. **Gemini reformulează** răspunsul pentru claritate în limba română

### Fluxul cu Checkbox Bifat (LLM Activ) - Tool Calling

```
Utilizator: "Care este ultima prognoză?"
         ↓
Gemini (Tool Selection via JSON): {"tool_name": "get_latest_forecast", "args": {}}
         ↓
execute_tool_call("get_latest_forecast", {}) -> EUR/RON = 5.1964 din baza de date
         ↓
Gemini (Reformulation): "Reformulează răspunsul în limba română"
         ↓
Source == "gemini_tools" (tool calling reușit)
         ↓
UI indicator: 🟢 GEMINI TOOLS
```

### Fluxul cu Checkbox Nebifat (Local)

```
Utilizator: "Care este ultima prognoză?"
         ↓
Tool-uri locale: extrag și generează răspuns
         ↓
Source == "local" (nu se apelează LLM)
         ↓
UI indicator: ⚪ LOCAL
```

## LLM Integration (Gemini + Tool Calling)

### Configurație

```
Model: gemini-1.5-flash
SDK: google-genai
API: Google Gemini
Method: JSON-based tool routing
Max tokens: 500
Temperature: 0.2
```

### Tool Declarations (GEMINI_TOOL_DECLARATIONS)

Fiecare tool are o schemă formală cu descriere și parametri:

```python
{
    "name": "get_latest_forecast",
    "description": "Aduce ultima prognoză EUR/RON din baza de date...",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

### Straturile de apeluri (Cascade)

1. **answer_with_gemini_tools_or_local_fallback()** - Tool calling formal (JSON routing)
2. **answer_with_gemini_or_local_tools_with_source()** - Reformulare simplă (fallback)
3. **answer_with_local_tools()** - Pure local, fără LLM

## TOOL_REGISTRY și Tool Execution

### TOOL_REGISTRY

```python
TOOL_REGISTRY = {
    "get_latest_forecast": get_latest_forecast,
    "get_latest_rates": get_latest_rates,
    "get_latest_training_run": get_latest_training_run,
    "trigger_scrape": trigger_scrape,
}
```

### execute_tool_call(tool_name, args)

- Validează dacă tool_name există
- Pentru `get_latest_rates`, citește parametrul `limit` (default 7)
- Pentru alte tool-uri, le apelează fără parametri
- Returnează `{"status": "ok", "tool_name": ..., "result": ...}` sau error

## Tool-uri Locale Disponibile

- `get_latest_forecast()` → `GET /api/forecast/latest`
- `get_latest_rates(limit=7)` → `GET /api/rates?limit=7`
- `get_latest_training_run()` → `GET /api/runs?limit=1`
- `trigger_scrape()` → `POST /api/scrape`

## Gestionare Erori

| Caz | Source | Acțiune |
|-----|--------|---------|
| No API Key | `local` | Apelează doar tool-uri locale |
| Gemini Tool Calling OK | `gemini_tools` | Tool selection + execution + reformulation |
| Gemini Tool Calling Fail → Fallback Reformulation | `gemini` | Doar reformulare simplă |
| Ambele Gemini fail | `local_fallback` | Returnează răspuns local cu eroare |

## UI Indicators

```
LLM STATUS:
🔵 Gemini activ: da          → API Key Gemini detectată
⚪ Gemini activ: nu          → API Key lipsă

RESPONSE SOURCE:
🟢 Mod răspuns: GEMINI TOOLS → Tool calling formal (JSON routing + execution)
🟢 Mod răspuns: GEMINI       → Reformulat de Gemini (fallback din tool calling)
⚪ Mod răspuns: LOCAL         → Direct din tool-uri local (checkbox nebifat)
🟡 Mod răspuns: LOCAL FALLBACK → LLM eșuat, fallback local
```

## Testare

### Scenario 1: Tool Calling Reușit
```
Întrebare: "Care este ultima prognoză?"
Expected Source: gemini_tools
Tool ales: get_latest_forecast
UI: 🟢 GEMINI TOOLS
```

### Scenario 2: Tool Calling Fallback la Reformulare
```
Întrebare: "Care sunt ultimele cursuri?"
Gemini Tool Calling eșuează → fallback la reformulare
Expected Source: gemini
UI: 🟢 GEMINI
```

### Scenario 3: Checkbox Nebifat (Local)
```
Source: local
Răspuns: direct din tool-uri, fără LLM
UI: ⚪ LOCAL
```

### Scenario 4: LLM Indisponibil
```
No GEMINI_API_KEY
Expected Source: local
UI: ⚪ LOCAL
```

## Avantaje Tool Calling Formal

1. ✅ **Gemini decide alegerea tool-ului** - nu keyword matching local
2. ✅ **Parametri formali** - tool-uri acceptă parametri structurați
3. ✅ **Datele reale prioritare** - tool-urile extrag din baza de date
4. ✅ **Reformulare automată** - Gemini clarificare după tool execution
5. ✅ **Fallback robust** - cascade de metode
6. ✅ **Transparent** - utilizator vede care tool a fost ales (source = "gemini_tools")
7. ✅ **Examen cerință**: Tool-urile formale și `get_latest_forecast` pentru prognoze
