"""Type aliases and constants for LambertLab."""

from __future__ import annotations

from typing import Union, Tuple
import numpy as np
from astropy.time import Time
from astropy import units as u

# Type aliases
Vec = np.ndarray  # 3D vector (km or km/s)
State = Tuple[Vec, Vec]  # (position, velocity) tuple
TimeLike = Union[str, Time]

# Unit constants
KM = u.km
KMS = u.km / u.s
DAY = u.day
DEG = u.deg
RAD = u.rad

# Tolerances
VEL_TOL_KMS = 1e-3  # km/s tolerance for v_inf matching
ANG_TOL_DEG = 1.0   # degree tolerance for angle matching
C3_TOL = 1e-6       # C3 tolerance for convergence

# Default bodies (NAIF IDs)
EARTH_ID = "399"
MARS_ID = "499"
CERES_ID = "20000001"  # Ceres
SUN_ID = 10

# Default frames
FRAME = "J2000"
CENTER = "10"