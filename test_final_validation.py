#!/usr/bin/env python
"""Final validation of local fallback behavior."""
import sys
sys.path.insert(0, '.')

from frontend.chatbot_tools import answer_with_local_tools, answer_with_llm_or_local_tools_with_source

# Test checkbox OFF (local mode)
print("=== TEST LOCAL (checkbox OFF) ===")
result = answer_with_local_tools("Care este ultima prognoză pentru EUR mâine?")
print(f"Răspuns: {result}\n")

# Test with_source function
print("=== TEST answer_with_llm_or_local_tools_with_source ===")
result_dict = answer_with_llm_or_local_tools_with_source("Care este ultima prognoză pentru EUR mâine?")
print(f"Source: {result_dict.get('source')}")
print(f"Answer snippet: {result_dict.get('answer')[:150]}...")
