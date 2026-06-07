#!/usr/bin/env python
"""Test script for formal tool calling implementation."""
import os
import sys

os.chdir(r'c:\Users\Bisca\Desktop\facultate\SIIPA1\SEM2\AIE2\AIE_Tema3_CursValutar')
sys.path.insert(0, r'c:\Users\Bisca\Desktop\facultate\SIIPA1\SEM2\AIE2\AIE_Tema3_CursValutar')

from frontend.chatbot_tools import (
    TOOL_REGISTRY,
    GEMINI_TOOL_DECLARATIONS,
    execute_tool_call,
    answer_with_gemini_tools_or_local_fallback,
)

print("=" * 80)
print("TEST 1: Verify TOOL_REGISTRY")
print("=" * 80)
print(f"✓ TOOL_REGISTRY keys: {list(TOOL_REGISTRY.keys())}")
print(f"✓ Count: {len(TOOL_REGISTRY)}")

print("\n" + "=" * 80)
print("TEST 2: Verify GEMINI_TOOL_DECLARATIONS")
print("=" * 80)
print(f"✓ Tool declarations count: {len(GEMINI_TOOL_DECLARATIONS)}")
for decl in GEMINI_TOOL_DECLARATIONS:
    print(f"  - {decl['name']}: {decl['description'][:60]}...")

print("\n" + "=" * 80)
print("TEST 3: execute_tool_call - Unknown tool")
print("=" * 80)
result = execute_tool_call("unknown_tool", {})
print(f"Status: {result.get('status')} (expected: error)")
print(f"Message: {result.get('message')}")

print("\n" + "=" * 80)
print("TEST 4: execute_tool_call - get_latest_forecast")
print("=" * 80)
result = execute_tool_call("get_latest_forecast", {})
print(f"Status: {result.get('status')}")
if result.get('status') == 'ok':
    print(f"Tool: {result.get('tool_name')}")
    res_data = result.get('result', {})
    print(f"Result type: {type(res_data)}")
    if isinstance(res_data, dict):
        print(f"Forecast data keys: {list(res_data.keys())[:3]}...")

print("\n" + "=" * 80)
print("TEST 5: execute_tool_call - get_latest_rates (default limit=7)")
print("=" * 80)
result = execute_tool_call("get_latest_rates", {})
print(f"Status: {result.get('status')}")
if result.get('status') == 'ok':
    res_data = result.get('result', [])
    print(f"Result type: {type(res_data)}")
    print(f"Items count: {len(res_data) if isinstance(res_data, list) else 'N/A'}")

print("\n" + "=" * 80)
print("TEST 6: execute_tool_call - get_latest_rates (limit=3)")
print("=" * 80)
result = execute_tool_call("get_latest_rates", {"limit": 3})
print(f"Status: {result.get('status')}")
if result.get('status') == 'ok':
    res_data = result.get('result', [])
    print(f"Items count: {len(res_data) if isinstance(res_data, list) else 'N/A'}")

print("\n" + "=" * 80)
print("TEST 7: answer_with_gemini_tools_or_local_fallback - No API Key (fallback local)")
print("=" * 80)
result = answer_with_gemini_tools_or_local_fallback("Care este ultima prognoză?")
print(f"Source: {result.get('source')} (expected: local)")
print(f"Answer preview: {result.get('answer')[:80]}...")

print("\n" + "=" * 80)
print("✅ All manual tests completed!")
print("=" * 80)
