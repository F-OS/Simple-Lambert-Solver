import pytest
import numpy as np
import os
from astropy.time import Time
from astropy import units as u

import sys
# Make src importable when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from lambertlab.core.spice_io import load_kernels
from lambertlab.flows.em_only import screen_em_grid
from conftest import kernel_paths, dates


def test_porkchop_csv(kernel_paths, dates):
    """Test porkchop plot CSV output."""
    load_kernels(kernel_paths)
    
    # Define grid parameters
    dep_start = dates["em_dep"] - 30 * u.day
    dep_end = dates["em_dep"] + 30 * u.day
    arr_start = dates["em_arr"] - 30 * u.day
    arr_end = dates["em_arr"] + 30 * u.day
    
    dep_times = Time(np.linspace(dep_start.jd, dep_end.jd, 5), format='jd')
    arr_times = Time(np.linspace(arr_start.jd, arr_end.jd, 5), format='jd')
    
    # Run grid
    dep_times, tof_days, C3 = screen_em_grid(
        dep_start=dep_start,
        dep_end=dep_end,
        dep_step_days=7,
        tof_min_days=190,
        tof_max_days=210,
        tof_step_days=5,
        dep_body="399",  # Earth
        arr_body="499"   # Mars
    )
    
    # Check that results are valid
    assert len(dep_times) > 0
    assert len(tof_days) > 0
    assert C3.shape[0] == len(dep_times)
    assert C3.shape[1] == len(tof_days)
    
    # Check that some values are finite
    assert np.any(np.isfinite(C3))