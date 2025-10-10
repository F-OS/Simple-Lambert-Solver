"""
LambertLab Test Suite - Step-by-Step System Validation
=======================================================

Modern test battery using PyKEP for realistic interplanetary mission scenarios.

Test Structure:
1. Unit Tests - Core components (Lambert, flyby, ephemeris)
2. Integration Tests - Multi-leg trajectories
3. Regression Tests - Known good missions (Mars 2020, Juno, etc.)
4. Stress Tests - Large grid searches

All tests use realistic values and validate physics constraints.
"""

import pytest
import numpy as np
from pathlib import Path
from astropy import units as u
from astropy.time import Time

# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
KERNEL_DIR = DATA_DIR / "kernels"

# Realistic mission parameters
EARTH_MARS_2025 = {
    "dep_date": "2025-01-15",
    "arr_date": "2025-08-20",
    "expected_c3_range": (10.0, 30.0),  # km²/s²
    "expected_tof_days": 217,
    "description": "Typical Mars opportunity window"
}

MARS_FLYBY_SCENARIO = {
    "altitude_km": 300.0,  # Typical Mars flyby altitude
    "rp_km": 3696.2,  # Mars radius + 300 km
    "mu_mars": 42828.0,  # km³/s²
    "expected_max_turn_deg": 90.0,  # Typical gravity assist
}

# Physics constraints
PHYSICS_TOLERANCES = {
    "vmag_conservation": 1e-6,  # km/s - v_inf magnitude conservation
    "energy_conservation": 1e-3,  # km²/s² - C3 numerical precision
    "position_accuracy": 1e-3,  # km - ephemeris precision
}


@pytest.fixture(scope="session")
def kernel_paths():
    """Required SPICE kernel paths."""
    kernels = [
        KERNEL_DIR / "naif0012.tls",  # Leap seconds
        KERNEL_DIR / "de440.bsp",     # Planetary ephemeris
        KERNEL_DIR / "mar097.bsp",    # Mars
        KERNEL_DIR / "gm_de440.tpc",  # Gravity parameters
        KERNEL_DIR / "pck00011.tpc",  # Physical constants
    ]
    
    # Verify all kernels exist
    missing = [k for k in kernels if not k.exists()]
    if missing:
        pytest.skip(f"Missing SPICE kernels: {missing}")
    
    return [str(k) for k in kernels]


@pytest.fixture(scope="session")
def pykep_available():
    """Check if PyKEP is available."""
    try:
        import pykep as pk
        version = pk.__version__
        return True
    except ImportError:
        pytest.skip("PyKEP not available - run 'conda activate lambertlab'")
        return False


@pytest.fixture(scope="session")
def spice_loaded(kernel_paths):
    """Load SPICE kernels once for all tests."""
    import sys
    from pathlib import Path
    # Add src to path if needed
    src_path = Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from lambertlab.core.spice_io import load_kernels
    load_kernels(kernel_paths)
    return True


def approx_equal(a, b, tolerance=1e-6):
    """Check if two values are approximately equal."""
    return abs(a - b) < tolerance


def vector_approx_equal(v1, v2, tolerance=1e-6):
    """Check if two vectors are approximately equal."""
    v1 = np.asarray(v1)
    v2 = np.asarray(v2)
    return np.linalg.norm(v1 - v2) < tolerance
