# tests/conftest.py
import os
import sys
import pytest
import warnings

# Suppress ERFA warnings for future dates
warnings.filterwarnings("ignore", message=".*dubious year.*", category=UserWarning, module="erfa.core")

# Register custom marks
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("filterwarnings", "ignore:.*dubious year.*:UserWarning")

from astropy.time import Time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def kernel_paths():
    # Adjust to your real paths - try the original Unix leapseconds file
    paths = [
        r"data\kernels\naif0012.tls",  # Original Unix leapseconds
        r"data\kernels\de440.bsp",
        r"data\kernels\mar097.bsp",
        r"data\kernels\20000001.bsp",  # Ceres SPK
    ]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        pytest.skip(f"Missing kernels: {missing}")
    return paths

@pytest.fixture(scope="session")
def dates():
    return {
        # EM window near a real low-C3 opportunity (2026-2027)
        "em_dep": Time("2026-06-25 00:00:00", scale="utc"),
        "em_arr": Time("2027-01-07 00:00:00", scale="utc"),  # TOF ≈ 196 d
        # Use Ceres date within SPK coverage (2025-2045)
        "mc_arr": Time("2028-06-20 00:00:00", scale="utc"),
    }

@pytest.fixture(scope="session")
def times_sample():
    """Sample times for Lambert solver testing."""
    t_dep = Time("2026-06-25 00:00:00", scale="utc")
    t_arr = Time("2027-01-07 00:00:00", scale="utc")  # ~196 days later
    tof = t_arr - t_dep
    return t_dep, t_arr, tof