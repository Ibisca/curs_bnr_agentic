# Configurare LLM și Gemini - Ghid Rapid

## Status Actual

✅ **Implementare completă cu tool calling formal**
✅ **Gemini are acces la TOOL_REGISTRY formal cu 4 tool-uri**
✅ **JSON-based tool routing implementat**
✅ **Model default: gemini-1.5-flash**

## Fișier de Configurare

Locație: `frontend/.env`

Conținut minim necesar pentru Gemini:
```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
```

## Strategia Sigură (Local + Tool Selection + Reformulation)

1. **Tool-uri locale stocate în TOOL_REGISTRY formal** - 4 tool-uri disponibile
2. **Gemini alege tool-ul** pe baza JSON-based tool routing
3. **Tool-ul execută** și aduce date reale din baza de date
4. **Gemini reformulează** pentru claritate în limba română

## Cum Funcționează

### Detectare Disponibilitate
- **LLM disponibil**: dacă `GEMINI_API_KEY` este setat în `.env`
- **Fallback**: cascade de metode dacă Gemini eșuează

### Fluxul Tool Calling

1. **Tool Selection** -> Gemini primește JSON request, alege tool
2. **Tool Execution** -> `execute_tool_call(tool_name, args)` din TOOL_REGISTRY
3. **Result Reformulation** -> Gemini reformulează pentru limba română

### Sursele Răspunsurilor

1. **"gemini_tools"**: Tool calling formal reușit (JSON routing + execution + reformulation)
2. **"gemini"**: Reformulare simplă Gemini (fallback din tool calling)
3. **"local"**: Răspunsul a venit de la tool-urile locale (checkbox nebifat sau LLM indisponibil)
4. **"local_fallback"**: Gemini a eșuat, se returnează răspunsul local

### UI Indicators

```
LLM STATUS:
🔵 Gemini activ: da          → API Key Gemini detectată
⚪ Gemini activ: nu          → API Key lipsă

RESPONSE SOURCE:
🟢 Mod răspuns: GEMINI TOOLS → Tool calling formal (JSON routing + execution)
🟢 Mod răspuns: GEMINI       → Reformulat de Google Gemini (fallback)
⚪ Mod răspuns: LOCAL         → Direct din tool-uri local
🟡 Mod răspuns: LOCAL FALLBACK → Gemini eșuat, fallback local
```

## Tool-uri Disponibile (TOOL_REGISTRY)

1. **get_latest_forecast** - Ultima prognoză EUR/RON
2. **get_latest_rates** - Ultimele cursuri EUR (limit opțional)
3. **get_latest_training_run** - Ultima antrenare a modelului
4. **trigger_scrape** - Actualizează datele BNR

## Instalare Dependențe

```bash
pip install python-dotenv google-genai requests
```

## Testare

### Scenario 1: Tool Calling Reușit
```
Întrebare: "Care este ultima prognoză?"
Gem ini alege: get_latest_forecast
Expected Source: gemini_tools
✅ Tool calling formal reușit
```

### Scenario 2: Checkbox Bifat (LLM Activ)
```
✅ Source: gemini_tools (dacă tool calling OK) sau gemini (fallback) sau local_fallback (dacă eșuat)
✅ Răspuns: reformulat de Gemini pe baza datelor locale
```

### Scenario 3: Checkbox Nebifat (Local)
```
✅ Source: local
✅ Răspuns: direct din tool-urile locale
```

## Troubleshooting

| Problem | Soluție |
|---------|---------|
| Error - JSON parsing | Gemini nu a returnat JSON valid, fallback la reformulare simplă |
| Error 400 - invalid_request_error | Verifică modelul în `.env`: `gemini-1.5-flash` |
| Error - timeout | LLM răspunde lent, fallback automat local |
| UI arată "GEMINI TOOLS" | Tool calling formal a reușit ✅ |
| UI arată "GEMINI" | Tool calling eșuat, fallback la reformulare |
| UI arată "LOCAL FALLBACK" | Ambele metode Gemini au eșuat, fallback local |
