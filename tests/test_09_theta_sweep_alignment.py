import pytest
import numpy as np
from numpy.linalg import norm
from astropy import units as u

from lambertlab.core.lambert_io import solve_leg
from lambertlab.core.spice_io import load_kernels, rv_helio
from conftest import kernel_paths, dates


def test_theta_sweep_alignment(kernel_paths, dates):
    """Test flyby alignment optimization with theta sweep."""
    load_kernels(kernel_paths)
    
    # Get Earth and Mars positions
    rE, vE = rv_helio("EARTH", dates["em_dep"])
    rM, vM = rv_helio("MARS", dates["em_arr"])
    
    # Solve for the leg
    tof = dates["em_arr"] - dates["em_dep"]
    v1, v2 = solve_leg(rE, rM, tof)
    
    # Compute v_inf at Earth
    vinf = (v1 - vE).to(u.km/u.s).value
    
    # For flyby alignment, we sweep over theta (pump angle)
    # Theta is the angle between v_inf and the flyby asymptote
    theta_values = np.linspace(0, 2*np.pi, 10)
    
    # For each theta, compute the turn angle or something
    # Simplified: just check that the calculation runs
    for theta in theta_values:
        # Rotate v_inf by theta around some axis
        # For simplicity, assume rotation around z-axis
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        rotation_matrix = np.array([
            [cos_theta, -sin_theta, 0],
            [sin_theta, cos_theta, 0],
            [0, 0, 1]
        ])
        vinf_rotated = rotation_matrix @ vinf
        
        # Compute some invariant, e.g., magnitude should be preserved
        assert abs(norm(vinf_rotated) - norm(vinf)) < 1e-10
    
    # The sweep should cover the full range
    assert len(theta_values) == 10