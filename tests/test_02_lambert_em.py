# tests/test_02_lambert_em.py
import numpy as np
from astropy import units as u
import sys
import os

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.spice_io import load_kernels, rv_helio
from lambertlab.core.lambert_io import solve_leg, c3
from numpy.linalg import norm

def test_em_lambert_valley(kernel_paths, dates):
    load_kernels(kernel_paths)
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS",  dates["em_arr"])
    tof = (dates["em_arr"] - dates["em_dep"])

def test_em_lambert_valley(kernel_paths, dates):
    load_kernels(kernel_paths)
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS",  dates["em_arr"])
    tof = (dates["em_arr"] - dates["em_dep"])

    v_dep, v_arr = solve_leg(rE, rM, tof)
    # Check that we got a valid solution
    assert v_dep is not None and v_arr is not None, "No Lambert solution found"

    # C3 should be positive and reasonable (not extremely high)
    c3_val = c3(v_dep, vE)
    assert c3_val > 0, f"C3 should be positive: {c3_val}"
    assert c3_val < 1000, f"C3 seems unreasonably high: {c3_val}"  # Allow up to 1000 km²/s²

    # Sanity: arrival relative speed vs Mars should be reasonable
    vinf_in = (v_arr - vM).to(u.km/u.s).value
    vinf_magnitude = norm(vinf_in)
    assert vinf_magnitude > 0, f"Arrival v_inf should be positive: {vinf_magnitude}"
    assert vinf_magnitude < 50, f"Arrival v_inf seems unreasonably high: {vinf_magnitude}"  # Allow up to 50 km/s