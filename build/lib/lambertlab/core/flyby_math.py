"""Ballistic flyby feasibility mathematics."""

from __future__ import annotations

import numpy as np
from astropy import units as units
from astropy import constants as const
from typing import Tuple


def angle_between(u: np.ndarray, v: np.ndarray) -> units.Quantity[units.rad]:
    """Compute angle between two 3D vectors.
    
    Args:
        u, v: 3D numpy arrays
        
    Returns:
        Angle in radians as astropy Quantity
    """
    u_norm = u / np.linalg.norm(u)
    v_norm = v / np.linalg.norm(v)
    cos_theta = np.clip(np.dot(u_norm, v_norm), -1, 1)
    angle_rad = float(np.arccos(cos_theta))
    return units.Quantity(angle_rad, units.rad)


def rp_from_delta(vinf: float, delta: units.Quantity[units.rad], mu: float) -> units.Quantity[units.km]:
    """Compute periapsis radius for hyperbolic flyby.
    
    Args:
        vinf: Hyperbolic excess velocity magnitude (km/s)
        delta: Turn angle (radians)
        mu: Gravitational parameter (km^3/s^2)
        
    Returns:
        Periapsis radius in km as astropy Quantity
    """
    # For hyperbolic orbit: e = 1 / sin(delta/2)
    # Semi-major axis a = -mu / vinf^2
    # Periapsis rp = a * (1 - e)
    
    sin_half_delta = np.sin(delta.value / 2)
    if sin_half_delta <= 0:
        return np.inf * units.km  # Invalid
    
    e = 1.0 / sin_half_delta
    a = -mu / (vinf ** 2)  # negative for hyperbola
    rp = a * (1 - e)
    
    return rp * units.km


def feasibility(vinf_in_vec: np.ndarray, vinf_out_req_vec: np.ndarray, mu: float, rp_min: float) -> dict:
    """Assess ballistic flyby feasibility.
    
    Args:
        vinf_in_vec: Incoming v_inf vector (km/s) [3]
        vinf_out_req_vec: Required outgoing v_inf vector (km/s) [3]  
        mu: Gravitational parameter (km^3/s^2)
        rp_min: Minimum allowed periapsis radius (km)
        
    Returns:
        dict with:
        - ballistic_ok: bool
        - delta_req_rad: required turn angle (rad)
        - rp_needed_km: required periapsis radius (km)
        - mag_mismatch_kms: | |vinf_in| - |vinf_out| | (km/s)
        - angle_err_deg: angle between vectors (deg)
    """
    vinf_in_mag = np.linalg.norm(vinf_in_vec)
    vinf_out_mag = np.linalg.norm(vinf_out_req_vec)
    
    mag_mismatch_kms = abs(vinf_in_mag - vinf_out_mag)
    
    delta_req = angle_between(vinf_in_vec, vinf_out_req_vec)
    delta_req_rad = delta_req.value
    angle_err_deg = delta_req.to(units.deg).value
    
    # Use average v_inf magnitude for rp calculation
    vinf_avg = (vinf_in_mag + vinf_out_mag) / 2
    rp_needed = rp_from_delta(vinf_avg, delta_req, mu)
    rp_needed_km = rp_needed.value
    
    # Feasibility criteria
    mag_tol = 0.1  # km/s tolerance for magnitude match
    ballistic_ok = (mag_mismatch_kms < mag_tol) and (rp_needed_km >= rp_min)
    
    return {
        'ballistic_ok': ballistic_ok,
        'delta_req_rad': delta_req_rad,
        'rp_needed_km': rp_needed_km,
        'mag_mismatch_kms': mag_mismatch_kms,
        'angle_err_deg': angle_err_deg
    }


def powered_delta_v(vinf_in_vec: np.ndarray, vinf_out_req_vec: np.ndarray, mu: float, rp_min: float) -> float:
    """Estimate delta-V required at periapsis for powered flyby.
    
    When ballistic flyby is infeasible at rp_min, calculates the velocity change
    needed at periapsis to achieve the required outgoing asymptote.
    
    Args:
        vinf_in_vec: Incoming v_inf vector (km/s) [3]
        vinf_out_req_vec: Required outgoing v_inf vector (km/s) [3]
        mu: Gravitational parameter (km^3/s^2)
        rp_min: Minimum safe periapsis radius (km)
        
    Returns:
        Delta-V magnitude at periapsis (km/s)
    """
    vinf_in_mag = np.linalg.norm(vinf_in_vec)
    vinf_out_mag = np.linalg.norm(vinf_out_req_vec)
    
    # For hyperbolic orbit at rp_min, calculate semi-major axis
    # a = -mu / vinf_in^2 (negative for hyperbola)
    a = -mu / (vinf_in_mag ** 2)
    
    # Eccentricity for this orbit: e = 1 / sqrt(1 + (rp/a)^2 * (vinf^2/mu)^2)
    # But more simply: e = sqrt(1 - (rp/|a|))
    e = np.sqrt(1 - (rp_min / abs(a)))
    
    # Velocity at periapsis for incoming hyperbola
    # vp = sqrt( mu * (2/rp - 1/|a|) ) = sqrt( mu * (2/rp + 1/|a|) ) since a is negative
    vp_in = np.sqrt(mu * (2/rp_min + 1/abs(a)))
    
    # Direction of velocity at periapsis for incoming asymptote
    # For hyperbola, velocity at periapsis is perpendicular to radius vector
    # and in the plane of the asymptote. For simplicity, assume the turn happens
    # in the plane containing both v_inf vectors.
    
    # The required outgoing velocity at periapsis should produce vinf_out_req
    # For the outgoing hyperbola with same rp_min and vinf_out_mag
    a_out = -mu / (vinf_out_mag ** 2)
    vp_out_required = np.sqrt(mu * (2/rp_min + 1/abs(a_out)))
    
    # The angle between incoming and outgoing asymptotes
    delta_req = angle_between(vinf_in_vec, vinf_out_req_vec).value
    
    # For powered flyby, we need to change the velocity direction at periapsis
    # The required velocity change depends on the turn angle
    # For small turns, dv ≈ vp * delta, but for larger turns we need proper calculation
    
    # Current velocity at periapsis (magnitude vp_in, direction based on incoming asymptote)
    # Required velocity at periapsis (magnitude vp_out_required, direction for outgoing asymptote)
    
    # The delta-V is the vector difference needed to go from current to required velocity
    # For simplicity, if magnitudes are similar, it's approximately vp * sin(delta/2) * 2 or similar
    # But let's calculate it properly
    
    # The turn angle delta corresponds to the angle change at periapsis
    # For hyperbolic orbits, the relationship is more complex, but approximately:
    # The delta-V needed is roughly 2 * vinf * sin(delta/2) for small delta
    # But for powered flyby at fixed rp, it's different
    
    # Actually, let's think differently. The velocity at periapsis determines the asymptote.
    # If we have incoming vp_in and want outgoing vp_out_required at angle delta_req,
    # then the delta-V is the magnitude of the vector difference.
    
    # For a given turn angle delta, the required velocity change at periapsis is:
    # dv = sqrt(vp_in^2 + vp_out^2 - 2*vp_in*vp_out*cos(delta))
    
    # But vp_in and vp_out depend on the vinf magnitudes, which may be different
    dv_peri = np.sqrt(vp_in**2 + vp_out_required**2 - 2*vp_in*vp_out_required*np.cos(delta_req))
    
    return dv_peri