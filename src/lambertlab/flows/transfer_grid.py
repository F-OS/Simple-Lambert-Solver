"""Generic transfer grid computation for any departure→arrival body pair."""

from __future__ import annotations

from typing import List, Tuple, Iterator
import numpy as np
from astropy.time import Time
from astropy import units as u
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

from ..core.spice_io import load_kernels, rv_helio_spice, _to_time, StateCache, ensure_spice_loaded, _pool_initializer
from ..core.lambert_io import best_lambert_branch, c3
from ..core.config import AU


def _compute_grid_chunk(dep_times: List[Time], tof_days: np.ndarray, 
                       dep_body: str, arr_body: str, use_mp: bool, n_workers: int, 
                       kernel_paths: List[str] | None = None, use_threads: bool = False) -> dict:
    """Compute grid chunk, either serially or in parallel."""
    n_dep = len(dep_times)
    n_tof = len(tof_days)
    
    # Initialize result arrays
    c3_grid = np.full((n_dep, n_tof), np.nan)
    vinf_out_x = np.full((n_dep, n_tof), np.nan)
    vinf_out_y = np.full((n_dep, n_tof), np.nan)
    vinf_out_z = np.full((n_dep, n_tof), np.nan)
    vinf_in_x = np.full((n_dep, n_tof), np.nan)
    vinf_in_y = np.full((n_dep, n_tof), np.nan)
    vinf_in_z = np.full((n_dep, n_tof), np.nan)
    v_arr_x = np.full((n_dep, n_tof), np.nan)
    v_arr_y = np.full((n_dep, n_tof), np.nan)
    v_arr_z = np.full((n_dep, n_tof), np.nan)
    r_arr_x = np.full((n_dep, n_tof), np.nan)
    r_arr_y = np.full((n_dep, n_tof), np.nan)
    r_arr_z = np.full((n_dep, n_tof), np.nan)

    if use_mp:
        # Parallel computation
        logger = logging.getLogger(__name__)
        logger.info('Computing grid using %d workers...', n_workers)
        
        # Create shared cache (this is tricky with multiprocessing, so we'll create per-worker caches)
        # For now, each worker will create its own cache
        
        if use_threads:
            from concurrent.futures import ThreadPoolExecutor
            executor_class = ThreadPoolExecutor
            executor_kwargs = {"max_workers": n_workers}
        else:
            executor_class = ProcessPoolExecutor
            executor_kwargs = {
                "max_workers": n_workers,
                "initializer": _pool_initializer,
                "initargs": (kernel_paths or [],),
            }
        
        with executor_class(**executor_kwargs) as executor:
            # Submit jobs for each departure time
            futures = {}
            for i, dep in enumerate(dep_times):
                future = executor.submit(_compute_dep_row, dep, tof_days, dep_body, arr_body)
                futures[future] = i
            
            # Collect results
            for future in as_completed(futures):
                i = futures[future]
                try:
                    row_results = future.result()
                    for j, result in enumerate(row_results):
                        if result is not None:
                            c3_val, v_inf_dep, v_inf_arr, r_arr, v_arr_planet = result
                            c3_grid[i, j] = c3_val
                            vinf_out_x[i, j] = v_inf_dep[0]
                            vinf_out_y[i, j] = v_inf_dep[1]
                            vinf_out_z[i, j] = v_inf_dep[2]
                            vinf_in_x[i, j] = v_inf_arr[0]
                            vinf_in_y[i, j] = v_inf_arr[1]
                            vinf_in_z[i, j] = v_inf_arr[2]
                            v_arr_x[i, j] = v_arr_planet[0]
                            v_arr_y[i, j] = v_arr_planet[1]
                            v_arr_z[i, j] = v_arr_planet[2]
                            r_arr_x[i, j] = r_arr[0]
                            r_arr_y[i, j] = r_arr[1]
                            r_arr_z[i, j] = r_arr[2]
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.exception('Error processing departure time %s: %s', dep_times[i].isot, e)
    else:
        # Serial computation with shared cache
        cache = StateCache()
        
        # Prefetch all required states
        for dep in dep_times:
            cache.get(dep_body, dep)
        
        for dep in dep_times:
            for tof in tof_days:
                arr = Time(dep.jd + tof, format='jd', scale='tdb')
                cache.get(arr_body, arr)

        logger = logging.getLogger(__name__)
        logger.info('Prefetched %d state vectors', cache.size())

        for i, dep in enumerate(dep_times):
            for j, tof in enumerate(tof_days):
                try:
                    arr = Time(dep.jd + tof, format='jd', scale='tdb')
                    _, c3_val, v_inf_dep, v_inf_arr, r_arr, v_arr_planet, _ = compute_transfer_c3_tof_cached(
                        dep, arr, cache, dep_body=dep_body, arr_body=arr_body
                    )
                    c3_grid[i, j] = c3_val
                    vinf_out_x[i, j] = v_inf_dep[0]
                    vinf_out_y[i, j] = v_inf_dep[1]
                    vinf_out_z[i, j] = v_inf_dep[2]
                    vinf_in_x[i, j] = v_inf_arr[0]
                    vinf_in_y[i, j] = v_inf_arr[1]
                    vinf_in_z[i, j] = v_inf_arr[2]
                    v_arr_x[i, j] = v_arr_planet[0]
                    v_arr_y[i, j] = v_arr_planet[1]
                    v_arr_z[i, j] = v_arr_planet[2]
                    r_arr_x[i, j] = r_arr[0]
                    r_arr_y[i, j] = r_arr[1]
                    r_arr_z[i, j] = r_arr[2]
                except Exception:
                    continue  # Leave as NaN

    return {
        'c3_grid': c3_grid,
        'vinf_out_x': vinf_out_x, 'vinf_out_y': vinf_out_y, 'vinf_out_z': vinf_out_z,
        'vinf_in_x': vinf_in_x, 'vinf_in_y': vinf_in_y, 'vinf_in_z': vinf_in_z,
        'v_arr_x': v_arr_x, 'v_arr_y': v_arr_y, 'v_arr_z': v_arr_z,
        'r_arr_x': r_arr_x, 'r_arr_y': r_arr_y, 'r_arr_z': r_arr_z
    }


