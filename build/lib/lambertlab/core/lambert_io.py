"""Lambert problem utilities."""

from __future__ import annotations

from typing import Tuple, Union, Optional
import numpy as np
from poliastro.bodies import Sun
from poliastro.iod.izzo import lambert
from astropy import units as u

from .types import Vec, KM, KMS, C3_TOL


def lambert_leg(r1: u.Quantity, r2: u.Quantity, tof: u.Quantity) -> Tuple[u.Quantity, u.Quantity]:
    """
    r1, r2: astropy Quantities (km); tof: Quantity (day or s).
    Returns (v1[km/s], v2[km/s]) heliocentric.
    """
    solutions = list(lambert(Sun.k, r1.to(KM), r2.to(KM), tof))
    if len(solutions) == 0:
        raise ValueError("No Lambert solutions found")
    # Take the first solution (usually the minimum energy one)
    v1, v2 = solutions[0]
    return v1.to(KMS), v2.to(KMS)


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
    """
    # Validate TOF
    tof_days = tof.to_value(u.day)
    if tof_days <= 0:
        print(f"Error: Invalid TOF {tof_days} days (must be positive)")
        return None
        
    if not np.isfinite(tof_days):
        print(f"Error: Invalid TOF {tof_days} days (not finite)")
        return None
    
    try:
        min_C3 = float("inf")
        best = None
        
        # Try different numbers of revolutions M
        for M in [0]:  # Only try direct (M=0) transfers for now
            try:
                # poliastro returns a sequence of solutions for each M
                solutions = list(lambert(Sun.k, r_dep * KM, r_arr * KM, tof, M=M))
                if not solutions:
                    continue
                    
                for v_dep_tr, v_arr_tr in solutions:
                    # Convert to plain numpy km/s
                    v_dep_tr_kms = v_dep_tr.to_value(KMS)
                    v_arr_tr_kms = v_arr_tr.to_value(KMS)

                    # Compute v_inf relative to planet velocity
                    v_inf_dep = v_dep_tr_kms - v_dep_planet
                    C3 = float(np.dot(v_inf_dep, v_inf_dep))
                    if C3 < min_C3:
                        min_C3 = C3
                        best = (min_C3, v_dep_tr_kms, v_arr_tr_kms, (M, True, True))  # Returns heliocentric velocities
            except Exception:
                continue
                
        # If no solutions found with default M, try with prograde/lowpath variations
        if best is None:
            for pr in (True, False):
                for lp in (True, False):
                    try:
                        v_d, v_a = lambert(Sun.k, r_dep * KM, r_arr * KM, tof, M=0, prograde=pr, lowpath=lp)
                        v_d_kms = v_d.to_value(KMS)
                        dv = v_d_kms - v_dep_planet
                        C3_try = float(np.dot(dv, dv))
                        if C3_try < min_C3:
                            min_C3 = C3_try
                            best = (C3_try, v_d_kms, v_a.to_value(KMS), (0, pr, lp))
                    except Exception:
                        pass

        # Guard: internal consistency check
        if best is not None:
            C3_val, v_dep_best, v_arr_best, used = best
            vinf_dep = v_dep_best - v_dep_planet
            if (not np.isfinite(C3_val)) or (abs(np.linalg.norm(vinf_dep) - np.sqrt(C3_val)) > C3_TOL):
                print(f"Warning: C3 consistency check failed for TOF {tof_days:.1f} days")
                return None

        return best
    except Exception as e:
        print(f"Error: Lambert solve failed for TOF {tof_days:.1f} days: {e}")
        return None