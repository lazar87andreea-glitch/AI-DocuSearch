#!/usr/bin/env python
"""Test LangSmith tracing without Streamlit"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("LangSmith Configuration Check")
print("=" * 60)
print(f"LANGSMITH_API_KEY: {'SET ✓' if os.environ.get('LANGSMITH_API_KEY') else 'NOT SET ✗'}")
print(f"LANGSMITH_TRACING: {os.environ.get('LANGSMITH_TRACING', 'NOT SET')}")
print(f"LANGSMITH_PROJECT: {os.environ.get('LANGSMITH_PROJECT', 'NOT SET')}")
print()

# Test traceable decorator
try:
    from langsmith import traceable
    
    @traceable(run_type="chain", name="test_trace")
    def test_function():
        print("  -> Executing test function...")
        return {"status": "success", "message": "LangSmith trace recorded"}
    
    print("Calling traced function...")
    result = test_function()
    print(f"Result: {result}")
    print()
    print("✓ LangSmith tracing is WORKING!")
    print()
    print("Check LangSmith dashboard at: https://smith.langchain.com")
    print(f"Project: {os.environ.get('LANGSMITH_PROJECT', 'default')}")
    print()
    
except Exception as e:
    print(f"✗ ERROR: {e}")
    sys.exit(1)