def _compute_dep_row(dep: Time, tof_days: np.ndarray, dep_body: str, arr_body: str) -> List[Tuple | None]:
    """Compute one row of the grid for a single departure time."""
    # Ensure SPICE kernels are loaded in this worker process
    ensure_spice_loaded()
    
    # Create per-worker cache
    cache = StateCache()
    cache.get(dep_body, dep)
    
    results = []
    for tof in tof_days:
        try:
            arr = Time(dep.jd + tof, format='jd', scale='tdb')
            cache.get(arr_body, arr)
            _, c3_val, v_inf_dep, v_inf_arr, r_arr, v_arr_planet, _ = compute_transfer_c3_tof_cached(
                dep, arr, cache, dep_body=dep_body, arr_body=arr_body
            )
            results.append((c3_val, v_inf_dep, v_inf_arr, r_arr, v_arr_planet))
        except Exception:
            results.append(None)
    
    return results


def _create_refined_grid(coarse_dep_times: List[Time], coarse_tof_days: np.ndarray, 
                        promising_mask: np.ndarray, fine_dep_step: int, 
                        fine_tof_days: np.ndarray, dep_start: Time, dep_end: Time) -> Tuple[List[Time], np.ndarray]:
    """Create refined grid around promising coarse grid points."""
    refined_dep_times = set()
    refined_tof_days = set()
    
    n_coarse_dep = len(coarse_dep_times)
    n_coarse_tof = len(coarse_tof_days)
    
    for i in range(n_coarse_dep):
        for j in range(n_coarse_tof):
            if promising_mask[i, j]:
                # Add this coarse point and surrounding fine points
                coarse_dep = coarse_dep_times[i]
                coarse_tof = coarse_tof_days[j]
                
                # Add points in a window around this promising point
                dep_window = fine_dep_step * 2  # ±2 steps
                tof_window = 4  # ±4 days
                
                dep_min = max(dep_start.jd, coarse_dep.jd - dep_window)
                dep_max = min(dep_end.jd, coarse_dep.jd + dep_window)
                
                # Add fine departure times in this window
                dep_times_window = Time(
                    np.arange(dep_min, dep_max + 1e-9, fine_dep_step),
                    format='jd', scale='tdb'
                )
                refined_dep_times.update(dep_times_window.jd)
                
                # Add TOF values in window
                tof_min = max(fine_tof_days[0], coarse_tof - tof_window)
                tof_max = min(fine_tof_days[-1], coarse_tof + tof_window)
                tof_values = fine_tof_days[(fine_tof_days >= tof_min) & (fine_tof_days <= tof_max)]
                refined_tof_days.update(tof_values)
    
    # Convert back to arrays
    refined_dep_times = Time(sorted(refined_dep_times), format='jd', scale='tdb')
    refined_tof_days = np.array(sorted(refined_tof_days))
    
    return refined_dep_times, refined_tof_days


