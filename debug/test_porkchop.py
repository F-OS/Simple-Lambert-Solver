#!/usr/bin/env python3
"""
Direct test of porkchop plot generation
"""
import sys
print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")

# Test matplotlib backend
import matplotlib
print(f"Matplotlib backend before import: {matplotlib.get_backend()}")

from lambertlab.viz.porkchop import plot_porkchop
import numpy as np
from astropy.time import Time

print(f"Matplotlib backend after import: {matplotlib.get_backend()}")

# Create simple test data
dep_times = Time(['2036-10-01', '2036-10-02', '2036-10-03'])
tof_days = np.array([100, 150, 200])
c3_grid = np.random.rand(3, 3) * 10  # Random C3 values

print("Generating test porkchop plot...")
plot_porkchop(dep_times, tof_days, c3_grid, outname="test_porkchop.png")

import os
if os.path.exists("test_porkchop.png"):
    size = os.path.getsize("test_porkchop.png")
    print(f"✓ Plot created successfully: test_porkchop.png ({size} bytes)")
else:
    print("✗ Plot file not created!")
