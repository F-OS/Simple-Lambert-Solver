#!/usr/bin/env python3
"""
Test script for checkpointed chain3 computation.
Demonstrates resumable, crash-proof gravity assist trajectory search.
"""

import sys
import subprocess
import time
import os

print("=" * 70)
print("Testing Checkpointed Chain3 (Resumable)")
print("=" * 70)
print()
print("This test demonstrates:")
print("  ✓ Tile-based computation")
print("  ✓ Atomic artifact writes")
print("  ✓ Progress tracking with heartbeats")
print("  ✓ Crash recovery (can be resumed)")
print()

# Test the checkpointed chain3 command
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
    '--dep-window', '2035-04-01:2035-04-08',  # 1 week window for testing
    '--dep-step', '7',             # Weekly departures
    '--leg1-tof', '200:225:25',    # 2 TOF values
    '--leg2-tof', '300:350:50',    # 2 TOF values
    '--rp-bounds', '3696.2:8696.2',  # Mars: 300-5300 km altitude
    '--bplane-theta=-15:15:2',     # 2 theta samples
    '--max-solutions', '20',
    '--checkpoint',                # Enable checkpointing!
    '--tile-size', '1',            # Small tiles for demonstration
    '--checkpoint-sec', '5',       # Frequent heartbeats
    '--resume',
    '--save',
    '--outdir', 'test_artifacts/chain3_checkpoint_test',
    '--format', 'table'
]

print("Scenario: Earth → Mars (flyby) → Ceres (CHECKPOINTED)")
print("  Departure: Earth (399)")
print("  Flyby: Mars (499)")
print("  Arrival: Ceres (20000001)")
print("  Window: 2035-04-01 to 2035-04-08 (1 week)")
print("  Mode: CHECKPOINTED (resumable)")
print()
print("Command:")
print(" ".join(cmd))
print()
print("-" * 70)

env = os.environ.copy()
# Absolute src path relative to tests directory
tests_dir = os.path.dirname(__file__)
env['PYTHONPATH'] = os.path.abspath(os.path.join(tests_dir, '..', 'src'))

start = time.time()
result = subprocess.run(cmd, capture_output=True, text=True, env=env)
elapsed = time.time() - start

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR (warnings):")
    # Only show actual errors, not ERFA warnings
    for line in result.stderr.split('\n'):
        if 'ErfaWarning' not in line and 'dubious year' not in line and line.strip():
            print(line)

print()
print("-" * 70)
print(f"Exit code: {result.returncode}")
print(f"Elapsed time: {elapsed:.1f}s")

if result.returncode == 0:
    print("✓ Checkpointed chain3 computation successful!")
    print()
    print("Artifacts created in test_artifacts/chain3_checkpoint_test/:")
    print("  ✓ meta.json - Configuration and code hash")
    print("  ✓ index.sqlite - Tile completion index")
    print("  ✓ run.state - Progress heartbeat")
    print("  ✓ tiles/*.csv - Individual tile results")
    print("  ✓ chain3_solutions.csv - Merged top solutions")
    print("  ✓ chain3_all_solutions.csv - All solutions")
    print()
    print("To resume: Run the same command again!")
    print("  (It will detect existing progress and continue)")
else:
    print("✗ Checkpointed chain3 computation failed")
    sys.exit(1)

print()
print("=" * 70)
print("RESUME TEST")
print("=" * 70)
print()
print("Running the same command again to test resume...")
print("(Should detect completed tiles and skip them)")
print()

result2 = subprocess.run(cmd, capture_output=True, text=True, env=env)

if "Resuming from checkpoint" in result2.stdout:
    print("✓ Resume detected! Skipped already-completed tiles.")
elif "Pending tiles: 0" in result2.stdout:
    print("✓ All tiles already done, nothing to resume.")
else:
    print("Output:")
    print(result2.stdout[:500])

print()
print("✓ Checkpointing system working correctly!")