def compute_transfer_c3_tof_cached(
    dep_time: str | Time,
    arr_time: str | Time,
    cache: StateCache,
    dep_body: str,
    arr_body: str,
    prograde: bool | None = None,
    lowpath: bool | None = None,
) -> Tuple[float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Tuple[int, bool, bool]]:
    """
    Compute (tof_days, C3, v_inf_dep, v_inf_arr, r_arr, v_arr_planet, branch) for any dep→arr pair using cache.
    """
    dep_t = _to_time(dep_time)
    arr_t = _to_time(arr_time)

    if arr_t <= dep_t:
        raise ValueError(f"Arrival time {arr_t.isot} must be after departure time {dep_t.isot}")

    # Sun-centered states (cached)
    r_dep, v_dep_planet = cache.get(dep_body, dep_t)
    r_arr, v_arr_planet = cache.get(arr_body, arr_t)

    # Time of flight
    tof = (arr_t - dep_t)

    # Try Lambert branches
    res = best_lambert_branch(
        r_dep, v_dep_planet, r_arr, v_arr_planet, tof,
        rtol=1e-10, prograde=prograde, lowpath=lowpath
    )
    if res is None:
        raise RuntimeError(f"No Lambert solution found for {dep_body} to {arr_body} transfer from {dep_t.isot} to {arr_t.isot} (TOF: {tof.to_value(u.day):.1f} days)")

    min_C3, v_dep_best, v_arr_best, used = res

    # v_inf relative to planets
    v_inf_dep = v_dep_best - v_dep_planet
    v_inf_arr = v_arr_best - v_arr_planet

    tof_days = tof.to_value(u.day)
    return tof_days, float(min_C3), v_inf_dep, v_inf_arr, r_arr, v_arr_planet, used


def compute_transfer_c3_tof(
    dep_time: str | Time,
    arr_time: str | Time,
    dep_body: str,
    arr_body: str,
    prograde: bool | None = None,
    lowpath: bool | None = None,
) -> Tuple[float, float, np.ndarray, np.ndarray, Tuple[int, bool, bool]]:
    """
    Compute (tof_days, C3, v_inf_dep, v_inf_arr, branch) for any dep→arr pair.
    """
    dep_t = _to_time(dep_time)
    arr_t = _to_time(arr_time)

    if arr_t <= dep_t:
        raise ValueError(f"Arrival time {arr_t.isot} must be after departure time {dep_t.isot}")

    # Sun-centered states
    r_dep, v_dep_planet = rv_helio_spice(dep_body, dep_t)
    r_arr, v_arr_planet = rv_helio_spice(arr_body, arr_t)

    # Time of flight
    tof = (arr_t - dep_t)

    # Try Lambert branches
    res = best_lambert_branch(
        r_dep, v_dep_planet, r_arr, v_arr_planet, tof,
        rtol=1e-10, prograde=prograde, lowpath=lowpath
    )
    if res is None:
        raise RuntimeError(f"No Lambert solution found for {dep_body} to {arr_body} transfer from {dep_t.isot} to {arr_t.isot} (TOF: {tof.to_value(u.day):.1f} days)")

    min_C3, v_dep_best, v_arr_best, used = res

    # v_inf relative to planets
    v_inf_dep = v_dep_best - v_dep_planet
    v_inf_arr = v_arr_best - v_arr_planet

    tof_days = tof.to_value(u.day)
    return tof_days, float(min_C3), v_inf_dep, v_inf_arr, used


