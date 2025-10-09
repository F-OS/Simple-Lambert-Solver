"""Test C3 invariant: C3 must equal ||vinf||^2"""

import pytest
import numpy as np
from astropy.time import Time
from astropy import units as u
import os

from lambertlab.flows.em_only import screen_em_grid_cached
from lambertlab.core.spice_io import load_kernels

# Build absolute kernel file paths relative to the repository root
tests_dir = os.path.dirname(__file__)
kern_dir = os.path.abspath(os.path.join(tests_dir, '..', 'data', 'kernels'))
KERNELS = [
    os.path.join(kern_dir, 'naif0012.tls'),
    os.path.join(kern_dir, 'de440.bsp'),
    os.path.join(kern_dir, 'gm_de440.tpc'),
    os.path.join(kern_dir, '20000001.bsp'),
    os.path.join(kern_dir, 'mar097.bsp'),
    os.path.join(kern_dir, 'pck00011.tpc')
]


def test_c3_matches_vinf_square():
    """
    Guard test: C3 must equal ||v_inf||^2.
    This ensures we never accidentally log heliocentric velocity as v_inf.
    """
    # Load kernels
    load_kernels(KERNELS)
    
    # Pick a known good departure window
    dep_start = Time("2027-01-01", scale="tdb")
    dep_end = Time("2027-01-03", scale="tdb")
    
    # Run a small grid
    dep_times, tof_days, c3, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, vM_x, vM_y, vM_z, rM_x, rM_y, rM_z = \
        screen_em_grid_cached(dep_start, dep_end, 1, 200, 300, 20, "399", "499", n_workers=1)
    
    # Check every finite result
    for i in range(len(dep_times)):
        for j in range(len(tof_days)):
            c3_val = c3[i, j]
            if not np.isfinite(c3_val):
                continue
            
            # Reconstruct v_inf from components
            vinf_out = np.array([vout_x[i, j], vout_y[i, j], vout_z[i, j]])
            vinf_in = np.array([vin_x[i, j], vin_y[i, j], vin_z[i, j]])
            
            # All components must be finite
            assert np.all(np.isfinite(vinf_out)), f"v_inf_out has non-finite components at ({i},{j})"
            assert np.all(np.isfinite(vinf_in)), f"v_inf_in has non-finite components at ({i},{j})"
            
            # C3 must match ||v_inf_out||^2
            vinf_out_mag = np.linalg.norm(vinf_out)
            c3_from_vinf = vinf_out_mag ** 2
            
            assert np.isclose(c3_val, c3_from_vinf, rtol=1e-6, atol=1e-9), \
                f"C3 mismatch at ({i},{j}): C3={c3_val:.6f}, ||vinf||^2={c3_from_vinf:.6f}, diff={abs(c3_val - c3_from_vinf):.9f}"
            
            # Sanity check: v_inf should be reasonable (0.5 - 15 km/s for interplanetary)
            assert 0.5 <= vinf_out_mag <= 15.0, \
                f"v_inf_out magnitude {vinf_out_mag:.2f} km/s is outside reasonable range at ({i},{j})"
            
            vinf_in_mag = np.linalg.norm(vinf_in)
            assert 0.5 <= vinf_in_mag <= 15.0, \
                f"v_inf_in magnitude {vinf_in_mag:.2f} km/s is outside reasonable range at ({i},{j})"
            
            # C3 should be in reasonable range (0.25 - 225 km²/s²)
            assert 0.25 <= c3_val <= 225.0, \
                f"C3={c3_val:.2f} km²/s² is outside reasonable range at ({i},{j})"


def test_c3_not_heliocentric_velocity():
    """
    Regression test: ensure we're not accidentally storing heliocentric
    transfer velocity as v_inf. Heliocentric velocities are typically
    15-40 km/s, while v_inf should be 2-10 km/s for good windows.
    """
    # Load kernels
    load_kernels(KERNELS)
    
    # Pick a known good departure window (near minimum C3)
    dep_start = Time("2027-01-01", scale="tdb")
    dep_end = Time("2027-01-01", scale="tdb")
    
    # Run a single point near the minimum
    dep_times, tof_days, c3, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, vM_x, vM_y, vM_z, rM_x, rM_y, rM_z = \
        screen_em_grid_cached(dep_start, dep_end, 1, 280, 280, 1, "399", "499", n_workers=1)
    
    # Get the result
    i, j = 0, 0
    c3_val = c3[i, j]
    vinf_out = np.array([vout_x[i, j], vout_y[i, j], vout_z[i, j]])
    
    # This should be near the minimum C3 (around 42-44 km²/s²)
    assert np.isfinite(c3_val)
    assert 40.0 <= c3_val <= 50.0, f"Expected C3 near 42-44 km²/s², got {c3_val:.2f}"
    
    # v_inf magnitude should be around 6-7 km/s, NOT 13-18 km/s (heliocentric)
    vinf_mag = np.linalg.norm(vinf_out)
    assert 5.0 <= vinf_mag <= 8.0, \
        f"Expected v_inf ~6-7 km/s, got {vinf_mag:.2f} km/s (might be heliocentric velocity!)"
    
    # If this were heliocentric velocity, C3 would be ~169-324 km²/s²
    # Our actual C3 should be much lower
    helio_c3_lower_bound = 13.0 ** 2  # 169 km²/s²
    assert c3_val < helio_c3_lower_bound, \
        f"C3={c3_val:.2f} is suspiciously high (> {helio_c3_lower_bound}), might be using heliocentric velocity!"


if __name__ == "__main__":
    test_c3_matches_vinf_square()
    test_c3_not_heliocentric_velocity()
    print("✅ All C3 invariant tests passed!")
