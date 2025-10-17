"""Generic transfer requirements computation for flyby trajectories.

This module provides functions to compute the required outbound velocity (v∞) at an 
intermediate body needed to reach a final destination body. This is critical for:

1. **Gravity Assist Design**: After a flyby at an intermediate planet, determine what
   outbound v∞ is needed to reach the next target with a given time-of-flight.

2. **Trajectory Screening**: Screen multiple departure/arrival time combinations to find
   feasible opportunities that satisfy mission constraints (e.g., C3 limits, arrival windows).

3. **Multi-Body Chain Planning**: Build up complex trajectories by computing requirements
   for each leg in sequence (e.g., Earth→Mars requires X v∞, Mars→Ceres requires Y v∞).

Key Concepts:
- **v∞ (v-infinity)**: The spacecraft's velocity relative to a body, far from its gravity well
- **C3**: The characteristic energy (v∞²), commonly used as a mission constraint
- **Lambert Problem**: Given two positions and a transfer time, solve for the required velocities

Usage Example:
    >>> from astropy.time import Time
    >>> # Compute what v∞ is needed leaving Mars on 2025-06-01 to reach Ceres on 2026-01-01
    >>> result = eval_transfer_requirement(
    ...     t_intermediate="2025-06-01",
    ...     t_final="2026-01-01", 
    ...     intermediate_body="499",  # Mars
    ...     final_body="20000001"     # Ceres
    ... )
    >>> print(f"Required v∞: {result['vinf_req_mag']:.2f} km/s")
    >>> print(f"C3: {result['vinf_req_mag']**2:.2f} km²/s²")
"""

from __future__ import annotations

import numpy as np
from astropy.time import Time
from astropy import units as u
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List
import logging

from ..core.spice_io import rv_helio_spice, _to_time


def eval_transfer_requirement(t_intermediate: str | Time, t_final: str | Time, 
                             intermediate_body: str, final_body: str) -> dict:
    """
    Compute required outbound v∞ at intermediate body for intermediate→final transfer.
    
    Args:
        t_intermediate: Time at intermediate body encounter
        t_final: Time at final body encounter  
        intermediate_body: NAIF ID of intermediate body
        final_body: NAIF ID of final body
        
    Returns dict with:
    - vinf_req_x/y/z: required v∞ components (km/s) in heliocentric frame
    - vinf_req_mag: magnitude of required v∞ (km/s)  
    - tof_d: time of flight from intermediate to final (days)
    - intermediate_iso: intermediate body encounter time
    - final_iso: final body encounter time
    - intermediate_body: intermediate body NAIF ID
    - final_body: final body NAIF ID
    """
    t_intermediate = _to_time(t_intermediate)
    t_final = _to_time(t_final)
    
    if t_final <= t_intermediate:
        raise ValueError(f"Final body time {t_final.isot} must be after intermediate body time {t_intermediate.isot}")
    
    # Get heliocentric states
    r_intermediate, v_intermediate = rv_helio_spice(intermediate_body, t_intermediate)
    r_final, v_final = rv_helio_spice(final_body, t_final)
    
    # Time of flight
    tof = t_final - t_intermediate
    tof_days = tof.to_value(u.day)
    
    # Solve Lambert problem: intermediate position -> final position
    # This gives us the velocity intermediate would need to have at t_intermediate to reach final at t_final
    from ..core.lambert_io import best_lambert_branch
    
    res = best_lambert_branch(
        r_intermediate, v_intermediate, r_final, tof
    )
    
    if res is None:
        raise RuntimeError(f"No Lambert solution found for {intermediate_body} to {final_body} transfer from {t_intermediate.isot} to {t_final.isot} (TOF: {tof_days:.1f} days)")
    
    min_c3, v_dep_required, v_arr_required, used = res
    
    # Required v∞ is the difference between required departure velocity and actual intermediate velocity
    vinf_req = v_dep_required - v_intermediate
    vinf_req_mag = np.linalg.norm(vinf_req)
    
    return {
        'vinf_req_x': vinf_req[0],
        'vinf_req_y': vinf_req[1], 
        'vinf_req_z': vinf_req[2],
        'vinf_req_mag': vinf_req_mag,
        'tof_d': tof_days,
        'intermediate_iso': t_intermediate.isot,
        'final_iso': t_final.isot,
        'intermediate_body': intermediate_body,
        'final_body': final_body
    }


def eval_transfer_requirements_batch(intermediate_times: List[Time], final_times: List[Time],
                                    intermediate_body: str, final_body: str,
                                    n_workers: int | None = None) -> List[dict]:
    """
    Compute transfer requirements for a batch of time pairs in parallel.
    
    Args:
        intermediate_times: List of times at intermediate body
        final_times: List of times at final body
        intermediate_body: NAIF ID of intermediate body
        final_body: NAIF ID of final body
        n_workers: Number of worker processes (None = CPU count)
        
    Returns list of requirement dictionaries
    """
    if n_workers is None or n_workers == 0:
        n_workers = mp.cpu_count()
    
    results = []
    
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all pairs
        futures = {}
        for intermediate_t in intermediate_times:
            for final_t in final_times:
                if final_t <= intermediate_t:
                    continue
                future = executor.submit(eval_transfer_requirement, intermediate_t, final_t, intermediate_body, final_body)
                futures[future] = (intermediate_t, final_t)
        
        # Collect results
        for future in as_completed(futures):
            intermediate_t, final_t = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.exception('Failed for %s %s, %s %s: %s', intermediate_body, intermediate_t.isot, final_body, final_t.isot, e)
                # Add failed result with NaN values
                results.append({
                    'vinf_req_x': np.nan, 'vinf_req_y': np.nan, 'vinf_req_z': np.nan,
                    'vinf_req_mag': np.nan, 'tof_d': np.nan,
                    'intermediate_iso': intermediate_t.isot, 'final_iso': final_t.isot,
                    'intermediate_body': intermediate_body, 'final_body': final_body
                })
    
    return results