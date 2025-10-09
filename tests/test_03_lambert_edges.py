# tests/test_03_lambert_edges.py
import pytest
import sys
import os
import warnings

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.lambert_io import solve_leg

def test_negative_tof_rejected(dates):
    from astropy import units as u
    with pytest.raises(ValueError, match="Time of flight must be positive"):
        solve_leg(1*u.km, 2*u.km, -1*u.day)  # your function should validate Quantity/sign

def test_no_solution_handling(kernel_paths, dates):
    from astropy import units as u
    from astropy.time import TimeDelta
    # Use identical positions - should be impossible for Lambert solver
    r1 = [1.0, 0.0, 0.0] * u.au
    r2 = [1.0, 0.0, 0.0] * u.au  # Same as r1
    tof = TimeDelta(1*u.day)
    # For identical positions, solve_leg should raise
    # Suppress expected warnings from poliastro for this edge case
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(ValueError, match="Lambert solve failed"):
            solve_leg(r1, r2, tof)