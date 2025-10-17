"""SPICE I/O utilities for ephemeris lookups."""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Tuple, Dict

import numpy as np
import spiceypy as sp
from astropy import units as u
from astropy.time import Time

from .config import DEFAULT_KERNELS
from .types import Vec, TimeLike, KM, KMS, FRAME, CENTER, SUN_ID

# Global kernel management for multiprocessing
_KERNEL_PATHS = []
_SPICE_READY = False


def _pool_initializer(paths):
    """Initialize SPICE kernels in a worker process."""
    sp.kclear()
    for p in paths:
        sp.furnsh(p)


def ensure_spice_loaded():
    """Ensure SPICE kernels are loaded in the current process."""
    global _SPICE_READY
    # ktotal==0 means this (sub)process has nothing loaded
    if not _SPICE_READY or sp.ktotal("ALL") == 0:
        for p in _KERNEL_PATHS:
            sp.furnsh(p)
        _SPICE_READY = True


@functools.cache
def time_to_et(t: Time) -> float:
    """Convert astropy Time to SPICE ET using UTC string."""
    return sp.str2et(t.utc.isot)


class StateCache:
    """Cache for SPICE state vectors to avoid repeated expensive calls."""
    
    def __init__(self):
        self._cache: Dict[Tuple[str, float], Tuple[Vec, Vec]] = {}
    
    def get(self, target: str, t: Time) -> Tuple[Vec, Vec]:
        """Get cached (r, v) for target at time t, computing if not cached."""
        key = (target, t.tdb.jd)
        if key not in self._cache:
            self._cache[key] = rv_helio_spice(target, t)
        return self._cache[key]
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()
    
    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)


def load_kernels(paths: list[str] | None = None) -> None:
    """Load SPICE kernels from provided paths (idempotent)."""
    global _KERNEL_PATHS, _SPICE_READY
    if paths is None:
        paths = DEFAULT_KERNELS
    sp.kclear()
    for kernel_path in paths:
        kernel = Path(kernel_path)
        if not kernel.exists():
            raise FileNotFoundError(f"Kernel file not found: {kernel}")
        
        logger = logging.getLogger(__name__)
        logger.info('Loading kernel: %s', kernel)
        try:
            sp.furnsh(kernel.as_posix())
            logger.info('Successfully loaded %s', kernel)
        except Exception as e:
            raise RuntimeError(f"Error loading kernel {kernel}: {e}")
    
    _KERNEL_PATHS = list(paths)
    _SPICE_READY = True


def rv_helio_spice(target: str | int, epoch: Time) -> Tuple[Vec, Vec]:
    """Return heliocentric position (km) and velocity (km/s) for target at epoch.

    Returns plain numpy arrays (no astropy Quantity) to avoid expensive unit ops
    inside tight loops.
    target: SPICE name or ID (string). epoch: astropy Time with scale='tdb'.
    """
    validate_time_range(epoch, target)
    et = time_to_et(epoch)
    state, _ = sp.spkezr(str(target).upper(), et, FRAME, "NONE", CENTER)
    # state: [rx, ry, rz, vx, vy, vz] with km and km/s
    r_km = np.array(state[:3], dtype=float)
    v_kms = np.array(state[3:6], dtype=float)
    return r_km, v_kms


def rv_helio_spice_q(target: str, epoch: Time) -> Tuple[u.Quantity, u.Quantity]:
    """Return (r[km], v[km/s]) as astropy Quantities, Sun-centered J2000, geometric."""
    r, v = rv_helio_spice(target, epoch)
    return r * KM, v * KMS


def rv_helio(target: str, t: Time) -> Tuple[u.Quantity, u.Quantity]:
    """Return heliocentric position and velocity for target at time t (J2000/TDB, SUN)."""
    return rv_helio_spice_q(target, t)


def validate_time_range(t: Time, target: str | int) -> None:
    """Validate that the target has ephemeris data for the given time.
    
    Raises ValueError with helpful message if data is not available.
    """
    try:
        et = time_to_et(t)
        # Try to get state - this will fail if no kernel coverage
        if isinstance(target, int):
            state, _ = sp.spkez(target, et, FRAME, "NONE", SUN_ID)
        else:
            state, _ = sp.spkezr(str(target).upper(), et, FRAME, "NONE", CENTER)
    except sp.stypes.SpiceyError as e:
        if "SPKINSUFFDATA" in str(e):
            # Get target ID for coverage checks
            if isinstance(target, str):
                try:
                    target_id = sp.bodn2c(target.upper())
                except sp.stypes.SpiceyError:
                    target_id = None
            else:
                target_id = target
            
            if target_id is None:
                raise ValueError(f"Unknown target '{target}'. Cannot check coverage.")
            
            # Try to find which kernels might have coverage
            loaded_kernels = sp.ktotal("ALL")
            coverage_info = []

            for i in range(loaded_kernels):
                kernel = sp.kdata(i, "ALL")[0]
                try:
                    spk_info = sp.spkobj(kernel)
                    if target_id in spk_info:
                        coverage = sp.spkcov(kernel, target_id)
                        if coverage.size > 0:
                            start_et = coverage[0]
                            end_et = coverage[-1]
                            start_time = sp.et2utc(start_et, "ISOC", 0)
                            end_time = sp.et2utc(end_et, "ISOC", 0)
                            coverage_info.append(f"{kernel}: {start_time} to {end_time}")
                except:
                    pass

            coverage_msg = "\n".join(coverage_info) if coverage_info else "No kernels found with coverage for this target"

            raise ValueError(
                f"No ephemeris data available for target '{target}' at {t.isot}.\n"
                f"Available coverage:\n{coverage_msg}\n"
                f"Consider updating your kernel set or checking the target ID."
            )
        else:
            raise ValueError(f"SPICE error for target '{target}' at {t.isot}: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error validating time range for target '{target}' at {t.isot}: {e}")
def _to_time(t: TimeLike) -> Time:
    if isinstance(t, Time):
        return t
    return Time(str(t), scale='tdb')