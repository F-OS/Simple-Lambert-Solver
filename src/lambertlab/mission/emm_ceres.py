"""Generic multi-gravity-assist (MGA) trajectory optimization using PyKEP.

This module provides utilities for optimizing multi-leg trajectories with
gravity assists using PyKEP's built-in MGA optimizers. It integrates with
lambertlab's SPICE ephemeris infrastructure for accurate planetary positions.

All units are PyKEP-consistent: km, seconds, km/s, km³/s².
"""

import pykep as pk
from astropy.time import Time
import numpy as np
from typing import Tuple, List, Dict, Union
import logging

# Import lambertlab SPICE infrastructure
from ..core.spice_io import load_kernels, rv_helio_spice, ensure_spice_loaded
from ..core.config import R_MARS, MU_MARS, MU_SUN

# NAIF ID mapping for common bodies
NAIF_IDS = {
    'sun': '10',
    'mercury': '199',
    'venus': '299',
    'earth': '399',
    'mars': '4',  # Mars barycenter
    'jupiter': '5',  # Jupiter barycenter
    'saturn': '6',  # Saturn barycenter
    'ceres': '20000001',  # Small body kernel uses 20000001, not 2000001
}

# Planetary radii (km) for common bodies
PLANET_RADII = {
    'sun': 695700.0,
    'mercury': 2439.7,
    'venus': 6051.8,
    'earth': 6378.1,
    'mars': 3396.2,
    'jupiter': 71492.0,
    'saturn': 60268.0,
    'ceres': 476.2,
}

# Planetary mu values (km³/s²) for common bodies
PLANET_MU = {
    'sun': 1.32712440018e11,  # km³/s²
    'mercury': 22032.0,
    'venus': 324858.59,
    'earth': 398600.4418,
    'mars': 42828.37,
    'jupiter': 126686534.0,
    'saturn': 37931187.0,
    'ceres': 63.1,
}


