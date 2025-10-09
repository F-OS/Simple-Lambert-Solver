#!/usr/bin/env python
"""
Test script to check poliastro upgrade compatibility.

Run this BEFORE and AFTER upgrading poliastro to compare results.
"""

import sys
import traceback

print("=" * 70)
print("POLIASTRO COMPATIBILITY TEST")
print("=" * 70)

# Test 1: Import poliastro
print("\n[TEST 1] Importing poliastro...")
try:
    import poliastro
    print(f"✅ poliastro version: {poliastro.__version__}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Lambert solver
print("\n[TEST 2] Testing Lambert solver...")
try:
    from poliastro.iod.izzo import lambert
    from poliastro.bodies import Sun
    import numpy as np
    import astropy.units as u
    
    # Simple Earth-Mars transfer
    r1 = np.array([1.0, 0.0, 0.0]) * u.AU
    r2 = np.array([0.0, 1.5, 0.0]) * u.AU
    tof = 200 * u.day
    
    v1, v2 = lambert(Sun.k, r1, r2, tof)
    print(f"✅ Lambert solver works")
    print(f"   v1 magnitude: {np.linalg.norm(v1.value):.4f} km/s")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    traceback.print_exc()

# Test 3: Orbit class  
print("\n[TEST 3] Testing Orbit class...")
try:
    from poliastro.twobody import Orbit
    print(f"✅ Orbit class imports successfully")
except Exception as e:
    print(f"❌ FAILED: {e}")
    traceback.print_exc()

# Test 4: Kepler propagation
print("\n[TEST 4] Testing Kepler propagation...")
try:
    from poliastro.twobody.propagation import kepler
    
    r0 = np.array([1.0e8, 0.0, 0.0])  # km
    v0 = np.array([0.0, 30.0, 0.0])   # km/s
    dt = 3600.0  # 1 hour in seconds
    k = 1.327e11  # Sun's GM in km^3/s^2
    
    r1, v1 = kepler(r0, v0, dt, k)
    print(f"✅ Kepler propagation works")
    print(f"   Position after 1 hour: {np.linalg.norm(r1):.2e} km")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    traceback.print_exc()

# Test 5: Check for new flyby module
print("\n[TEST 5] Checking for poliastro.core.flybys...")
try:
    from poliastro.core.flybys import compute_flyby
    print(f"✅ poliastro.core.flybys.compute_flyby is AVAILABLE!")
    
    import inspect
    sig = inspect.signature(compute_flyby)
    print(f"   Signature: {sig}")
    
    # Try a simple flyby calculation
    print("\n   Testing compute_flyby function...")
    # These are placeholder values - need to check actual signature
    # v_spacecraft, v_body, k, r_p, theta
    
except ImportError:
    print(f"ℹ️  poliastro.core.flybys not available (expected in v0.7.0)")
    print(f"   This module was added in later versions")
except Exception as e:
    print(f"⚠️  Module exists but error occurred: {e}")
    traceback.print_exc()

# Test 6: Check dependencies
print("\n[TEST 6] Checking key dependencies...")
try:
    import numpy
    import scipy
    import astropy
    
    print(f"✅ numpy version: {numpy.__version__}")
    print(f"✅ scipy version: {scipy.__version__}")
    print(f"✅ astropy version: {astropy.__version__}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    traceback.print_exc()

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"poliastro version: {poliastro.__version__}")
print("\nIf all core tests (1-4) pass, the upgrade is likely safe.")
print("Test 5 will only pass in poliastro >= 0.8.0 (approximately)")
print("\nNext steps:")
print("  1. Save this output")
print("  2. Run: pip install --upgrade poliastro")
print("  3. Run this script again")  
print("  4. Compare results")
print("=" * 70)
