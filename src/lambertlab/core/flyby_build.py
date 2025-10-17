"""Non-coplanar flyby velocity construction using poliastro."""

from __future__ import annotations

import numpy as np
from astropy import units as units

from .flyby_math import angle_between
from .config import MU_MARS


def _compute_delta_from_rp(vinf: float, rp_km: float, mu: float) -> float:
    """Compute turn angle delta from v_inf and periapsis radius."""
    e = 1 + rp_km * vinf**2 / mu  # eccentricity
    sin_half_delta = 1.0 / e
    if sin_half_delta > 1:
        return np.pi  # max turn angle
    delta = 2 * np.arcsin(sin_half_delta)
    return delta


def build_outbound(v_sc_arr_helio: np.ndarray, rp_km: float, theta_deg: float) -> tuple[np.ndarray, float]:
    """Build outbound heliocentric velocity after Mars flyby.
    
    Args:
        v_sc_arr_helio: Incoming spacecraft velocity vector (km/s) [3]
        rp_km: Periapsis radius (km)
        theta_deg: Rotation angle in B-plane (degrees)
        
    Returns:
        (v_out_helio, turn_angle_rad): Outbound velocity vector and turn angle
    """
    v_in = v_sc_arr_helio
    vinf = np.linalg.norm(v_in)
    
    # Compute turn angle
    delta = _compute_delta_from_rp(vinf, rp_km, MU_MARS)
    
    # Compute delta_v magnitude
    delta_v_mag = 2 * vinf * np.sin(delta / 2)
    
    # Find orthonormal basis perpendicular to v_in
    v_in_unit = v_in / vinf
    # Choose arbitrary perpendicular vector
    if abs(v_in_unit[0]) > 0.1:
        perp = np.array([ -v_in_unit[1], v_in_unit[0], 0])
    else:
        perp = np.array([0, -v_in_unit[2], v_in_unit[1]])
    perp = perp / np.linalg.norm(perp)
    u1 = perp
    u2 = np.cross(v_in_unit, u1)
    
    # Rotate in B-plane by theta
    theta_rad = np.radians(theta_deg)
    delta_v = delta_v_mag * (np.cos(theta_rad) * u1 + np.sin(theta_rad) * u2)
    
    # Outbound velocity
    v_out = v_in + delta_v
    
    # Turn angle
    turn_angle_rad = angle_between(v_in, v_out).value
    
    return v_out, turn_angle_rad


def theta_sweep(v_sc_arr: np.ndarray, v_mars: np.ndarray, rp_km: float, vinf_req: np.ndarray, step_deg: float = 5.0) -> tuple[float, float]:
    """Sweep theta to find best match to required v_inf.
    
    Args:
        v_sc_arr: Incoming spacecraft velocity vector (km/s) [3]
        v_mars: Mars velocity vector (km/s) [3]
        rp_km: Periapsis radius (km)
        vinf_req: Required outgoing v_inf vector (km/s) [3]
        step_deg: Step size for theta sweep (degrees)
        
    Returns:
        (best_theta_deg, best_ang_err_deg): Best theta and corresponding angle error
    """
    theta_values = np.arange(-180, 180 + step_deg, step_deg)
    best_theta = 0.0
    best_ang_err = 180.0  # Max possible
    
    for theta_deg in theta_values:
        try:
            v_out, _ = build_outbound(v_sc_arr, rp_km, theta_deg)
            ang_err = angle_between(v_out, vinf_req).to(units.deg).value
            if ang_err < best_ang_err:
                best_ang_err = ang_err
                best_theta = theta_deg
        except Exception:
            # Skip invalid flybys
            continue
    
    return best_theta, best_ang_err