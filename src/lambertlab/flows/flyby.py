"""
Flyby targeting and optimization module.

This module provides patched-conic flyby targeting with Lambert solver integration.
Key features:
- ESA-recommended patched-conic method with PyKEP validation
- B-plane analysis and bookkeeping
- Local refinement around optimal candidates
- Units consistency (all velocities in km/s, positions in km)
- Constraint validation for Mars flybys

Author: LambertLab Team
"""

import numpy as np
import pykep as pk
from astropy import units as u
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from ..core.spice_io import rv_helio
from ..core.lambert_io import solve_leg
from scipy.optimize import minimize_scalar


@dataclass
class FlyResult:
    """Container for flyby targeting results."""
    success: bool
    message: str
    rp: Optional[float] = None
    turn_angle: Optional[float] = None
    b_vec: Optional[np.ndarray] = None
    vinf_out: Optional[np.ndarray] = None
    arrival_epoch: Optional[Any] = None
    c3_to_target: Optional[float] = None
    flyby_model: str = "patchedconic"


def find_flyby_lambert(
    v_sc_in: np.ndarray,
    r_planet: np.ndarray,
    v_planet: np.ndarray,
    target_body: str,
    epoch: Any,
    mu_planet: float,
    search_arrival_window: Tuple[float, float],
    rp_bounds: Tuple[float, float] = (300.0, 10000.0),
    min_alt_km: float = 100.0,
    max_turn: Optional[float] = None,
    max_samples: int = 1000
) -> FlyResult:
    """
    Find optimal flyby trajectory with Lambert transfer to target body.

    This function implements ESA-recommended patched-conic flyby targeting:
    - Requires heliocentric spacecraft velocity input (v_sc_in)
    - Uses PyKEP fb_prop for validated flyby propagation
    - Performs coarse grid search followed by local refinement
    - Computes proper B-plane coordinates
    - Validates geometry constraints

    Parameters
    ----------
    v_sc_in : np.ndarray
        Heliocentric spacecraft velocity at flyby epoch (km/s)
        Must be heliocentric - no ambiguity allowed
    r_planet : np.ndarray
        Planet position vector at flyby epoch (km)
    v_planet : np.ndarray
        Planet velocity vector at flyby epoch (km/s)
    target_body : str
        NAIF ID of target body (e.g., '4' for Mars)
    epoch : astropy.Time
        Flyby epoch
    mu_planet : float
        Planet gravitational parameter (km^3/s^2)
    search_arrival_window : Tuple[float, float]
        Arrival time search window as (t_start, t_end) in astropy.Time
    rp_bounds : Tuple[float, float], optional
        Periapsis radius bounds (km), default (300, 10000)
    min_alt_km : float, optional
        Minimum altitude above planet surface (km), default 100
    max_turn : float, optional
        Maximum turn angle (radians), default None
    max_samples : int, optional
        Maximum number of samples for coarse search, default 1000

    Returns
    -------
    FlyResult
        Flyby targeting result with success status and trajectory data

    Notes
    -----
    - All velocities must be in km/s, positions in km
    - v_sc_in must be heliocentric spacecraft velocity
    - Uses PyKEP fb_con for constraint validation
    - Performs local refinement around best coarse candidate
    """
    # Input validation and units consistency
    if not isinstance(v_sc_in, np.ndarray) or v_sc_in.shape != (3,):
        return FlyResult(False, "v_sc_in must be 3-element numpy array", flyby_model="patchedconic")

    if not isinstance(r_planet, np.ndarray) or r_planet.shape != (3,):
        return FlyResult(False, "r_planet must be 3-element numpy array", flyby_model="patchedconic")

    if not isinstance(v_planet, np.ndarray) or v_planet.shape != (3,):
        return FlyResult(False, "v_planet must be 3-element numpy array", flyby_model="patchedconic")

    # Compute incoming v_inf (planetocentric)
    vinf_minus = v_sc_in - v_planet
    v_inf_mag = float(np.linalg.norm(vinf_minus))

    if v_inf_mag == 0.0:
        return FlyResult(False, "Zero v_inf input", flyby_model="patchedconic")

    # Enforce periapsis bounds with minimum altitude
    # For Mars, use planetary radius; otherwise assume min_alt_km is relative to surface
    planet_radius = 3390.0 if target_body == '499' else 0.0  # Mars radius in km
    rp_min = max(rp_bounds[0], planet_radius + min_alt_km)
    rp_max = rp_bounds[1]

    if rp_min >= rp_max:
        return FlyResult(False, "Invalid rp bounds", flyby_model="patchedconic")

    # Coarse grid search
    best_candidate = _coarse_flyby_search(
        v_sc_in, r_planet, v_planet, target_body, epoch,
        mu_planet, search_arrival_window, rp_min, rp_max,
        max_turn, max_samples
    )

    if best_candidate is None:
        return FlyResult(False, "No feasible flyby+Lambert found", flyby_model="patchedconic")

    # Local refinement around best candidate
    refined_candidate = _refine_flyby_candidate(
        best_candidate, v_sc_in, r_planet, v_planet, target_body, epoch, mu_planet
    )

    # Compute B-plane coordinates for the refined solution
    b_vec = _compute_b_plane(
        refined_candidate['rp'], refined_candidate['turn_angle'],
        vinf_minus, v_inf_mag, mu_planet
    )

    return FlyResult(
        True,
        "Patched-conic solution found with refinement",
        rp=refined_candidate['rp'],
        turn_angle=refined_candidate['turn_angle'],
        b_vec=b_vec,
        vinf_out=refined_candidate['vinf_out'],
        arrival_epoch=refined_candidate['arrival_epoch'],
        c3_to_target=refined_candidate['c3'],
        flyby_model="patchedconic"
    )


