# tests/test_05_mc_requirement.py
from astropy import units as u
import sys
import os

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.spice_io import load_kernels, rv_helio
from lambertlab.core.lambert_io import solve_leg
from numpy.linalg import norm

def test_mc_leg_vinf_req_is_reasonable(kernel_paths, dates):
    load_kernels(kernel_paths)
    rM, vM = rv_helio("MARS",  dates["em_arr"])
    # Use a date that has Ceres coverage (around 2025-2030)
    from astropy.time import Time
    ceres_date = dates["mc_arr"]
    rC, vC = rv_helio(20000001, ceres_date)
    tof2 = (ceres_date - dates["em_arr"])
    v_out_req, _ = solve_leg(rM, rC, tof2)
    vinf_req = (v_out_req - vM).to(u.km/u.s).value
    assert 0.5 <= norm(vinf_req) <= 11.0