#!/usr/bin/env python
"""Test script to verify source detection in chatbot responses."""
import os
import sys

os.chdir(r'c:\Users\Bisca\Desktop\facultate\SIIPA1\SEM2\AIE2\AIE_Tema3_CursValutar')
sys.path.insert(0, r'c:\Users\Bisca\Desktop\facultate\SIIPA1\SEM2\AIE2\AIE_Tema3_CursValutar')

from frontend.chatbot_tools import answer_with_llm_or_local_tools_with_source

print("=== TEST 1: Verificare funcție cu_source ===")

print("\n=== TEST 2: Testare funcție cu_source - întrebare prognoză ===")
result = answer_with_llm_or_local_tools_with_source("Care este ultima prognoză pentru EUR?")
print(f"Răspuns: {result.get('answer')[:100]}...")
print(f"Sursă: {result.get('source')}")

print("\n=== TEST 3: Testare funcție with_source - întrebare cursuri ===")
result = answer_with_llm_or_local_tools_with_source("Care sunt ultimele cursuri?")
print(f"Răspuns: {result.get('answer')[:100]}...")
print(f"Sursă: {result.get('source')}")

print("\n=== TEST 4: Testare formulare viitor ===")
result = answer_with_llm_or_local_tools_with_source("Cât va fi euro mâine?")
print(f"Răspuns: {result.get('answer')}")
print(f"Sursă: {result.get('source')}")
if "pentru perioada cerută" in result.get('answer', ''):
    print("✓ Formulare 'pentru perioada cerută' detectată (OK)")
else:
    print("✗ Formulare NU detectată")
