"""Configuration and constants for LambertLab."""

from pathlib import Path

# Default paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
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
MU_SUN = 1.32712440018e20  # km^3/s^2
MU_MARS = 4.282837e4  # km^3/s^2
R_MARS = 3396.2  # km

# Constants
AU = 149597870.7  # km, astronomical unit
MU_SUN = 1.32712440018e20  # m^3/s^2, gravitational parameter of Sun
MU_MARS = 42828.37  # km^3/s^2, gravitational parameter of Mars
RP_MIN_MARS = 300.0  # km, minimum periapsis radius for Mars flyby

# Default bodies (NAIF IDs)
EARTH_ID = "399"
MARS_ID = "4"  # Mars barycenter

# Default frame
FRAME = "J2000"