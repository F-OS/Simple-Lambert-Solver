#!/usr/bin/env python3
"""
Test script for chain3 (three-body chain) computation.
Tests Earth → Mars (flyby) → Ceres trajectory search.
"""

import sys
import subprocess
import os

# Test the chain3 command
cmd = [
    sys.executable, '-m', 'lambertlab.cli.main',
    'chain3',
    '--kernels', '../data/kernels/naif0012.tls',
    '--kernels', '../data/kernels/de440.bsp',
    '--kernels', '../data/kernels/gm_de440.tpc',
    '--kernels', '../data/kernels/20000001.bsp',
    '--kernels', '../data/kernels/mar097.bsp',
    '--kernels', '../data/kernels/pck00011.tpc',
    '--dep-body', '399',           # Earth
    '--flyby-body', '499',         # Mars
    '--arr-body', '20000001',      # Ceres
    '--dep-window', '2035-04-01:2035-04-15',  # Short window for testing
    '--dep-step', '7',             # Every 7 days
    '--leg1-tof', '200:250:25',    # 200-250 days, step 25
    '--leg2-tof', '300:400:50',    # 300-400 days, step 50
    '--rp-bounds', '3696.2:13396.2',  # Mars: 300 km to 10000 km altitude
    '--bplane-theta=-20:20:3',        # Use = to avoid negative number parsing issue
    '--max-solutions', '50',
    '--save',
    '--format', 'table'
]

print("=" * 70)
print("Testing Three-Body Chain (chain3)")
print("=" * 70)
print()
print("Scenario: Earth → Mars (flyby) → Ceres")
print("  Departure: Earth (399)")
print("  Flyby: Mars (499)")
print("  Arrival: Ceres (20000001)")
print("  Window: 2035-04-01 to 2035-04-15")
print("  Leg 1 TOF: 200-250 days")
print("  Leg 2 TOF: 300-400 days")
print()
print("Command:")
print(" ".join(cmd))
print()
print("-" * 70)

env = os.environ.copy()
# Make PYTHONPATH absolute relative to this test file so it works from any CWD
tests_dir = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(tests_dir, '..', 'src'))
env['PYTHONPATH'] = src_path

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
    print("✓ Chain3 computation successful!")
    print("\nCheck artifacts/ directory for:")
    print("  - chain3_leg1_grid.csv")
    print("  - chain3_bplane_grid.csv")
    print("  - chain3_leg2_grid.csv")
    print("  - chain3_solutions.csv")
    print("  - chain3_meta.json")
else:
    print("✗ Chain3 computation failed")
    sys.exit(1)
