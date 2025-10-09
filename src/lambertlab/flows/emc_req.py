"""Mars-Ceres requirement computation for flyby trajectories."""

from __future__ import annotations

import numpy as np
from astropy.time import Time
from astropy import units as u
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from ..core.spice_io import rv_helio_spice, _to_time
from ..core.lambert_io import best_lambert_branch
from ..core.types import MARS_ID, CERES_ID


def eval_mc_requirement(t_mars: str | Time, t_ceres: str | Time) -> dict:
    """
    Compute required outbound v∞ at Mars for Mars→Ceres transfer.
    
    Returns dict with:
    - vinf_req_x/y/z: required v∞ components (km/s) in heliocentric frame
    - vinf_req_mag: magnitude of required v∞ (km/s)  
    - tof2_d: time of flight from Mars to Ceres (days)
    - mars_iso: Mars encounter time
    - ceres_iso: Ceres encounter time
    """
    t_mars = _to_time(t_mars)
    t_ceres = _to_time(t_ceres)
    
    if t_ceres <= t_mars:
        raise ValueError(f"Ceres time {t_ceres.isot} must be after Mars time {t_mars.isot}")
    
    # Get heliocentric states
    r_mars, v_mars = rv_helio_spice(MARS_ID, t_mars)
    r_ceres, v_ceres = rv_helio_spice(CERES_ID, t_ceres)
    
    # Time of flight
    tof = t_ceres - t_mars
    tof_days = tof.to_value(u.day)
    
    # Solve Lambert problem: Mars position -> Ceres position
    # This gives us the velocity Mars would need to have at t_mars to reach Ceres at t_ceres
    res = best_lambert_branch(
        r_mars, v_mars, r_ceres, v_ceres, tof,
        rtol=1e-10, prograde=None, lowpath=None
    )
    
    if res is None:
        raise RuntimeError(f"No Lambert solution found for Mars to Ceres transfer from {t_mars.isot} to {t_ceres.isot} (TOF: {tof_days:.1f} days)")
    
    min_c3, v_dep_required, v_arr_required, used = res
    
    # Required v∞ is the difference between required departure velocity and actual Mars velocity
    vinf_req = v_dep_required - v_mars
    vinf_req_mag = np.linalg.norm(vinf_req)
    
    return {
        'vinf_req_x': vinf_req[0],
        'vinf_req_y': vinf_req[1], 
        'vinf_req_z': vinf_req[2],
        'vinf_req_mag': vinf_req_mag,
        'tof2_d': tof_days,
        'mars_iso': t_mars.isot,
        'ceres_iso': t_ceres.isot
    }


def eval_mc_requirements_batch(mars_times: List[Time], ceres_times: List[Time], 
                              n_workers: int | None = None) -> List[dict]:
    """Compute Mars-Ceres requirements for a batch of time pairs in parallel."""
    if n_workers is None or n_workers == 0:
        n_workers = mp.cpu_count()
    
    results = []
    
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all pairs
        futures = {}
        for mars_t in mars_times:
            for ceres_t in ceres_times:
                if ceres_t <= mars_t:
                    continue
                future = executor.submit(eval_mc_requirement, mars_t, ceres_t)
                futures[future] = (mars_t, ceres_t)
        
        # Collect results
        for future in as_completed(futures):
            mars_t, ceres_t = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Failed for Mars {mars_t.isot}, Ceres {ceres_t.isot}: {e}")
                # Add failed result with NaN values
                results.append({
                    'vinf_req_x': np.nan, 'vinf_req_y': np.nan, 'vinf_req_z': np.nan,
                    'vinf_req_mag': np.nan, 'tof2_d': np.nan,
                    'mars_iso': mars_t.isot, 'ceres_iso': ceres_t.isot
                })
    
    return results