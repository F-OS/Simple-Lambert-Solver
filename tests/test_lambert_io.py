# tests/test_lambert_io.py
import numpy as np
from astropy import units as u
from astropy.time import Time
import pytest
import sys
import os

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.spice_io import rv_helio
from lambertlab.core.lambert_io import solve_leg, c3

def test_lambert_basic_and_c3_identity(kernel_paths, times_sample):
    # Load kernels for this test
    from lambertlab.core.spice_io import load_kernels
    load_kernels(kernel_paths)
    
    t_dep, t_arr, _ = times_sample
    rE, vE = rv_helio("EARTH", t_dep)
    rM, vM = rv_helio("MARS",  t_arr)

    result = solve_leg(rE, rM, (t_arr - t_dep).to(u.day))
    assert result is not None, "Lambert solver failed to find solution"
    v_dep, v_arr = result
    # Identity: C3 = |vinf|^2 at departure
    vinf_dep = (v_dep - vE).to(u.km/u.s).value
    C3_val = c3(v_dep, vE)
    assert np.isfinite(C3_val)
    assert abs(C3_val - float(vinf_dep @ vinf_dep)) < 1e-6, "C3 identity failed."