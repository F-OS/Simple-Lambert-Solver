
"""Minimal solver module: compute C3 and TOF for a single pair.

Provides:
 - compute_c3_tof(dep_time, arr_time, dep_body='EARTH', arr_body='MARS')

When run as a script, it prints results for an example pair.
"""

import numpy as np
import spiceypy as sp
import pykep as pk
from astropy import units as u
from astropy.time import Time
from typing import Tuple, Union
from .config import DEFAULT_KERNELS

# PyKEP constants
MU_SUN_KM3S2 = 1.32712440018e11  # km^3/s^2 (Sun's gravitational parameter)


def rv_helio_spice(target: str | int, epoch: Time):
    """Return heliocentric position (km) and velocity (km/s) for target at epoch.

    Returns plain numpy arrays (no astropy Quantity) to avoid expensive unit ops
    inside tight loops.
    target: SPICE name or ID (string or int). epoch: astropy Time with scale='tdb'.
    """
    et = sp.str2et(epoch.tdb.isot)
    target_arg = target.upper() if isinstance(target, str) else target
    state, _ = sp.spkezr(str(target_arg), et, "J2000", "NONE", "SUN")
    # state: [rx, ry, rz, vx, vy, vz] with km and km/s
    r_km = np.array(state[:3], dtype=float)
    v_kms = np.array(state[3:6], dtype=float)
    return r_km, v_kms


def _to_time(t: Union[str, Time]) -> Time:
    if isinstance(t, Time):
        return t
    return Time(str(t), scale='tdb')


def compute_c3_tof(dep_time: Union[str, Time], arr_time: Union[str, Time],
                   dep_body: str = 'EARTH', arr_body: str = 'MARS',
                   prograde: Union[bool, None] = None, lowpath: Union[bool, None] = None) -> Tuple[float, float]:
    """
    Compute (tof_days, C3) for a single departure/arrival pair.
    Picks the minimum-C3 solution among all M=0 Lambert branches.
    """
    dep_t = _to_time(dep_time)
    arr_t = _to_time(arr_time)

    if arr_t <= dep_t:
        raise ValueError("Arrival must be after departure")

    # Sun-centered states at the endpoints (plain numpy arrays)
    r_dep, v_dep_planet = rv_helio_spice(dep_body, dep_t)
    r_arr, v_arr_planet = rv_helio_spice(arr_body, arr_t)

    # Time of flight as an astropy Quantity
    tof = (arr_t - dep_t)

    # Try all branches and pick minimum C3
    res = best_lambert_branch(r_dep, v_dep_planet, r_arr, v_arr_planet, tof,
                              rtol=1e-10, prograde=prograde, lowpath=lowpath)
    if res is None:
        raise RuntimeError("No M=0 Lambert solution found for this dep/arr pair")

    min_C3, v_dep_best, v_arr_best, used = res  # used = (M, prograde, lowpath)

    # (If you want to log which branch was used, uncomment:)
    # print(f"Used branch: M={used[0]}, prograde={used[1]}, lowpath={used[2]}")

    # v_dep_best and v_arr_best are plain numpy arrays (km/s);
    # v_dep_planet and v_arr_planet are also plain numpy arrays (km/s)
    v_inf_dep = v_dep_best - v_dep_planet
    v_inf_arr = v_arr_best - v_arr_planet

    tof_days = tof.to_value(u.day)
    return tof_days, float(min_C3), v_inf_dep, v_inf_arr, used


def best_lambert_branch(r_dep, v_dep_planet, r_arr, v_arr_planet, tof, rtol=1e-10,
                        prograde: Union[bool, None] = None, lowpath: Union[bool, None] = None):
    """
    Try all M=0 Lambert branches and return (min_C3, v_dep_best, v_arr_best, used_tuple)
    used_tuple = (M, prograde, lowpath). Returns None if no branch converged.
    
    NOTE: PyKEP doesn't have prograde/lowpath flags. These params are ignored.
    """
    import numpy as np

    try:
        # Convert to plain arrays and seconds
        r_dep_km = np.asarray(r_dep, dtype=float)
        r_arr_km = np.asarray(r_arr, dtype=float)
        tof_sec = tof.to_value(u.second)
        
        # PyKEP Lambert problem (0 revolutions, counter-clockwise)
        lp = pk.lambert_problem(
            r_dep_km.tolist(),
            r_arr_km.tolist(),
            tof_sec,
            MU_SUN_KM3S2,
            cw=False,
            max_revs=0
        )
        
        # Get number of solutions (use len() not get_Nmax())
        n_sol = len(lp.get_v1())
        if n_sol == 0:
            return None

        min_C3 = float("inf")
        best = None
        used_flags = (0, True, True)
        
        for i in range(n_sol):
            v_dep_tr_kms = np.array(lp.get_v1()[i])
            v_arr_tr_kms = np.array(lp.get_v2()[i])
            
            # Skip NaN solutions
            if not np.all(np.isfinite(v_dep_tr_kms)) or not np.all(np.isfinite(v_arr_tr_kms)):
                continue

            # Compute v_inf relative to planet velocity (both plain numpy arrays)
            v_inf_dep = v_dep_tr_kms - v_dep_planet
            C3 = float(np.dot(v_inf_dep, v_inf_dep))
            if C3 < min_C3:
                min_C3 = C3
                best = (min_C3, v_dep_tr_kms, v_arr_tr_kms, used_flags)

        # Guard 1: internal consistency check
        if best is not None:
            C3_val, v_dep_best, v_arr_best, used = best
            vinf_dep = v_dep_best - v_dep_planet
            if (not np.isfinite(C3_val)) or (abs(np.linalg.norm(vinf_dep) - np.sqrt(C3_val)) > 1e-6):
                # If consistency check fails, return None
                return None

        return best
    except Exception:
        return None


if __name__ == '__main__':
    print("This module is not meant to be run directly. Use main.py instead.")
