
"""Minimal solver module: compute C3 and TOF for a single pair.

Provides:
 - load_kernels(): load SPICE kernels used for state lookups.
 - compute_c3_tof(dep_time, arr_time, dep_body='EARTH', arr_body='MARS')

When run as a script, it prints results for an example pair.
"""

import numpy as np
import spiceypy as sp
from astropy import units as u
from astropy.time import Time
from poliastro.bodies import Sun
from poliastro.iod.izzo import lambert
from typing import Tuple, Union
from .config import DEFAULT_KERNELS


def load_kernels() -> None:
    """Load SPICE kernels from default paths."""
    for kernel in DEFAULT_KERNELS:
        print(f"Loading kernel: {kernel} (exists: {kernel.exists()})")
        if kernel.exists():
            try:
                sp.furnsh(kernel.as_posix())
                print(f"Successfully loaded {kernel}")
            except Exception as e:
                print(f"Error loading kernel {kernel}: {e}")
        else:
            print(f"Warning: Kernel {kernel} not found.")


def rv_helio_spice(target: str, epoch: Time):
    """Return heliocentric position (km) and velocity (km/s) for target at epoch.

    Returns plain numpy arrays (no astropy Quantity) to avoid expensive unit ops
    inside tight loops.
    target: SPICE name or ID (string). epoch: astropy Time with scale='tdb'.
    """
    et = sp.str2et(epoch.tdb.isot)
    state, _ = sp.spkezr(target.upper(), et, "J2000", "NONE", "SUN")
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
    """
    from poliastro.bodies import Sun
    from poliastro.iod.izzo import lambert
    import numpy as np
    from astropy import units as u

    # poliastro's lambert doesn't accept prograde/lowpath, so just use M=0
    try:
        # Try default lambert call first (poliastro returns a sequence of solutions)
        solutions = list(lambert(Sun.k, r_dep * u.km, r_arr * u.km, tof, M=0))
        if not solutions:
            return None

        min_C3 = float("inf")
        best = None
        used_flags = (0, True, True)
        for v_dep_tr, v_arr_tr in solutions:
            # poliastro returns Quantity arrays (km/s). Convert to plain numpy km/s
            v_dep_tr_kms = v_dep_tr.to(u.km / u.s).value
            v_arr_tr_kms = v_arr_tr.to(u.km / u.s).value

            # Compute v_inf relative to planet velocity (both plain numpy arrays)
            v_inf_dep = v_dep_tr_kms - v_dep_planet
            C3 = float(np.dot(v_inf_dep, v_inf_dep))
            if C3 < min_C3:
                min_C3 = C3
                best = (min_C3, v_dep_tr_kms, v_arr_tr_kms, used_flags)

        # Guard 1: internal consistency check — if result looks NaN/Inf or inconsistent, re-enumerate
        if best is not None:
            C3_val, v_dep_best, v_arr_best, used = best
            vinf_dep = v_dep_best - v_dep_planet
            if (not np.isfinite(C3_val)) or (abs(np.linalg.norm(vinf_dep) - np.sqrt(C3_val)) > 1e-6):
                # Re-enumerate across prograde/lowpath if requested or available
                res = None
                for pr in (True, False) if prograde is None else (prograde,):
                    for lp in (True, False) if lowpath is None else (lowpath,):
                        try:
                            v_d, v_a = lambert(Sun.k, r_dep * u.km, r_arr * u.km, tof, M=0, prograde=pr, lowpath=lp)
                            v_d_kms = v_d.to(u.km / u.s).value
                            dv = v_d_kms - v_dep_planet
                            C3_try = float(np.dot(dv, dv))
                            if (res is None) or (C3_try < res[0]):
                                res = (C3_try, v_d_kms, v_a.to(u.km / u.s).value, (0, pr, lp))
                        except Exception:
                            pass
                if res:
                    return res

        return best
    except Exception:
        return None


if __name__ == '__main__':
    print("This module is not meant to be run directly. Use main.py instead.")
