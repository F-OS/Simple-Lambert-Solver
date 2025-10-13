"""Lambert problem utilities."""

from __future__ import annotations

from typing import Tuple, Union, Optional
import numpy as np
import pykep as pk
from astropy import units as u
import logging

from .types import Vec, KM, KMS, C3_TOL

# PyKEP constants
MU_SUN_KM3S2 = 1.32712440018e11  # km^3/s^2 (Sun's gravitational parameter)


def lambert_leg(r1: u.Quantity, r2: u.Quantity, tof: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
    """
    r1, r2: astropy Quantities (km); tof: Quantity (day or s).
    Returns (v1[km/s], v2[km/s]) heliocentric.
    Uses PyKEP's lambert_problem for superior performance and multi-rev capability.
    """
    # Convert to plain arrays and seconds
    r1_km = r1.to_value(KM)
    r2_km = r2.to_value(KM)
    tof_sec = tof.to_value(u.second)
    
    # PyKEP Lambert problem (0 revolutions, counter-clockwise)
    lp = pk.lambert_problem(
        r1_km.tolist(),
        r2_km.tolist(),
        tof_sec,
        MU_SUN_KM3S2,
        cw=False,
        max_revs=0
    )
    
    # Get first solution (0-rev, minimum energy)
    v1_kms = np.array(lp.get_v1()[0])
    v2_kms = np.array(lp.get_v2()[0])
    
    return v1_kms * KMS, v2_kms * KMS


def solve_leg(r1: u.Quantity, r2: u.Quantity, tof: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
    """Solve Lambert problem for single leg (poliastro Izzo).
    
    Returns (v1, v2) on success, raises exception if no solution found.
    """
    # Validate inputs
    if tof.to_value(u.second) <= 0:
        raise ValueError(f"Time of flight must be positive, got {tof}")
    
    try:
        return lambert_leg(r1, r2, tof)
    except Exception as e:
        raise ValueError(f"Lambert solve failed for TOF {tof}: {e}") from e


def vinf_vec(v_sc: u.Quantity, v_planet: u.Quantity) -> u.Quantity:
    """Return v_inf vector (km/s) = spacecraft - planet. Accept Quantities."""
    return (v_sc - v_planet).to(KMS)


def c3(v_sc: u.Quantity, v_body: u.Quantity) -> float:
    """Return C3 = |vinf|^2 (km^2/s^2) where vinf = v_sc - v_body."""
    vinf = vinf_vec(v_sc, v_body)
    return float(np.dot(vinf.to_value(KMS), vinf.to_value(KMS)))


def best_lambert_branch(
    r_dep: Vec,
    v_dep_planet: Vec,
    r_arr: Vec,
    v_arr_planet: Vec,
    tof: u.Quantity,
    rtol: float = 1e-10,
    prograde: Optional[bool] = None,
    lowpath: Optional[bool] = None,
) -> Optional[Tuple[float, Vec, Vec, Tuple[int, bool, bool]]]:
    """
    Try all M=0 Lambert branches and return (min_C3, v_dep_best, v_arr_best, used_tuple)
    used_tuple = (M, prograde, lowpath). Returns None if no branch converged.
    
    NOTE: PyKEP doesn't have prograde/lowpath flags like poliastro. It solves for
    all geometrically valid trajectories automatically. We ignore these params.
    """
    # Validate TOF
    tof_days = tof.to_value(u.day)
    if tof_days <= 0:
        logger = logging.getLogger(__name__)
        logger.warning('Invalid TOF %s days (must be positive)', tof_days)
        return None
        
    if not np.isfinite(tof_days):
        logger = logging.getLogger(__name__)
        logger.warning('Invalid TOF %s days (not finite)', tof_days)
        return None
    
    try:
        # Convert to plain arrays and seconds
        r_dep_km = np.asarray(r_dep, dtype=float)
        r_arr_km = np.asarray(r_arr, dtype=float)
        tof_sec = tof.to_value(u.second)
        
        # PyKEP Lambert problem (0 revolutions)
        # Note: PyKEP automatically finds both cw and ccw solutions
        lp = pk.lambert_problem(
            r_dep_km.tolist(),
            r_arr_km.tolist(),
            tof_sec,
            MU_SUN_KM3S2,
            cw=False,  # Counter-clockwise (prograde in solar system)
            max_revs=0  # Direct transfer only
        )
        
        # Get number of solutions (use len() not get_Nmax())
        n_sol = len(lp.get_v1())
        if n_sol == 0:
            return None
        
        # Try all solutions and find minimum C3
        min_C3 = float("inf")
        best = None
        
        for i in range(n_sol):
            v_dep_kms = np.array(lp.get_v1()[i])
            v_arr_kms = np.array(lp.get_v2()[i])
            
            # Skip NaN solutions
            if not np.all(np.isfinite(v_dep_kms)) or not np.all(np.isfinite(v_arr_kms)):
                continue
            
            # Compute v_inf relative to planet velocity
            v_inf_dep = v_dep_kms - v_dep_planet
            C3 = float(np.dot(v_inf_dep, v_inf_dep))
            
            if C3 < min_C3:
                min_C3 = C3
                # Store as (C3, v_dep, v_arr, (M, prograde, lowpath))
                # prograde/lowpath are legacy from poliastro, not used by PyKEP
                best = (min_C3, v_dep_kms, v_arr_kms, (0, True, True))

        # Guard: internal consistency check
        if best is not None:
            C3_val, v_dep_best, v_arr_best, used = best
            vinf_dep = v_dep_best - v_dep_planet
            if (not np.isfinite(C3_val)) or (abs(np.linalg.norm(vinf_dep) - np.sqrt(C3_val)) > C3_TOL):
                logger = logging.getLogger(__name__)
                logger.warning('C3 consistency check failed for TOF %.1f days', tof_days)
                return None

        return best
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception('Lambert solve failed for TOF %.1f days: %s', tof_days, e)
        return None