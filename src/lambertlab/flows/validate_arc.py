"""Validation of Earth-Mars-Ceres trajectories via two-body propagation."""

from __future__ import annotations

import numpy as np
from astropy.time import Time
from astropy import units as units
import spiceypy as spice

try:
    from poliastro.twobody import Orbit
    from poliastro.bodies import Sun
    POLIASTRO_AVAILABLE = True
except ImportError:
    POLIASTRO_AVAILABLE = False

from ..core.config import MU_SUN


def validate_trajectory(em_row: dict, mc_row: dict) -> dict:
    """Validate a trajectory by propagating from Mars to Ceres under two-body dynamics.

    Args:
        em_row: Row from em_porkchop.csv with Mars state data
        mc_row: Row from mc_req.csv with Ceres requirements

    Returns:
        dict with validation results:
        - min_distance_km: Minimum distance to Ceres during propagation
        - arrival_distance_km: Distance at nominal arrival time
        - propagation_ok: Whether propagation succeeded
        - error_msg: Error message if propagation failed
    """
    if not POLIASTRO_AVAILABLE:
        return {
            'min_distance_km': np.nan,
            'arrival_distance_km': np.nan,
            'propagation_ok': False,
            'error_msg': 'poliastro not available'
        }

    try:
        # Parse times
        mars_iso = em_row['mars_iso']
        ceres_iso = mc_row['ceres_iso']
        t_mars = Time(mars_iso)
        t_ceres = Time(ceres_iso)

        # Get Mars state
        r_mars_vec = np.array([
            float(em_row['rM_x']),
            float(em_row['rM_y']),
            float(em_row['rM_z'])
        ])
        v_mars_vec = np.array([
            float(em_row['vM_x']),
            float(em_row['vM_y']),
            float(em_row['vM_z'])
        ])

        # Get incoming v_inf (relative to Mars)
        vinf_in_vec = np.array([
            float(em_row['vinf_in_x']),
            float(em_row['vinf_in_y']),
            float(em_row['vinf_in_z'])
        ])

        # Compute spacecraft heliocentric velocity at Mars arrival
        # v_sc_helio = v_mars + v_inf_relative_to_mars
        v_sc_mars_arr_helio = v_mars_vec + vinf_in_vec

        # For this basic validation, assume no flyby change (ballistic case)
        # In full implementation, we'd apply the flyby delta-V
        v_sc_dep_helio = v_sc_mars_arr_helio

        # Create poliastro orbit at Mars
        r_mars = r_mars_vec * units.km
        v_sc = v_sc_dep_helio * units.km / units.s

        orbit = Orbit.from_vectors(Sun, r_mars, v_sc, epoch=t_mars)

        # Propagate to Ceres arrival time
        dt_to_ceres = t_ceres - t_mars
        orbit_ceres = orbit.propagate(dt_to_ceres)

        # Get propagated position
        r_sc_ceres = orbit_ceres.r.to(units.km).value

        # Get Ceres position from SPICE
        et_ceres = spice.str2et(ceres_iso)
        r_ceres_state, _ = spice.spkpos('20000001', et_ceres, 'ECLIPJ2000', 'NONE', 'SUN')
        r_ceres = np.array(r_ceres_state)  # SPICE returns km

        # Calculate distance at arrival
        arrival_distance_km = np.linalg.norm(r_sc_ceres - r_ceres)

        # For minimum distance, sample the trajectory coarsely
        dt_days = (t_ceres - t_mars).to_value(units.day)
        n_samples = 20
        dt_samples = np.linspace(0, dt_days, n_samples) * units.day

        min_distance_km = float('inf')
        for dt in dt_samples[1:-1]:  # Skip start and end points
            try:
                orbit_t = orbit.propagate(dt)
                r_sc_t = orbit_t.r.to(units.km).value

                # Calculate time for SPICE
                t_current = t_mars + dt
                et_t = spice.str2et(t_current.iso)
                r_target_state, _ = spice.spkpos('20000001', et_t, 'ECLIPJ2000', 'NONE', 'SUN')
                r_target = np.array(r_target_state)

                distance_km = np.linalg.norm(r_sc_t - r_target)
                min_distance_km = min(min_distance_km, distance_km)
            except Exception:
                continue

        return {
            'min_distance_km': min_distance_km,
            'arrival_distance_km': arrival_distance_km,
            'propagation_ok': True,
            'error_msg': None
        }

    except Exception as e:
        return {
            'min_distance_km': np.nan,
            'arrival_distance_km': np.nan,
            'propagation_ok': False,
            'error_msg': str(e)
        }


def validate_emc_candidates(em_csv: str = 'em_porkchop.csv', mc_csv: str = 'mc_req.csv',
                           n_candidates: int = 5) -> None:
    """Validate top EMC candidates by propagation.

    Args:
        em_csv: Path to Earth-Mars porkchop CSV
        mc_csv: Path to Mars-Ceres requirements CSV
        n_candidates: Number of best candidates to validate
    """
    import csv
    from collections import defaultdict

    # Read EM data: mars_iso -> list of rows
    em_data = defaultdict(list)
    with open(em_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mars_iso = row['mars_iso']
            em_data[mars_iso].append(row)

    # Read MC data: mars_iso -> list of rows
    mc_data = defaultdict(list)
    with open(mc_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mars_iso = row['mars_iso']
            mc_data[mars_iso].append(row)

    # Find candidates that exist in both datasets
    candidates = []
    for mars_iso in set(em_data.keys()) & set(mc_data.keys()):
        for em_row in em_data[mars_iso]:
            for mc_row in mc_data[mars_iso]:
                candidates.append((em_row, mc_row))

    print(f"Validating {min(n_candidates, len(candidates))} EMC candidates:")
    print("=" * 80)

    for i, (em_row, mc_row) in enumerate(candidates[:n_candidates]):
        result = validate_trajectory(em_row, mc_row)

        dep_iso = em_row['dep_iso']
        mars_iso = em_row['mars_iso']
        ceres_iso = mc_row['ceres_iso']

        print(f"\nCandidate {i+1}: {dep_iso} -> {mars_iso} -> {ceres_iso}")
        if result['propagation_ok']:
            print(".1f")
            print(".1f")
        else:
            print(f"  Propagation failed: {result['error_msg']}")


if __name__ == '__main__':
    validate_emc_candidates()