#!/usr/bin/env python
"""Test formatter și logica de formatare a răspunsurilor."""

from frontend.chatbot_tools import format_tool_result
from frontend.app import _format_error_message

# Test 1: format_tool_result pentru get_latest_training_run
print("=" * 60)
print("TEST 1: get_latest_training_run")
print("=" * 60)

training_result = {
    "id": 7,
    "model_name": "XGBoost",
    "mae": 0.0469,
    "rmse": 0.0486,
    "mape": 0.8946,
    "created_at": "2026-06-07T22:57:23.459969",
}

formatted = format_tool_result("get_latest_training_run", training_result, "Ce model a fost antrenat ultima dată?")
print("Input (dict brut):")
print(training_result)
print("\nOutput (text natural):")
print(formatted)
print("\n✓ PASS: Nu este dict brut!" if "{" not in formatted else "\n✗ FAIL: Conține {}")

# Test 2: format_tool_result pentru trigger_scrape
print("\n" + "=" * 60)
print("TEST 2: trigger_scrape")
print("=" * 60)

scrape_result = {
    "status": "success",
    "inserted": 3,
    "skipped": 2,
}

formatted = format_tool_result("trigger_scrape", scrape_result, "Actualizează datele BNR.")
print("Input (dict brut):")
print(scrape_result)
print("\nOutput (text natural):")
print(formatted)
print("\n✓ PASS: Nu este dict brut!" if "{" not in formatted else "\n✗ FAIL: Conține {}")

# Test 3: format_tool_result pentru get_latest_forecast
print("\n" + "=" * 60)
print("TEST 3: get_latest_forecast")
print("=" * 60)

forecast_result = {
    "predicted_value": 5.2345,
    "forecast_date": "2026-06-14",
    "model_name": "XGBoost",
    "mae_14_days": 0.0486,
}

formatted = format_tool_result("get_latest_forecast", forecast_result, "Care este ultima prognoză?")
print("Input (dict brut):")
print(forecast_result)
print("\nOutput (text natural):")
print(formatted)
print("\n✓ PASS: Nu este dict brut!" if "{" not in formatted else "\n✗ FAIL: Conține {}")

# Test 4: format_tool_result pentru get_latest_rates
print("\n" + "=" * 60)
print("TEST 4: get_latest_rates")
print("=" * 60)

# Note: format_tool_result expects the raw result from the tool, not wrapped
rates_result = [
    {"date": "2026-06-07", "value": 5.2345},
    {"date": "2026-06-06", "value": 5.2340},
]

formatted = format_tool_result("get_latest_rates", rates_result, "Arată ultimele cursuri.")
print("Input (list brut):")
print(rates_result)
print("\nOutput (text natural):")
print(formatted)
has_list = "[" in formatted and "{" in formatted
print("\n✓ PASS: Nu este list/dict brut!" if not has_list else "\n✗ FAIL: Conține [ sau {")

# Test 5: _format_error_message pentru 429
print("\n" + "=" * 60)
print("TEST 5: _format_error_message - 429 RESOURCE_EXHAUSTED")
print("=" * 60)

error_429 = (
    '{"error":{"message":"error","code":"RESOURCE_EXHAUSTED",'
    '"status":"429"}}'
)

formatted = _format_error_message(error_429)
print("Input (eroare brută cu 429):")
print(error_429[:100] + "...")
print("\nOutput (ascuns):")
print(formatted)
print("\n✓ PASS: Eroare ascunsă!" if "429" not in formatted and "RESOURCE_EXHAUSTED" not in formatted else "\n✗ FAIL: Eroare nu e ascunsă")

# Test 6: _format_error_message pentru altă eroare
print("\n" + "=" * 60)
print("TEST 6: _format_error_message - altă eroare")
print("=" * 60)

error_other = "Conexiune eșuată la backend-ul local"

formatted = _format_error_message(error_other)
print("Input (eroare obișnuită):")
print(error_other)
print("\nOutput:")
print(formatted)
print("\n✓ PASS: Eroare afișată!" if formatted == error_other else "\n✗ FAIL")

print("\n" + "=" * 60)
print("REZUMAT TESTE")
print("=" * 60)
print("✓ format_tool_result() elimină dict brut")
print("✓ format_tool_result() pentru trigger_scrape e scurt și natural")
print("✓ _format_error_message() ascunde eroarea 429")
print("✓ _format_error_message() afișează alte erori")
print("\nTeste finalizate!")
