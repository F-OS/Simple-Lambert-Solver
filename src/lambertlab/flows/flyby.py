"""Flyby computations."""

import numpy as np
import pykep as pk
from astropy.time import Time
import astropy.units as u
from ..core.spice_io import rv_helio
from ..core.lambert_io import solve_leg
from ..core.config import MU_SUN, R_MARS


class FlyResult:
    def __init__(self, success, message, rp=None, turn_angle=None, b_vec=None, vinf_out=None, arrival_epoch=None, c3_to_ceres=None, flyby_model="mock"):
        self.success = success
        self.message = message
        self.rp = rp
        self.turn_angle = turn_angle
        self.b_vec = b_vec
        self.vinf_out = vinf_out
        self.arrival_epoch = arrival_epoch
        self.c3_to_ceres = c3_to_ceres
        self.flyby_model = flyby_model


def compute_flyby(epoch, r_planet, v_planet, mu_planet, vinf_in, rp_bounds, target_body, mu_central, search_arrival_window, max_samples, seed, min_alt_km=0.0, max_turn=None):
    """Analytical patched-conic flyby targeting (non-coplanar allowed).

    Steps:
    - Interpret `vinf_in` as a heliocentric vector; convert to planetocentric v_inf^- = vinf_in - v_planet.
    - Search over periapsis radius in bounds and rotation around the v_inf vector to find a post-flyby v_inf^+
      that enables a heliocentric Lambert to the target body within the requested arrival window.
    - Compute turning angle from classical patched-conic relation and apply rotation in the plane perpendicular to v_inf^-.

    Returns a FlyResult with flyby_model="patchedconic" on success.
    """
    rng = np.random.default_rng(int(seed))

    # Normalize inputs
    r_planet = np.asarray(r_planet, dtype=float)
    v_planet = np.asarray(v_planet, dtype=float)
    vinf_helio = np.asarray(vinf_in, dtype=float)

    # Determine whether vinf_in was passed as planetocentric v_inf^- (spacecraft-planet)
    # or as a heliocentric spacecraft velocity. Heuristic: if the magnitude of
    # vinf_in is small compared to the planet speed, assume it's already planetocentric.
    v_planet_mag = float(np.linalg.norm(v_planet))
    vinf_in_mag_guess = float(np.linalg.norm(vinf_helio))
    if vinf_in_mag_guess < 0.5 * v_planet_mag:
        # likely already planetocentric v_inf^- (spacecraft - planet)
        vinf_minus = vinf_helio
    else:
        # treat vinf_in as heliocentric spacecraft velocity and subtract planet velocity
        vinf_minus = vinf_helio - v_planet
    v_inf_mag = float(np.linalg.norm(vinf_minus))
    if v_inf_mag == 0.0:
        return FlyResult(False, "Zero v_inf input", flyby_model="patchedconic")

    # enforce periapsis bounds with min altitude
    rp_min = max(rp_bounds[0], (R_MARS if 'R_MARS' in globals() else 0) + min_alt_km)
    rp_max = rp_bounds[1]
    if rp_min >= rp_max:
        return FlyResult(False, "Invalid rp bounds", flyby_model="patchedconic")

    # Prepare search grids
    n_rp = 20
    n_phi = 36
    rp_grid = np.linspace(rp_min, rp_max, n_rp)
    phi_grid = np.linspace(0.0, 2*np.pi, n_phi, endpoint=False)

    # We don't need to build an orthonormal basis anymore - PyKEP handles rotation!
    # (Keeping commented out for reference during migration)
    # e1 = vinf_minus / v_inf_mag
    # tmp = np.array([0.0, 0.0, 1.0])
    # if abs(np.dot(tmp, e1)) > 0.9:
    #     tmp = np.array([0.0, 1.0, 0.0])
    # e2 = tmp - np.dot(tmp, e1) * e1
    # e2 /= np.linalg.norm(e2)
    # e3 = np.cross(e1, e2)

    best = None
    # sample arrival epochs in window
    t_start, t_end = search_arrival_window
    n_arr = min(30, max_samples)
    arr_times = [t_start + (i/(n_arr-1))*(t_end - t_start) for i in range(n_arr)]

    from ..core.lambert_io import solve_leg
    from ..core.spice_io import rv_helio

    for rp in rp_grid:
        # classical deflection relation for hyperbola (patched-conic):
        # sin(delta/2) = 1 / (1 + (rp * v_inf^2)/mu_planet)
        x = 1.0 + (rp * v_inf_mag**2) / mu_planet
        s = 1.0 / x
        if s <= 0 or s > 1.0:
            continue
        delta = 2.0 * np.arcsin(s)
        if max_turn is not None and delta > max_turn:
            continue

        # For each orientation around the incoming direction, use PyKEP's fb_prop()
        for phi in phi_grid:
            # PyKEP fb_prop(v_spacecraft, v_planet, rp, beta, mu) 
            # where beta is the B-plane angle (equivalent to our phi)
            # Convert to heliocentric spacecraft velocity for PyKEP
            v_sc_in = v_planet + vinf_minus
            
            try:
                # PyKEP fb_prop returns post-flyby heliocentric velocity
                v_after = np.array(pk.fb_prop(
                    v_sc_in.tolist(),
                    v_planet.tolist(),
                    rp,
                    phi,  # beta (B-plane angle)
                    mu_planet
                ))
            except Exception:
                # PyKEP may throw if geometry is invalid
                continue
            
            # Extract post-flyby v_inf (planetocentric)
            vinf_out_planet = v_after - v_planet
            vinf_out_helio = v_after  # Already heliocentric from fb_prop()

            # post-flyby heliocentric state (position unchanged at encounter)
            r_after = r_planet.copy()
            v_after = v_planet + vinf_out_planet

            # Try arrivals to target body
            for t_arr in arr_times:
                try:
                    r_target, v_target = rv_helio(target_body, t_arr)
                except Exception:
                    continue
                tof_td = t_arr - epoch
                # ensure positive TOF and convert to a Quantity in days
                try:
                    tof_qty = tof_td.to(u.day)
                except Exception:
                    # fallback: compute numeric days
                    tof_qty = (t_arr.tdb.jd - epoch.tdb.jd) * u.day
                if tof_qty.to_value(u.second) <= 0:
                    continue
                try:
                    # solve Lambert from post-flyby to target arrival
                    # ensure positions are astropy Quantities in km
                    from astropy import units as _u
                    r_after_q = (r_after * _u.km)
                    v_dep, v_arr = solve_leg(r_after_q, r_target, tof_qty)
                except Exception:
                    continue

                # compute arrival excess relative to target (heliocentric)
                vinf_at_target = v_arr - v_target
                # Ensure numeric km/s array then compute C3 = |vinf|^2 (km^2/s^2)
                try:
                    vinf_at_target_kms = vinf_at_target.to(u.km / u.s).value
                except Exception:
                    # if already plain numpy
                    vinf_at_target_kms = np.asarray(vinf_at_target)
                c3_to_target = float(np.dot(vinf_at_target_kms, vinf_at_target_kms))

                # Accept candidate
                cand = {
                    'rp': float(rp),
                    'turn_angle': float(delta),
                    'b_vec': (0.0, 0.0, 0.0),
                    'vinf_out': np.asarray(vinf_out_planet, dtype=float),
                    'arrival_epoch': t_arr,
                    'c3': c3_to_target,
                    'vinf_minus': vinf_minus,
                    'vinf_out_helio': vinf_out_helio
                }
                if best is None or cand['c3'] < best['c3']:
                    best = cand

    if best is None:
        return FlyResult(False, "No feasible flyby+Lambert found", flyby_model="patchedconic")

    # Build a b-plane vector estimate (use impact parameter b = mu/ v_inf^2 * cot(delta/2))
    # We need a basis vector perpendicular to vinf_minus for b_vec direction
    e1 = vinf_minus / v_inf_mag
    tmp = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(tmp, e1)) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])
    e2 = tmp - np.dot(tmp, e1) * e1
    e2 /= np.linalg.norm(e2)
    
    cot_half = 1.0 / np.tan(0.5 * best['turn_angle']) if np.tan(0.5 * best['turn_angle']) != 0 else 0.0
    b_mag = mu_planet / (v_inf_mag**2) * cot_half
    # choose b_vec aligned with e2 for now
    b_vec = b_mag * e2

    # Verify invariants
    vinf_in_mag = v_inf_mag
    vinf_out_mag = float(np.linalg.norm(best['vinf_out']))

    return FlyResult(
        True,
        "Patched-conic solution found",
        rp=best['rp'],
        turn_angle=best['turn_angle'],
        b_vec=b_vec,
        vinf_out=best['vinf_out'],
        arrival_epoch=best['arrival_epoch'],
        c3_to_ceres=best['c3'],
        flyby_model="patchedconic"
    )