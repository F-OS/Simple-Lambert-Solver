#!/usr/bin/env python3
"""
Test script to demonstrate the flyby interactive flow.
This simulates what happens when a user selects option 2 in run.py
"""

import sys
import subprocess
import os

# Simulate what get_flyby_params() would build as a command
# Based on: Mars flyby at 2026-12-25, targeting Ceres, vinf_in = [5, 0, 0]

kernels = [
    "../data/kernels/naif0012.tls",
    "../data/kernels/de440.bsp",
    "../data/kernels/gm_de440.tpc",
    "../data/kernels/mar097.bsp",
    "../data/kernels/20000001.bsp",
    "../data/kernels/pck00011.tpc"
]

cmd = [sys.executable, "-m", "lambertlab.cli.main", "flyby"]

# Add kernels
for k in kernels:
    cmd.extend(["--kernels", k])

# Add flyby parameters
cmd.extend([
    "--epoch", "2026-12-25",
    "--planet-id", "499",        # Mars
    "--target-id", "20000001",   # Ceres
    "--r-body", "3396.2",        # Mars radius
    "--alt-min", "300.0",        # 300 km altitude
    "--vinf-in", "5.0", "0.0", "0.0"
])

print("=" * 70)
print("Testing Interactive Flyby Flow")
print("=" * 70)
print()
print("Scenario: Mars flyby on 2026-12-25, targeting Ceres")
print("  Flyby body: Mars (499)")
print("  Target body: Ceres (20000001)")
print("  Incoming v-infinity: [5.0, 0.0, 0.0] km/s")
print("  Minimum altitude: 300 km")
print()
print("Command:")
print(" ".join(cmd))
print()
print("-" * 70)

env = os.environ.copy()
# Absolute src path relative to tests directory
tests_dir = os.path.dirname(__file__)
env['PYTHONPATH'] = os.path.abspath(os.path.join(tests_dir, '..', 'src'))

result = subprocess.run(cmd, capture_output=True, text=True, env=env)

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

print()
print("-" * 70)
print(f"Exit code: {result.returncode}")

if result.returncode == 0:
    print("✓ Flyby computation successful!")
else:
    print("✗ Flyby computation failed")
    sys.exit(1)
