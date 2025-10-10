#!/usr/bin/env python
"""Test script to check which Python environment is being used."""
import sys
import subprocess

print(f"Current Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

# Test if lambertlab is available
try:
    import lambertlab
    print(f"✓ lambertlab module found at: {lambertlab.__file__}")
except ImportError as e:
    print(f"✗ lambertlab module NOT found: {e}")

# Test if this would work in a subprocess (what run.py does)
print("\n--- Subprocess test (simulating run.py behavior) ---")
cmd = [sys.executable, '-c', 'import lambertlab; print("Subprocess: lambertlab OK")']
try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"Subprocess FAILED: {result.stderr.strip()}")
except Exception as e:
    print(f"Subprocess error: {e}")