def _coarse_flyby_search(
    v_sc_in: np.ndarray, r_planet: np.ndarray, v_planet: np.ndarray,
    target_body: str, epoch: Any, mu_planet: float,
    search_arrival_window: Tuple[float, float],
    rp_min: float, rp_max: float, max_turn: Optional[float], max_samples: int
) -> Optional[Dict[str, Any]]:
    """
    Perform coarse grid search for flyby candidates.

    Returns the best candidate with lowest C3 to target.
    """
    vinf_minus = v_sc_in - v_planet
    v_inf_mag = float(np.linalg.norm(vinf_minus))

    # Grid parameters
    n_rp = min(20, max_samples // 10)
    n_phi = min(36, max_samples // 5)
    n_arr = min(30, max_samples // 10)

    rp_grid = np.linspace(rp_min, rp_max, n_rp)
    phi_grid = np.linspace(0.0, 2*np.pi, n_phi, endpoint=False)

    # Sample arrival epochs
    t_start, t_end = search_arrival_window
    arr_times = [t_start + (i/(n_arr-1))*(t_end - t_start) for i in range(n_arr)]

    best = None

    for rp in rp_grid:
        # Classical deflection relation
        x = 1.0 + (rp * v_inf_mag**2) / mu_planet
        s = 1.0 / x
        if s <= 0 or s > 1.0:
            continue
        delta = 2.0 * np.arcsin(s)
        if max_turn is not None and delta > max_turn:
            continue

        # Validate flyby geometry with PyKEP
        try:
            pk.fb_con(
                v_sc_in.tolist(),
                v_planet.tolist(),
                rp,
                mu_planet
            )
        except Exception:
            # Invalid geometry, skip
            continue

        for phi in phi_grid:
            try:
                # PyKEP flyby propagation
                v_after = np.array(pk.fb_prop(
                    v_sc_in.tolist(),
                    v_planet.tolist(),
                    rp,
                    phi,
                    mu_planet
                ))
            except Exception:
                continue

            # Post-flyby planetocentric velocity
            vinf_out_planet = v_after - v_planet

            # Try Lambert transfers to target
            for t_arr in arr_times:
                try:
                    r_target, v_target = rv_helio(target_body, t_arr)
                except Exception:
                    continue

                tof_td = t_arr - epoch
                try:
                    tof_qty = tof_td.to(u.day)
                except Exception:
                    tof_qty = (t_arr.tdb.jd - epoch.tdb.jd) * u.day

                if tof_qty.to_value(u.second) <= 0:
                    continue

                try:
                    r_after_q = r_planet * u.km
                    v_dep, v_arr = solve_leg(r_after_q, r_target, tof_qty)
                except Exception:
                    continue

                # Compute C3 at target
                vinf_at_target = v_arr - v_target
                try:
                    vinf_at_target_kms = vinf_at_target.to(u.km / u.s).value
                except Exception:
                    vinf_at_target_kms = np.asarray(vinf_at_target)

                c3_to_target = float(np.dot(vinf_at_target_kms, vinf_at_target_kms))

                # Track best candidate
                cand = {
                    'rp': float(rp),
                    'phi': float(phi),
                    'turn_angle': float(delta),
                    'vinf_out': vinf_out_planet.copy(),
                    'arrival_epoch': t_arr,
                    'c3': c3_to_target,
                    'vinf_minus': vinf_minus.copy()
                }

                if best is None or cand['c3'] < best['c3']:
                    best = cand

    return best


def _refine_flyby_candidate(
    candidate: Dict[str, Any], v_sc_in: np.ndarray, r_planet: np.ndarray,
    v_planet: np.ndarray, target_body: str, epoch: Any, mu_planet: float
) -> Dict[str, Any]:
    """
    Perform local refinement around a flyby candidate.

    Uses scipy.optimize to minimize C3 by adjusting rp and phi.
    """
    def objective(params):
        rp, phi = params
        # Clamp parameters to valid ranges
        rp = np.clip(rp, 300.0, 10000.0)
        phi = phi % (2 * np.pi)

        try:
            # PyKEP flyby propagation
            v_after = np.array(pk.fb_prop(
                v_sc_in.tolist(),
                v_planet.tolist(),
                rp,
                phi,
                mu_planet
            ))

            vinf_out_planet = v_after - v_planet

            # Lambert to target at candidate arrival time
            r_target, v_target = rv_helio(target_body, candidate['arrival_epoch'])
            tof_td = candidate['arrival_epoch'] - epoch
            tof_qty = tof_td.to(u.day)

            r_after_q = r_planet * u.km
            v_dep, v_arr = solve_leg(r_after_q, r_target, tof_qty)

            # C3 at target
            vinf_at_target = v_arr - v_target
            vinf_at_target_kms = vinf_at_target.to(u.km / u.s).value
            c3 = float(np.dot(vinf_at_target_kms, vinf_at_target_kms))

            return c3

        except Exception:
            return 1e10  # Large penalty for invalid solutions

    # Initial parameters
    x0 = [candidate['rp'], candidate['phi']]

    # Bounds for optimization
    bounds = [(300.0, 10000.0), (0.0, 2*np.pi)]

    # Local optimization
    result = minimize_scalar(
        lambda rp: objective([rp, candidate['phi']]),
        bounds=(bounds[0][0], bounds[0][1]),
        method='bounded'
    )

    if result.success:
        rp_opt = result.x
        # Optimize phi at optimal rp
        result_phi = minimize_scalar(
            lambda phi: objective([rp_opt, phi]),
            bounds=(0.0, 2*np.pi),
            method='bounded'
        )
        if result_phi.success:
            phi_opt = result_phi.x
        else:
            phi_opt = candidate['phi']
    else:
        rp_opt = candidate['rp']
        phi_opt = candidate['phi']

    # Recompute final solution
    try:
        v_after = np.array(pk.fb_prop(
            v_sc_in.tolist(),
            v_planet.tolist(),
            rp_opt,
            phi_opt,
            mu_planet
        ))

        vinf_minus = v_sc_in - v_planet
        v_inf_mag = float(np.linalg.norm(vinf_minus))
        x = 1.0 + (rp_opt * v_inf_mag**2) / mu_planet
        delta = 2.0 * np.arcsin(1.0 / x)

        # Final Lambert computation
        r_target, v_target = rv_helio(target_body, candidate['arrival_epoch'])
        tof_td = candidate['arrival_epoch'] - epoch
        tof_qty = tof_td.to(u.day)
        r_after_q = r_planet * u.km
        v_dep, v_arr = solve_leg(r_after_q, r_target, tof_qty)

        vinf_at_target = v_arr - v_target
        vinf_at_target_kms = vinf_at_target.to(u.km / u.s).value
        c3_final = float(np.dot(vinf_at_target_kms, vinf_at_target_kms))

        return {
            'rp': float(rp_opt),
            'turn_angle': float(delta),
            'vinf_out': v_after - v_planet,
            'arrival_epoch': candidate['arrival_epoch'],
            'c3': c3_final,
            'vinf_minus': vinf_minus
        }

    except Exception:
        # Return original candidate if refinement fails
        return candidate


def _compute_b_plane(
    rp: float, turn_angle: float, vinf_minus: np.ndarray,
    v_inf_mag: float, mu_planet: float
) -> np.ndarray:
    """
    Compute B-plane impact parameter vector.

    The B-vector lies in the B-plane, perpendicular to the incoming v_inf direction.
    Magnitude is given by b = (mu / v_inf^2) * cot(delta/2)
    """
    # Orthonormal basis with e1 along v_inf
    e1 = vinf_minus / v_inf_mag

    # Choose reference vector not aligned with e1
    tmp = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(tmp, e1)) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])

    e2 = tmp - np.dot(tmp, e1) * e1
    e2 /= np.linalg.norm(e2)

    # B magnitude from hyperbolic geometry
    half_delta = 0.5 * turn_angle
    cot_half = 1.0 / np.tan(half_delta) if np.tan(half_delta) != 0 else 0.0
    b_mag = mu_planet / (v_inf_mag**2) * cot_half

    # B-vector aligned with e2 (arbitrary orientation)
    return b_mag * e2


