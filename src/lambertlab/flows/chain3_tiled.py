"""
Checkpointed three-body chain computation with tiling.

Provides resumable, crash-proof gravity assist trajectory search.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import pykep as pk
from astropy import units as u
from astropy.time import Time

from ..core.checkpoint import (
    Tile, TileResult, checkpoint_context,
    make_tile_id, atomic_write_csv, sha256_file, write_state
)
from ..core.config import MU_MARS
from ..core.lambert_io import solve_leg
from ..core.spice_io import rv_helio_spice
from ..flows.em_only import screen_em_grid_cached


@dataclass
class Chain3Config:
    """Configuration for chain3 computation."""
    dep_body: int
    flyby_body: int
    arr_body: int
    dep_window_start: str
    dep_window_end: str
    dep_step: int
    leg1_tof_min: int
    leg1_tof_max: int
    leg1_tof_step: int
    leg2_tof_min: int
    leg2_tof_max: int
    leg2_tof_step: int
    rp_min_km: float
    rp_max_km: float
    bplane_theta_min_deg: float
    bplane_theta_max_deg: float
    bplane_theta_n: int
    tile_size: int = 10
    checkpoint_sec: int = 30
    max_solutions: int = 200
    dv_tol_ms: float = 100.0
    n_workers: int = 1
    seed: int = 42
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dep_body': self.dep_body,
            'flyby_body': self.flyby_body,
            'arr_body': self.arr_body,
            'dep_window': f"{self.dep_window_start}:{self.dep_window_end}",
            'dep_step': self.dep_step,
            'leg1_tof': f"{self.leg1_tof_min}:{self.leg1_tof_max}:{self.leg1_tof_step}",
            'leg2_tof': f"{self.leg2_tof_min}:{self.leg2_tof_max}:{self.leg2_tof_step}",
            'rp_bounds_km': f"{self.rp_min_km}:{self.rp_max_km}",
            'bplane_theta_deg': f"{self.bplane_theta_min_deg}:{self.bplane_theta_max_deg}:{self.bplane_theta_n}",
            'tile_size': self.tile_size,
            'max_solutions': self.max_solutions,
            'dv_tol_ms': self.dv_tol_ms,
            'seed': self.seed
        }


def make_chain3_tiles(config: Chain3Config) -> List[Tile]:
    """
    Create tiles for chain3 computation.
    
    Strategy: Tile the Leg 1 grid (dep × tof1).
    Each tile will independently compute Leg 1, then expand through flybys and Leg 2.
    
    Args:
        config: Chain3 configuration
        
    Returns:
        List of Tile objects
    """
    # Calculate grid dimensions
    n_dep = int(np.ceil((Time(config.dep_window_end) - Time(config.dep_window_start)).jd / config.dep_step))
    n_tof1 = int((config.leg1_tof_max - config.leg1_tof_min) / config.leg1_tof_step) + 1
    
    tiles = []
    tile_idx = 0
    
    # Tile the departure × TOF1 grid
    for i in range(0, n_dep, config.tile_size):
        for j in range(0, n_tof1, config.tile_size):
            dep_start = i
            dep_end = min(i + config.tile_size, n_dep)
            tof_start = j
            tof_end = min(j + config.tile_size, n_tof1)
            
            tile_id = make_tile_id(
                'chain3',
                d=f"{dep_start:04d}-{dep_end:04d}",
                t=f"{tof_start:04d}-{tof_end:04d}"
            )
            
            tiles.append(Tile(
                id=tile_id,
                kind='chain3',
                params={
                    'dep_start_idx': dep_start,
                    'dep_end_idx': dep_end,
                    'tof_start_idx': tof_start,
                    'tof_end_idx': tof_end
                },
                seed=config.seed + tile_idx
            ))
            tile_idx += 1
    
    return tiles


def process_chain3_tile(tile: Tile, config: Chain3Config, outdir: Path) -> TileResult:
    """
    Process a single chain3 tile.
    
    This is the core computation function that runs independently per tile.
    
    Args:
        tile: Tile to process
        config: Chain3 configuration
        outdir: Output directory
        
    Returns:
        TileResult with output metadata
    """
    start_time = time.time()
    
    # Set deterministic seed for this tile
    np.random.seed(tile.seed)
    
    # Parse tile bounds
    dep_start_idx = tile.params['dep_start_idx']
    dep_end_idx = tile.params['dep_end_idx']
    tof_start_idx = tile.params['tof_start_idx']
    tof_end_idx = tile.params['tof_end_idx']
    
    # Compute full Leg 1 grid (we'll extract our tile slice)
    dep_start = Time(config.dep_window_start, scale='tdb')
    dep_end = Time(config.dep_window_end, scale='tdb')
    
    dep_times, tof1_days, c3_leg1, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, \
        vFB_x, vFB_y, vFB_z, rFB_x, rFB_y, rFB_z = screen_em_grid_cached(
            dep_start, dep_end, config.dep_step,
            config.leg1_tof_min, config.leg1_tof_max, config.leg1_tof_step,
            dep_body=str(config.dep_body), arr_body=str(config.flyby_body),
            n_workers=1  # Single worker per tile
        )
    
    # Extract tile slice

    # Prepare grids for B-plane and Leg 2
    theta_grid = np.linspace(
        np.radians(config.bplane_theta_min_deg),
        np.radians(config.bplane_theta_max_deg),
        config.bplane_theta_n
    )
    rp_grid = np.linspace(config.rp_min_km, config.rp_max_km, 10)
    
    # Storage for solutions from this tile
    solutions = []
    
    # Process each point in the tile
    for i in range(dep_start_idx, dep_end_idx):
        if i >= len(dep_times):
            continue
            
        for j in range(tof_start_idx, tof_end_idx):
            if j >= len(tof1_days):
                continue
            
            if not np.isfinite(c3_leg1[i, j]):
                continue
            
            # Leg 1 parameters
            t_dep = dep_times[i]
            tof1 = tof1_days[j]
            t_flyby = t_dep + tof1 * u.day
            c3_launch = c3_leg1[i, j]
            
            # Flyby arrival state
            r_flyby = np.array([rFB_x[i, j], rFB_y[i, j], rFB_z[i, j]])
            v_flyby = np.array([vFB_x[i, j], vFB_y[i, j], vFB_z[i, j]])
            vinf_in_vec = np.array([vin_x[i, j], vin_y[i, j], vin_z[i, j]])
            vinf_in_mag = np.linalg.norm(vinf_in_vec)
            
            # Try different periapsis and B-plane angles
            for rp in rp_grid:
                # Gravity turn angle
                mu_flyby = MU_MARS  # TODO: make body-agnostic
                x = 1.0 + (rp * vinf_in_mag**2) / mu_flyby
                if x <= 1.0:
                    continue
                sin_half_delta = 1.0 / x
                if sin_half_delta > 1.0 or sin_half_delta <= 0:
                    continue
                delta = 2.0 * np.arcsin(sin_half_delta)
                
                for theta in theta_grid:
                    # Use PyKEP's fb_prop() for gravity assist rotation
                    # PyKEP fb_prop(v_spacecraft, v_planet, rp, beta, mu)
                    # where beta is the B-plane angle (our theta)
                    v_sc_in = v_flyby + vinf_in_vec  # Heliocentric spacecraft velocity before flyby
                    
                    try:
                        # PyKEP returns post-flyby heliocentric velocity
                        v_sc_post = np.array(pk.fb_prop(
                            v_sc_in.tolist(),
                            v_flyby.tolist(),  # Planet velocity
                            rp,
                            theta,  # B-plane angle (beta)
                            mu_flyby
                        ))
                    except Exception:
                        # PyKEP may throw for invalid geometry
                        continue
                    
                    vinf_out_vec = v_sc_post - v_flyby
                    vinf_out_mag = np.linalg.norm(vinf_out_vec)
                    
                    # Leg 2 scan
                    for tof2 in range(config.leg2_tof_min, config.leg2_tof_max + 1, config.leg2_tof_step):
                        t_arr = t_flyby + tof2 * u.day
                        
                        try:
                            r_arr, v_arr = rv_helio_spice(str(config.arr_body), t_arr)
                            v1, v2 = solve_leg(r_flyby * u.km, r_arr * u.km, tof2 * u.day)
                            
                            v1_arr = v1.to(u.km/u.s).value
                            dv_match = np.linalg.norm(v_sc_post - v1_arr)
                            
                            if dv_match * 1000 > config.dv_tol_ms:
                                continue
                            
                            vinf_arr_vec = (v2 - v_arr * u.km/u.s).to(u.km/u.s).value
                            vinf_arr_mag = np.linalg.norm(vinf_arr_vec)
                            
                            # Store solution
                            solution = {
                                't_dep_tdb': t_dep.tdb.isot,
                                't_flyby_tdb': t_flyby.tdb.isot,
                                't_arr_tdb': t_arr.tdb.isot,
                                'tof1_days': float(tof1),
                                'tof2_days': float(tof2),
                                'tof_total_days': float(tof1 + tof2),
                                'C3_launch_km2s2': float(c3_launch),
                                'vinf_in_kms': float(vinf_in_mag),
                                'vinf_out_kms': float(vinf_out_mag),
                                'rp_km': float(rp),
                                'turn_angle_deg': float(np.degrees(delta)),
                                'bplane_theta_deg': float(np.degrees(theta)),
                                'arr_vinf_kms': float(vinf_arr_mag),
                                'dv_match_ms': float(dv_match * 1000),
                                'score': float(c3_launch + vinf_arr_mag**2),
                                'tile_id': tile.id
                            }
                            
                            solutions.append(solution)
                            
                        except Exception:
                            continue
    
    # Write tile output
    df = pd.DataFrame(solutions)
    tile_dir = outdir / 'tiles'
    tile_dir.mkdir(parents=True, exist_ok=True)
    out_path = tile_dir / tile.filename()
    
    atomic_write_csv(df, out_path)
    
    walltime = time.time() - start_time
    
    return TileResult(
        out_path=str(out_path),
        out_hash=sha256_file(out_path),
        n_records=len(df),
        walltime_s=walltime
    )


def run_chain3_checkpointed(config: Chain3Config, outdir: Path, resume: bool = True):
    """
    Run checkpointed chain3 computation with resumability.
    
    Args:
        config: Chain3 configuration
        outdir: Output directory
        resume: Whether to resume from existing checkpoint (default True)
    """
    outdir = Path(outdir)
    
    # Code modules to track for reproducibility
    code_modules = [
        'lambertlab/core/lambert_io.py',
        'lambertlab/core/spice_io.py',
        'lambertlab/flows/em_only.py',
        'lambertlab/flows/chain3_tiled.py'
    ]
    
    logger = logging.getLogger(__name__)
    logger.info('Starting chain3 computation')
    logger.info('Output directory: %s', outdir)
    logger.info('Resume mode: %s', resume)
    logger.info('')
    
    with checkpoint_context(outdir, config.to_dict(), code_modules) as idx:
        # Create tiles
        tiles = make_chain3_tiles(config)
        logger.info('Total tiles: %d', len(tiles))

        # Register tiles
        idx.ensure_tiles(tiles)

        # Get pending tiles
        pending = idx.pending_tiles()
        logger.info('Pending tiles: %d', len(pending))

        if len(pending) < len(tiles):
            logger.info('Resuming from checkpoint (%d tiles already done)', len(tiles) - len(pending))

        logger.info('')

        # Process tiles
        last_heartbeat = time.time()

        for i, tile in enumerate(pending):
            logger.info('Processing tile %d/%d: %s', i+1, len(pending), tile.id)

            try:
                idx.mark_running(tile.id)
                result = process_chain3_tile(tile, config, outdir)
                idx.mark_done(tile.id, result.out_path, result.out_hash, result.n_records)
                logger.info('  [OK] Done: %d solutions (%.1fs)', result.n_records, result.walltime_s)
            except Exception as e:
                idx.mark_error(tile.id, str(e))
                logger.exception('  [ERR] Error: %s', e)

            # Heartbeat
            if time.time() - last_heartbeat > config.checkpoint_sec:
                progress = idx.progress_summary()
                write_state(outdir, progress)

                logger.info('\nProgress: %d/%d tiles (%.1f%%)', progress['done'], progress['total'], progress['progress_pct'])
                if progress['eta_seconds']:
                    eta_min = progress['eta_seconds'] / 60
                    logger.info('ETA: %.1f minutes', eta_min)
                logger.info('')

                last_heartbeat = time.time()

        # Final progress
        progress = idx.progress_summary()
        write_state(outdir, progress)

        logger.info('')
        logger.info('%s', '=' * 60)
        logger.info('Tile processing complete!')
        logger.info('Total: %d tiles', progress['total'])
        logger.info('Done: %d', progress['done'])
        logger.info('Errors: %d', progress['error'])
        logger.info('')

    # Merge tiles
    logger.info('Merging tile results...')
    merge_tiles(outdir, config)

    logger.info('[OK] Chain3 computation complete!')


def merge_tiles(outdir: Path, config: Chain3Config):
    """
    Merge tile CSVs into final solutions file.
    
    Args:
        outdir: Output directory
        config: Chain3 configuration
    """
    tile_dir = outdir / 'tiles'
    csv_files = list(tile_dir.glob('chain3_*.csv'))
    
    if not csv_files:
        logger = logging.getLogger(__name__)
        logger.info('No tile results to merge')
        return
    
    # Read all tiles
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0:
                dfs.append(df)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning('Could not read %s: %s', csv_file, e)
    
    if not dfs:
        logger = logging.getLogger(__name__)
        logger.info('No valid solutions found')
        return
    
    # Concatenate
    all_solutions = pd.concat(dfs, ignore_index=True)
    logger = logging.getLogger(__name__)
    logger.info('Total solutions before filtering: %d', len(all_solutions))
    
    # Sort by score and keep top N
    all_solutions = all_solutions.sort_values('score')
    top_solutions = all_solutions.head(config.max_solutions)
    
    logger.info('Top solutions (keeping %d)', len(top_solutions))
    
    # Write final solutions
    from ..core.checkpoint import atomic_write_csv
    atomic_write_csv(top_solutions, outdir / 'chain3_solutions.csv')
    
    # Also write all solutions for reference
    atomic_write_csv(all_solutions, outdir / 'chain3_all_solutions.csv')
    
    logger.info('Saved to:')
    logger.info('  %s (top %d)', outdir / 'chain3_solutions.csv', len(top_solutions))
    logger.info('  %s (all %d)', outdir / 'chain3_all_solutions.csv', len(all_solutions))