def screen_transfer_grid(
    dep_start: str | Time,
    dep_end: str | Time,
    dep_step_days: int,
    tof_min_days: int,
    tof_max_days: int,
    tof_step_days: int = 1,
    dep_body: str = "399",
    arr_body: str = "499",
) -> Tuple[List[Time], np.ndarray, np.ndarray]:
    """
    Screen transfer grid and return (dep_times, tof_days, c3_grid).
    """
    dep_start_t = _to_time(dep_start)
    dep_end_t = _to_time(dep_end)

    dep_times = Time(
        np.arange(dep_start_t.jd, dep_end_t.jd + 1e-9, dep_step_days),
        format='jd',
        scale='tdb'
    )
    tof_days = np.arange(tof_min_days, tof_max_days + 1, tof_step_days)

    c3_grid = np.full((len(dep_times), len(tof_days)), np.nan)

    for i, dep in enumerate(dep_times):
        for j, tof in enumerate(tof_days):
            try:
                arr = Time(dep.jd + tof, format='jd', scale='tdb')
                _, c3_val, _, _, _ = compute_transfer_c3_tof(
                    dep, arr, dep_body=dep_body, arr_body=arr_body
                )
                c3_grid[i, j] = c3_val
            except Exception:
                continue  # Leave as NaN

    return dep_times, tof_days, c3_grid


