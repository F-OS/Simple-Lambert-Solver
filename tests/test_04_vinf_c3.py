# tests/test_04_vinf_c3.py
import numpy as np
from numpy.linalg import norm
from astropy import units as u
import sys
import os

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.spice_io import load_kernels, rv_helio
from lambertlab.core.lambert_io import solve_leg, c3

def test_c3_equals_vinf_squared(kernel_paths, dates):
    load_kernels(kernel_paths)
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS",  dates["em_arr"])
    tof = (dates["em_arr"] - dates["em_dep"])
    v_dep, v_arr = solve_leg(rE, rM, tof)

    vinf_earth = (v_dep - vE).to(u.km/u.s).value
    c3_val = c3(v_dep, vE)
    assert abs(c3_val - norm(vinf_earth)**2) < 1e-6