class SpicePlanet:
    """
    Wrapper for PyKEP SPICE planet that uses lambertlab's SPICE kernels.
    
    This ensures PyKEP uses the same SPICE ephemerides as the rest of
    lambertlab, maintaining consistency across the codebase.
    """
    
    def __init__(self, naif_id: str, name: str = None):
        """
        Initialize SPICE-based planet.
        
        Parameters
        ----------
        naif_id : str
            NAIF ID of the body
        name : str, optional
            Display name
        """
        self.naif_id = naif_id
        self.body_name = name or naif_id
        
        # Get physical parameters
        body_lower = self.body_name.lower()
        self.radius = PLANET_RADII.get(body_lower, 0.0)
        self.mu_self = PLANET_MU.get(body_lower, 0.0)
        
        # PyKEP MGA requires mu_central_body (for heliocentric orbits, this is mu_sun)
        self.mu_central_body = PLANET_MU['sun']
        
        # Ensure SPICE kernels are loaded
        ensure_spice_loaded()
        
        # Create PyKEP SPICE planet
        # Note: PyKEP's SPICE planet expects different parameters
        # For now, we'll use a custom ephemeris function approach
        self._planet = None
    
    def eph(self, mjd2000: float) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Return ephemeris at given epoch using SPICE.
        
        Parameters
        ----------
        mjd2000 : float
            Epoch in MJD2000 format
            
        Returns
        -------
        r : Tuple[float, float, float]
            Position vector (km)
        v : Tuple[float, float, float]
            Velocity vector (km/s)
        """
        # Convert MJD2000 to astropy Time
        epoch_time = from_mjd2000(mjd2000)
        
        # Ensure SPICE kernels are loaded
        ensure_spice_loaded()
        
        # Get state from SPICE
        r, v = rv_helio_spice(self.naif_id, epoch_time)
        
        # Return as tuples (PyKEP format)
        return (tuple(float(x) for x in r), tuple(float(x) for x in v))
    
    def __repr__(self):
        return f"SpicePlanet({self.body_name}, NAIF ID: {self.naif_id})"


def get_spice_planet(body_name: str) -> SpicePlanet:
    """
    Create a SPICE-based planet for use with PyKEP optimizers.
    
    Parameters
    ----------
    body_name : str
        Planet name (e.g., 'earth', 'mars', 'ceres')
        Case-insensitive
        
    Returns
    -------
    SpicePlanet
        SPICE-based planet object compatible with PyKEP
        
    Raises
    ------
    ValueError
        If planet name is not recognized
    """
    body_lower = body_name.lower()
    
    if body_lower not in NAIF_IDS:
        available = ', '.join(NAIF_IDS.keys())
        raise ValueError(f"Unknown planet: {body_name}. Available: {available}")
    
    naif_id = NAIF_IDS[body_lower]
    return SpicePlanet(naif_id, body_name)


def get_planet_radius(body_name: str) -> float:
    """
    Get planetary radius in km.
    
    Parameters
    ----------
    body_name : str
        Planet name
        
    Returns
    -------
    float
        Radius in km
    """
    body_lower = body_name.lower()
    if body_lower in PLANET_RADII:
        return PLANET_RADII[body_lower]
    
    logger = logging.getLogger(__name__)
    logger.warning(f"Unknown radius for {body_name}, assuming 0")
    return 0.0


def get_planet_mu(body_name: str) -> float:
    """
    Get planetary gravitational parameter in km³/s².
    
    Parameters
    ----------
    body_name : str
        Planet name
        
    Returns
    -------
    float
        Mu in km³/s²
    """
    body_lower = body_name.lower()
    if body_lower in PLANET_MU:
        return PLANET_MU[body_lower]
    
    logger = logging.getLogger(__name__)
    logger.warning(f"Unknown mu for {body_name}, assuming 0")
    return 0.0


def to_mjd2000(t: Time) -> float:
    """
    Convert astropy.time.Time to PyKEP's MJD2000 epoch.
    
    PyKEP uses Modified Julian Date 2000 as its time reference.
    MJD2000 = 0 corresponds to 2000-01-01 12:00:00 TT.
    MJD2000 = MJD - 51544.5
    
    Parameters
    ----------
    t : astropy.time.Time
        Time to convert
        
    Returns
    -------
    float
        MJD2000 epoch in days
    """
    # MJD2000 = MJD - 51544.5
    # where 51544.5 is the MJD of J2000.0 (2000-01-01 12:00:00 TT)
    mjd = t.mjd  # Modified Julian Date
    mjd2000 = mjd - 51544.5
    return mjd2000


def from_mjd2000(mjd2000: float) -> Time:
    """
    Convert PyKEP's MJD2000 epoch to astropy.time.Time.
    
    Parameters
    ----------
    mjd2000 : float
        MJD2000 epoch in days
        
    Returns
    -------
    astropy.time.Time
        Converted time
    """
    # MJD = MJD2000 + 51544.5
    mjd = mjd2000 + 51544.5
    return Time(mjd, format='mjd', scale='tt')


def days_to_seconds(days: float) -> float:
    """Convert days to seconds."""
    return days * 86400.0


def seconds_to_days(seconds: float) -> float:
    """Convert seconds to days."""
    return seconds / 86400.0


def pretty_print_solution(
    t0: float,
    tof1: float,
    tof2: float,
    rp_flyby: float,
    beta_flyby: float,
    dv_total: float,
    vinf_arr: float,
    flyby_body: str = "mars",
    vinf_dep: float = None
) -> None:
    """
    Pretty-print a trajectory solution.
    
    Parameters
    ----------
    t0 : float
        Launch epoch (MJD2000)
    tof1 : float
        First leg time of flight (days)
    tof2 : float
        Second leg time of flight (days)
    rp_flyby : float
        Flyby periapsis radius (km)
    beta_flyby : float
        Flyby B-plane angle (radians)
    dv_total : float
        Total Δv (km/s)
    vinf_arr : float
        Arrival v∞ at target (km/s)
    flyby_body : str
        Name of flyby body
    vinf_dep : float, optional
        Departure v∞ from origin (km/s)
    """
    t_launch = from_mjd2000(t0)
    t_flyby = from_mjd2000(t0 + tof1)
    t_arrival = from_mjd2000(t0 + tof1 + tof2)
    
    r_flyby_body = get_planet_radius(flyby_body)
    h_flyby = rp_flyby - r_flyby_body
    
    print("\n" + "="*60)
    print("TRAJECTORY SOLUTION")
    print("="*60)
    print(f"Launch:      {t_launch.iso} UTC")
    print(f"{flyby_body.title()} Flyby:  {t_flyby.iso} UTC  (+{tof1:.1f} days)")
    print(f"Arrival:     {t_arrival.iso} UTC  (+{tof2:.1f} days)")
    print(f"Total TOF:   {tof1 + tof2:.1f} days")
    print("-"*60)
    print(f"{flyby_body.title()} rp:     {rp_flyby:.1f} km  (altitude: {h_flyby:.1f} km)")
    print(f"{flyby_body.title()} β:      {np.degrees(beta_flyby):.1f}°")
    print("-"*60)
    if vinf_dep is not None:
        print(f"Launch v∞:   {vinf_dep:.3f} km/s  (C3: {vinf_dep**2:.3f} km²/s²)")
    print(f"Arrival v∞:  {vinf_arr:.3f} km/s  (C3: {vinf_arr**2:.3f} km²/s²)")
    print(f"Total Δv:    {dv_total:.3f} km/s")
    print("="*60 + "\n")


def validate_flyby_altitude(
    rp: float,
    body_name: str,
    h_min_km: float = 300.0
) -> Tuple[bool, str]:
    """
    Validate flyby periapsis altitude constraint.
    
    Parameters
    ----------
    rp : float
        Periapsis radius (km)
    body_name : str
        Name of flyby body
    h_min_km : float
        Minimum altitude above surface (km)
        
    Returns
    -------
    valid : bool
        True if constraint satisfied
    message : str
        Validation message
    """
    r_body = get_planet_radius(body_name)
    h = rp - r_body
    if h < h_min_km:
        return False, f"{body_name.title()} altitude {h:.1f} km < minimum {h_min_km:.1f} km"
    return True, f"{body_name.title()} altitude {h:.1f} km OK"


def compute_arrival_vinf(v_sc: np.ndarray, v_planet: np.ndarray) -> float:
    """
    Compute arrival v∞ magnitude.
    
    Parameters
    ----------
    v_sc : np.ndarray
        Spacecraft velocity (km/s)
    v_planet : np.ndarray
        Planet velocity (km/s)
        
    Returns
    -------
    float
        v∞ magnitude (km/s)
    """
    vinf = v_sc - v_planet
    return float(np.linalg.norm(vinf))
