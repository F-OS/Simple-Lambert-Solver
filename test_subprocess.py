#!/usr/bin/env python3
"""
Test script to mimic run.py's subprocess execution
"""
import sys
import os
import subprocess

# Get the src directory
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))

# Create environment with PYTHONPATH
env = os.environ.copy()
pythonpath = env.get('PYTHONPATH', '')
env['PYTHONPATH'] = f"{src_path}{os.pathsep}{pythonpath}" if pythonpath else src_path
env['PYTHONDONTWRITEBYTECODE'] = '1'

python_exe = sys.executable

# Kernel list
kernels = [
    "data/kernels/naif0012.tls",
    "data/kernels/de440.bsp",
    "data/kernels/gm_de440.tpc",
    "data/kernels/20000001.bsp",
    "data/kernels/mar097.bsp",
    "data/kernels/pck00011.tpc"
]

# Build command
cmd = [python_exe, '-W', 'ignore', '-m', 'lambertlab.cli.main', 'em-grid']
for k in kernels:
    cmd.extend(["--kernels", k])
cmd.extend([
    "--dep-start", "2036-10-02",
    "--dep-end", "2036-10-12",  # Smaller range for testing
    "--dep-step", "10",
    "--tof-min", "100",
    "--tof-max", "200",  # Smaller range for testing
    "--tof-step", "50",
    "--dep-id", "399",
    "--arr-id", "499",
    "--save"
])

print(f"Running command: {' '.join(cmd)}")
print(f"Using Python: {python_exe}")
print(f"PYTHONPATH: {env['PYTHONPATH']}")
print(f"Current working directory: {os.getcwd()}")
print()

# Delete old plot if exists
if os.path.exists("artifacts/porkchop.png"):
    os.remove("artifacts/porkchop.png")
    print("Deleted old porkchop.png")

try:
    result = subprocess.run(cmd, env=env, cwd=os.getcwd())
    print(f"\nSubprocess exited with code: {result.returncode}")
    
    # Check if plot was created
    if os.path.exists("artifacts/porkchop.png"):
        size = os.path.getsize("artifacts/porkchop.png")
        print(f"✓ Porkchop plot created: {size} bytes")
    else:
        print("✗ Porkchop plot NOT created!")
        
except KeyboardInterrupt:
    print("\nInterrupted by user")
