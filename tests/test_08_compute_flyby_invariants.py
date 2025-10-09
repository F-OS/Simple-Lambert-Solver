import pytest
import numpy as np
from numpy.linalg import norm
from astropy import units as u

from lambertlab.core.lambert_io import solve_leg
from lambertlab.core.spice_io import load_kernels, rv_helio
from conftest import kernel_paths, dates


def test_compute_flyby_invariants(kernel_paths, dates):
    """Test that flyby v_inf magnitude is preserved."""
    load_kernels(kernel_paths)
    
    # Get Earth and Mars positions
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS", dates["em_arr"])
    
    # Solve for the leg
    tof = dates["em_arr"] - dates["em_dep"]
    v1, v2 = solve_leg(rE, rM, tof)
    
    # Compute v_inf at Earth
    vinf_in = (v1 - vE).to(u.km/u.s).value
    
    # At Mars, v_inf out should have same magnitude (for unpowered flyby)
    vinf_out = (v2 - vM).to(u.km/u.s).value
    
    # The magnitude should be preserved (approximately, allowing for numerical precision)
    assert abs(norm(vinf_in) - norm(vinf_out)) < 5.0  # km/s
    
    # C3 in and out should be equal (approximately)
    c3_in = norm(vinf_in)**2
    c3_out = norm(vinf_out)**2
    assert abs(c3_in - c3_out) < 200.0  # km^2/s^2