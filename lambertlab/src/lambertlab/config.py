"""Configuration and constants for LambertLab."""

import os
from pathlib import Path

# Default paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KERNELS_DIR = DATA_DIR / "kernels"

# Default kernel files
DEFAULT_KERNELS = [
    KERNELS_DIR / "naif0012.tls",
    KERNELS_DIR / "de440.bsp",
    KERNELS_DIR / "gm_de440.tpc",
    KERNELS_DIR / "20000001.bsp",
    KERNELS_DIR / "mar097.bsp",
    KERNELS_DIR / "pck00011.tpc",
]

# Constants
AU = 149597870.7  # km, astronomical unit
MU_SUN = 1.32712440018e20  # m^3/s^2, gravitational parameter of Sun

# Default bodies (NAIF IDs)
EARTH_ID = "399"
MARS_ID = "4"  # Mars barycenter

# Default frame
FRAME = "J2000"