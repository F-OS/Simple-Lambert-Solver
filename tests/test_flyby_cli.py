#!/usr/bin/env python3
"""
Test script for flyby computation via CLI
"""
import subprocess
import sys
import os

# Test the flyby command directly via CLI
cmd = [
    sys.executable, '-m', 'lambertlab.cli.main',
    'flyby',
    '--kernels', '../data/kernels/naif0012.tls',
    '--kernels', '../data/kernels/de440.bsp',
    '--kernels', '../data/kernels/gm_de440.tpc',
    '--kernels', '../data/kernels/20000001.bsp',
    '--kernels', '../data/kernels/mar097.bsp',
    '--kernels', '../data/kernels/pck00011.tpc',
    '--epoch', '2026-12-25',
    '--planet-id', '499',        # Mars flyby
    '--target-id', '20000001',   # Targeting Ceres
    '--r-body', '3396.2',
    '--alt-min', '300',
    '--vinf-in', '5.0', '0.0', '0.0',
    '--save'
]

print("Testing flyby CLI command...")
print("Command:", ' '.join(cmd))
env = os.environ.copy()
env['PYTHONPATH'] = '../src'
print()

env = os.environ.copy()
# Absolute src path relative to tests directory
tests_dir = os.path.dirname(__file__)
env['PYTHONPATH'] = os.path.abspath(os.path.join(tests_dir, '..', 'src'))

result = subprocess.run(cmd, capture_output=True, text=True, env=env)

print("Return code:", result.returncode)
print("\nSTDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

if result.returncode == 0:
    print("\n✓ Flyby computation successful!")
    print("Check artifacts/flyby.json for results")
else:
    print("\n✗ Flyby computation failed")