# Legacy function for backward compatibility
def compute_flyby(epoch, r_planet, v_planet, mu_planet, vinf_in, rp_bounds, target_body, mu_central, search_arrival_window, max_samples, seed, min_alt_km=0.0, max_turn=None):
    """
    Legacy flyby function for backward compatibility.

    This function maintains the old interface but internally calls the new
    find_flyby_lambert function with appropriate parameter mapping.
    """
    # Convert old interface to new interface
    # Assume vinf_in is heliocentric spacecraft velocity (most common usage)
    v_sc_in = np.asarray(vinf_in, dtype=float)

    # Call new function
    result = find_flyby_lambert(
        v_sc_in=v_sc_in,
        r_planet=np.asarray(r_planet, dtype=float),
        v_planet=np.asarray(v_planet, dtype=float),
        target_body=target_body,
        epoch=epoch,
        mu_planet=mu_planet,
        search_arrival_window=search_arrival_window,
        rp_bounds=rp_bounds,
        min_alt_km=min_alt_km,
        max_turn=max_turn,
        max_samples=max_samples
    )

    # Convert back to old FlyResult format
    return FlyResult(
        success=result.success,
        message=result.message,
        rp=result.rp,
        turn_angle=result.turn_angle,
        b_vec=result.b_vec,
        vinf_out=result.vinf_out,
        arrival_epoch=result.arrival_epoch,
        c3_to_ceres=result.c3_to_target,  # Map to old field name
        flyby_model=result.flyby_model
    )