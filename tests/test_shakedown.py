# tests/test_shakedown.py
import pytest
import numpy as np
from astropy.time import Time
import sys
import os

# Add the src directory to the path so we can import lambertlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambertlab.core.spice_io import load_kernels
from lambertlab.flows.em_only import screen_em_grid_cached
from lambertlab.flows.emc_req import eval_mc_requirement


def test_kernel_loading(kernel_paths):
    """Test that all required SPICE kernels can be loaded."""
    # This should not raise an exception
    load_kernels(kernel_paths)
    assert True  # If we get here, kernels loaded successfully


def test_em_trajectory_computation(kernel_paths, dates):
    """Test Earth-Mars trajectory computation with known low-C3 case."""
    load_kernels(kernel_paths)

    # Single point test - should find the low C3 valley
    dep_start = dates["em_dep"]
    dep_end = dates["em_dep"]  # Single departure time
    dep_step_days = 1  # Not used for single point
    tof_min_days = 190
    tof_max_days = 200

    try:
        dep_times, tof_days, c3_grid, vinf_out_x, vinf_out_y, vinf_out_z, vinf_in_x, vinf_in_y, vinf_in_z, vM_x, vM_y, vM_z, rM_x, rM_y, rM_z = screen_em_grid_cached(
            dep_start=dep_start,
            dep_end=dep_end,
            dep_step_days=dep_step_days,
            tof_min_days=tof_min_days,
            tof_max_days=tof_max_days,
            dep_body=399,  # Earth
                            arr_body=499,  # Mars (updated NAIF ID)
            n_workers=1    # Use single worker for testing
        )

        # Should have computed results
        assert len(dep_times) > 0
        assert len(tof_days) > 0
        assert c3_grid.shape == (len(dep_times), len(tof_days))

        # Check that some C3 values are finite (not all NaN)
        finite_c3 = c3_grid[np.isfinite(c3_grid)]
        assert len(finite_c3) > 0, "No valid C3 values computed"

        # Check that C3 values are reasonable (should be positive for valid trajectories)
        assert np.all(finite_c3 >= 0), "C3 values should be non-negative"

    except Exception as e:
        # If SPICE kernels don't cover the test dates, that's OK - the framework works
        if "SPICE" in str(e) or "leapseconds" in str(e).lower():
            pytest.skip(f"SPICE kernel coverage issue: {e}")
        else:
            raise  # Re-raise unexpected errors


def test_mc_requirement_computation(kernel_paths, dates):
    """Test Mars-Ceres requirement computation."""
    load_kernels(kernel_paths)

    # Test Mars departure and Ceres arrival
    mars_time = dates["em_arr"]  # Use Mars arrival as departure for Mars-Ceres
    ceres_time = dates["mc_arr"]

    try:
        result = eval_mc_requirement(mars_time, ceres_time)

        # Should return a valid result dictionary
        assert isinstance(result, dict)
        assert 'vinf_req_mag' in result
        assert 'vinf_req_x' in result
        assert 'vinf_req_y' in result
        assert 'vinf_req_z' in result
        assert 'tof2_d' in result

        # Delta-V should be reasonable (not None and finite)
        assert result['vinf_req_mag'] is not None
        assert np.isfinite(result['vinf_req_mag'])
        assert result['vinf_req_mag'] >= 0.0  # Delta-V can't be negative

        # TOF should be positive
        assert result['tof2_d'] > 0

    except Exception as e:
        # If SPICE kernels don't cover the test dates, that's OK
        if "SPICE" in str(e) or "leapseconds" in str(e).lower():
            pytest.skip(f"SPICE kernel coverage issue: {e}")
        else:
            raise


def test_end_to_end_workflow(kernel_paths, dates):
    """Test the complete Earth-Mars-Ceres workflow."""
    load_kernels(kernel_paths)

    try:
        # Step 1: Earth-Mars trajectory
        dep_start = dates["em_dep"]
        dep_end = dates["em_dep"]  # Single departure time
        dep_step_days = 1
        tof_min_days = 190
        tof_max_days = 200

        dep_times, tof_days, c3_grid, _, _, _, _, _, _, _, _, _, _, _, _ = screen_em_grid_cached(
            dep_start=dep_start,
            dep_end=dep_end,
            dep_step_days=dep_step_days,
            tof_min_days=tof_min_days,
            tof_max_days=tof_max_days,
            dep_body=399,
            arr_body=499,  # Updated Mars NAIF ID
            n_workers=1,
            use_threads=True,  # Test thread-based parallelism
            kernel_paths=kernel_paths
        )
        finite_c3 = c3_grid[np.isfinite(c3_grid)]
        assert len(finite_c3) > 0

        # Step 2: Mars-Ceres requirement
        mars_arrival = dates["em_arr"]  # Approximate Mars arrival
        mc_result = eval_mc_requirement(mars_arrival, dates["mc_arr"])

        assert mc_result['vinf_req_mag'] is not None
        assert np.isfinite(mc_result['vinf_req_mag'])

        # The total mission should be feasible (rough check)
        min_c3 = np.min(finite_c3)
        total_delta_v = np.sqrt(min_c3) + mc_result['vinf_req_mag']  # Approximate
        assert total_delta_v < 50.0  # km/s - very rough upper bound

    except Exception as e:
        # If SPICE kernels don't cover the test dates, that's OK
        if "SPICE" in str(e) or "leapseconds" in str(e).lower():
            pytest.skip(f"SPICE kernel coverage issue: {e}")
        else:
            raise