def screen_transfer_grid_cached(
    dep_start: str | Time,
    dep_end: str | Time,
    dep_step_days: int,
    tof_min_days: int,
    tof_max_days: int,
    tof_step_days: int = 1,
    dep_body: str = "399",
    arr_body: str = "499",
    n_workers: int | None = None,
    coarse_refine: bool = False,
    coarse_factor: int = 4,
    use_threads: bool = False,
    kernel_paths: list[str] | None = None,
) -> Tuple[List[Time], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Screen transfer grid with caching and return (dep_times, tof_days, c3_grid, 
    vinf_out_x, vinf_out_y, vinf_out_z, vinf_in_x, vinf_in_y, vinf_in_z, 
    v_arr_x, v_arr_y, v_arr_z, r_arr_x, r_arr_y, r_arr_z).
    
    Args:
        dep_start: Departure start time
        dep_end: Departure end time  
        dep_step_days: Step size for departure times (days)
        tof_min_days: Minimum time of flight (days)
        tof_max_days: Maximum time of flight (days)
        dep_body: Departure body NAIF ID
        arr_body: Arrival body NAIF ID
        n_workers: Number of worker processes (None = serial, 0 = CPU count)
        coarse_refine: Enable coarse→refine mode for large grids
        coarse_factor: Factor by which to coarsen initial grid
        use_threads: Use ThreadPoolExecutor instead of ProcessPoolExecutor
        kernel_paths: Kernel paths for multiprocessing initialization
    """
    dep_start_t = _to_time(dep_start)
    dep_end_t = _to_time(dep_end)

    # Determine if we should use multiprocessing
    if n_workers is None or n_workers <= 1:
        use_mp = False
        actual_workers = 1
    else:
        use_mp = True
        actual_workers = mp.cpu_count() if n_workers == 0 else n_workers

    # Create base grids
    base_dep_times = Time(
        np.arange(dep_start_t.jd, dep_end_t.jd + 1e-9, dep_step_days),
        format='jd',
        scale='tdb'
    )
    base_tof_days = np.arange(tof_min_days, tof_max_days + 1, tof_step_days)

    if coarse_refine:
        # Run coarse grid first
        coarse_dep_step = max(1, dep_step_days * coarse_factor)
        coarse_tof_step = max(tof_step_days, coarse_factor * tof_step_days)

        coarse_dep_times = Time(
            np.arange(dep_start_t.jd, dep_end_t.jd + 1e-9, coarse_dep_step),
            format='jd',
            scale='tdb'
        )
        coarse_tof_days = np.arange(tof_min_days, tof_max_days + 1, coarse_tof_step)

        logger = logging.getLogger(__name__)
        logger.info('Running coarse grid: %dx%d = %d points', len(coarse_dep_times), len(coarse_tof_days), len(coarse_dep_times) * len(coarse_tof_days))

        # Compute coarse grid
        coarse_results = _compute_grid_chunk(
            coarse_dep_times, coarse_tof_days, dep_body, arr_body, use_mp, actual_workers, kernel_paths, use_threads
        )

        # Find promising regions (C3 < some threshold)
        c3_threshold = np.nanpercentile(coarse_results['c3_grid'], 25)  # Bottom 25% of C3 values
        promising_mask = coarse_results['c3_grid'] < c3_threshold

        if not np.any(promising_mask):
            logger.info('No promising regions found in coarse grid, using all points')
            promising_mask = np.ones_like(coarse_results['c3_grid'], dtype=bool)

        # Create refined grid around promising points
        dep_times, tof_days = _create_refined_grid(
            coarse_dep_times, coarse_tof_days, promising_mask,
            dep_step_days, base_tof_days, dep_start_t, dep_end_t
        )

        logger.info('Refined to %dx%d = %d points', len(dep_times), len(tof_days), len(dep_times) * len(tof_days))
    else:
        dep_times = base_dep_times
        tof_days = base_tof_days

    # Compute the final grid
    results = _compute_grid_chunk(
        dep_times, tof_days, dep_body, arr_body, use_mp, actual_workers, kernel_paths, use_threads
    )

    return (
        dep_times, tof_days, results['c3_grid'],
        results['vinf_out_x'], results['vinf_out_y'], results['vinf_out_z'],
        results['vinf_in_x'], results['vinf_in_y'], results['vinf_in_z'],
        results['v_arr_x'], results['v_arr_y'], results['v_arr_z'],
        results['r_arr_x'], results['r_arr_y'], results['r_arr_z']
    )


def grid_transfer(dep_start, dep_end, dep_step_d, tof_min_d, tof_max_d, tof_step_d, dep_body="399", arr_body="499") -> Iterator[Tuple[Time, Time]]:
    """Generate (t_dep, t_arr) pairs for transfer grid."""
    dep_start_t = _to_time(dep_start)
    dep_end_t = _to_time(dep_end)
    
    dep_times = Time(
        np.arange(dep_start_t.jd, dep_end_t.jd + 1e-9, dep_step_d),
        format='jd',
        scale='tdb'
    )
    tof_days = np.arange(tof_min_d, tof_max_d + 1, tof_step_d)
    
    for dep in dep_times:
        for tof in tof_days:
            arr = Time(dep.jd + tof, format='jd', scale='tdb')
            yield dep, arr


def eval_transfer_point(t_dep, t_arr, dep_body="399", arr_body="499") -> dict:
    """Evaluate transfer point and return dict with C3, tof, etc."""
    try:
        tof_days, c3_val, v_inf_dep, v_inf_arr, used = compute_transfer_c3_tof(t_dep, t_arr, dep_body, arr_body)
        vinf_kms = np.linalg.norm(v_inf_dep)
        return {
            'C3': c3_val,
            'tof_days': tof_days,
            'vinf_out_kms': vinf_kms,
            'dep_iso': t_dep.isot,
            'arr_iso': t_arr.isot,
            'dep_body': dep_body,
            'arr_body': arr_body
        }
    except ValueError as e:
        logger = logging.getLogger(__name__)
        logger.warning('Validation error for %s -> %s: %s', t_dep.isot, t_arr.isot, e)
        return {
            'C3': np.nan,
            'tof_days': np.nan,
            'vinf_out_kms': np.nan,
            'dep_iso': t_dep.isot,
            'arr_iso': t_arr.isot,
            'dep_body': dep_body,
            'arr_body': arr_body
        }
    except RuntimeError as e:
        logger = logging.getLogger(__name__)
        logger.exception('Computation error for %s -> %s: %s', t_dep.isot, t_arr.isot, e)
        return {
            'C3': np.nan,
            'tof_days': np.nan,
            'vinf_out_kms': np.nan,
            'dep_iso': t_dep.isot,
            'arr_iso': t_arr.isot,
            'dep_body': dep_body,
            'arr_body': arr_body
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception('Unexpected error for %s -> %s: %s', t_dep.isot, t_arr.isot, e)
        return {
            'C3': np.nan,
            'tof_days': np.nan,
            'vinf_out_kms': np.nan,
            'dep_iso': t_dep.isot,
            'arr_iso': t_arr.isot,
            'dep_body': dep_body,
            'arr_body': arr_body
        }