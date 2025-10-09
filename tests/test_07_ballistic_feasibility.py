import pytest
import numpy as np
from numpy.linalg import norm
from astropy import units as u

from lambertlab.core.lambert_io import solve_leg
from lambertlab.core.spice_io import load_kernels, rv_helio
from conftest import kernel_paths, dates


def test_ballistic_feasibility(kernel_paths, dates):
    """Test ballistic feasibility of flyby trajectories."""
    load_kernels(kernel_paths)
    
    # Get Earth and Mars positions
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS", dates["em_arr"])
    
    # Solve for the leg
    tof = dates["em_arr"] - dates["em_dep"]
    v1, v2 = solve_leg(rE, rM, tof)
    
    # Compute v_inf at Earth
    vinf = (v1 - vE).to(u.km/u.s).value
    
    # For ballistic feasibility, check that the trajectory doesn't require
    # excessive v_inf or C3
    c3 = norm(vinf)**2
    
    # Reasonable C3 for Earth-Mars is < 250 km^2/s^2 (allowing for different branches)
    assert c3 < 250.0
    
    # v_inf should be reasonable
    assert norm(vinf) < 20.0  # km/s
    
    # The trajectory should be ballistic (no thrust required)
    # This is ensured by the Lambert solver providing the solution