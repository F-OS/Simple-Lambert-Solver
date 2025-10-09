import os
import math
import json
import hashlib
import numpy as np
import pytest
import warnings
from pathlib import Path
from astropy.time import Time
import astropy.units as u
import csv
import sys

# Make src importable when running this test standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Suppress ERFA warnings for future dates
warnings.filterwarnings("ignore", message=".*dubious year.*", category=UserWarning)

# --- Import your library under test ---
# Adjust these imports to match your package layout
from lambertlab.core.spice_io import load_kernels
from lambertlab.core.spice_io import rv_helio_spice
from lambertlab.core.config import MU_SUN, MU_MARS, R_MARS
from lambertlab.flows.em_only import screen_em_grid_cached
from lambertlab.flows.flyby import compute_flyby  # your helper from step 8–10
from lambertlab.core.orbits import kepler_propagate  # 2-body propagator about the Sun
from lambertlab.core.frames import v_infinity  # helper that subtracts planet velocity

# ---------- Config knobs ----------
# You can scale these via environment for heavier/lighter sweeps.
GRID_STEP_DAYS   = int(os.getenv("STRESS_DEP_STEP_DAYS", "3"))
TOF_MIN_DAYS     = int(os.getenv("STRESS_TOF_MIN_DAYS", "180"))
TOF_MAX_DAYS     = int(os.getenv("STRESS_TOF_MAX_DAYS", "420"))
TOF_STEP_DAYS    = int(os.getenv("STRESS_TOF_STEP_DAYS", "10"))
N_RANDOM_PROBES  = int(os.getenv("STRESS_N_RANDOM_PROBES", "20"))
SEED             = int(os.getenv("STRESS_SEED", "20250101"))
N_WORKERS        = int(os.getenv("STRESS_N_WORKERS", "2"))
ARTIFACT_DIR     = Path(os.getenv("STRESS_ARTIFACT_DIR", "test_artifacts"))
ARTIFACT_DIR.mkdir(exist_ok=True)

# Mars/Ceres NAIF IDs; Earth=399, Mars=499, Ceres=2000001 (or '1' if your kernel uses 1)
EARTH_ID = 399
MARS_ID  = 499
CERES_ID = "20000001"  # string because sp.spkezr takes names/strings

# Two representative EM opportunity windows; adjust as needed
WINDOWS = [
    # Classic low-C3 window around 2026/2027
    (Time("2026-04-01", scale="tdb"), Time("2026-09-01", scale="tdb")),
    # Future window ~2035
    (Time("2035-04-01", scale="tdb"), Time("2035-09-01", scale="tdb")),
]

# ---------- Utility ----------
def _hash_array(a: np.ndarray) -> str:
    """Stable hash to detect accidental regressions in numeric fields."""
    m = hashlib.sha256()
    m.update(np.nan_to_num(a, nan=1e99).tobytes())
    return m.hexdigest()

def _finite_fraction(a: np.ndarray) -> float:
    if a.size == 0: return 0.0
    return np.isfinite(a).sum() / a.size

# ---------- The test ----------
@pytest.mark.slow
def test_all_up_stress(tmp_path):
    """
    All-up stress test:

    1) Loads kernels and verifies time coverage for all bodies used.
    2) Builds two Earth->Mars porkchop grids across two windows.
    3) Validates 'physics sanity' of the C3 surface:
       - significant fraction finite
       - min C3 within plausible range
       - smoothness (finite-diff continuity) at random probes
    4) Picks the best EM candidate in each window, computes Mars V∞in.
    5) Runs a non-coplanar Mars flyby search to target Ceres:
       - enforces rp bounds (≥ R_Mars + margin)
       - solves for B-plane turning to hit a heliocentric Lambert to Ceres
    6) Verifies patched-conic invariants:
       - V∞ magnitude conserved across flyby (to tol)
       - backward propagation re-encounters Mars at the flyby epoch
    7) Emits artifacts (JSON + CSV) with checksums for reproducibility.
    """
    print(f"\n=== STRESS TEST START ===")
    print(f"Test configuration:")
    print(f"  Grid step: {GRID_STEP_DAYS} days")
    print(f"  TOF range: {TOF_MIN_DAYS}-{TOF_MAX_DAYS} days (step {TOF_STEP_DAYS})")
    print(f"  Random probes: {N_RANDOM_PROBES}")
    print(f"  Workers: {N_WORKERS}")
    print(f"  Seed: {SEED}")
    
    rng = np.random.default_rng(SEED)

    # 1) Load kernels (LSK + DE SPK + MARS SPK + CERES SPK)
    #    Your fixture or conftest can pass explicit paths; here we rely on defaults.
    print(f"\n1) Loading SPICE kernels...")
    load_kernels()

    # Basic coverage smoke: query one epoch per window for all bodies
    print(f"2) Verifying ephemeris coverage for {len(WINDOWS)} windows...")
    for i, (dep_start, dep_end) in enumerate(WINDOWS, 1):
        mid = dep_start + 0.5 * (dep_end - dep_start)
        print(f"  Window {i}: {dep_start.iso} to {dep_end.iso}")
        for bid in (EARTH_ID, MARS_ID, CERES_ID):
            r, v = rv_helio_spice(bid, mid)
            print(f"    Body {bid} @ {mid.iso}: r={np.linalg.norm(r):.1f} km, v={np.linalg.norm(v):.3f} km/s")

    window_artifacts = []

    for widx, (dep_start, dep_end) in enumerate(WINDOWS, start=1):
        # 2) Build porkchop (Earth->Mars)
        dep_times, tof_days, c3_grid, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, rM_x, rM_y, rM_z, vM_x, vM_y, vM_z = screen_em_grid_cached(
            dep_start=dep_start,
            dep_end=dep_end,
            dep_step_days=GRID_STEP_DAYS,
            tof_min_days=TOF_MIN_DAYS,
            tof_max_days=TOF_MAX_DAYS,
            tof_step_days=TOF_STEP_DAYS,
            dep_body=EARTH_ID,
            arr_body=MARS_ID,
            n_workers=N_WORKERS
        )

        assert dep_times.size > 0 and tof_days.size > 0
        assert c3_grid.shape == (dep_times.size, tof_days.size)

        # 3a) significant fraction of finite points
        frac = _finite_fraction(c3_grid)
        # Expect at least 20% finite in a sensible window; tune if needed
        assert frac >= 0.2, f"Too few finite C3 values: {frac:.2%}"

        # 3b) min C3 plausibility (Earth->Mars ~ 8–20 km^2/s^2 in good windows, allow slack)
        c3_min = np.nanmin(c3_grid)
        assert np.isfinite(c3_min), "No finite C3 minima found"
        assert 0.0 <= c3_min < 100.0, f"C3 min looks off: {c3_min:.3f}"

        # 3c) local smoothness: random finite points should not have huge discrete gradients
        #     (prevents unit/frame bugs that create checkerboards)
        grad_limits = []
        for _ in range(N_RANDOM_PROBES):
            i = rng.integers(1, dep_times.size-1)
            j = rng.integers(1, tof_days.size-1)
            if not np.isfinite(c3_grid[i, j]): continue
            # 4-neighbor finite diffs
            diffs = []
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1)):
                nval = c3_grid[i+di, j+dj]
                if np.isfinite(nval):
                    diffs.append(abs(nval - c3_grid[i, j]))
            if diffs:
                grad_limits.append(max(diffs))
        if grad_limits:
            # Upper bound is heuristic—spikes > ~100 km^2/s^2 in 1 step are suspicious
            assert np.percentile(grad_limits, 95) < 100.0, f"Large C3 spikes detected: {np.percentile(grad_limits,95):.1f}"

        # 4) Pick best EM candidate
        best_idx = np.unravel_index(np.nanargmin(c3_grid), c3_grid.shape)
        idep, jtof = best_idx
        dep_epoch = dep_times[idep]
        tof_days_val = float(tof_days[jtof])
        arr_epoch = dep_epoch + tof_days_val * u.day

        # Heliocentric states at Mars arrival
        rM, vM = np.array([rM_x[idep, jtof], rM_y[idep, jtof], rM_z[idep, jtof]]), \
                 np.array([vM_x[idep, jtof], vM_y[idep, jtof], vM_z[idep, jtof]])

        vinf_in_vec = np.array([vin_x[idep, jtof], vin_y[idep, jtof], vin_z[idep, jtof]])
        vinf_in_mag = np.linalg.norm(vinf_in_vec)

        # Sanity check: verify position and velocity magnitudes are correct
        R = np.linalg.norm(rM)
        V = np.linalg.norm(vM)
        assert 1e7 < R < 5e8, f"rM looks wrong: |r|={R:.3e} km (expected ~1e8-2e8)"
        assert 10 < V < 40, f"vM looks wrong: |v|={V:.3f} km/s (expected ~20-30)"

        print(f"Best trajectory: dep_idx={idep}, tof_idx={jtof}, C3={c3_grid[idep, jtof]:.3f}")
        print(f"vinf_in_vec = {vinf_in_vec}, mag = {vinf_in_mag}")
        print(f"rM(km) = {rM}, |rM|={R:.3e} km")
        print(f"vM(km/s) = {vM}, |vM|={V:.3f} km/s")        # 5) Mars flyby to aim at Ceres (non-coplanar allowed)
        # Choose a reasonable periapsis bound: R_Mars + 300 km margin
        rp_min = R_MARS + 300.0  # km
        rp_max = R_MARS + 10000.0

        # Select a small arrival window around arr_epoch to look for Ceres hits
        ceres_window = (arr_epoch + 200*u.day, arr_epoch + 1000*u.day)

        fly = compute_flyby(
            epoch=arr_epoch.tdb,              # flyby epoch at Mars arrival (TDB)
            r_planet=rM, v_planet=vM,         # Mars heliocentric state
            mu_planet=MU_MARS,                # Mars GM
            vinf_in=vinf_in_vec,              # incoming hyperbolic excess (heliocentric frame => subtract planet already)
            rp_bounds=(rp_min, rp_max),       # periapsis bounds
            target_body=CERES_ID,             # NAIF id for Ceres
            mu_central=MU_SUN,                # heliocentric patched conics
            search_arrival_window=ceres_window,
            max_samples=200,                  # search budget; scale with env if desired
            seed=SEED + widx                  # deterministic
        )

        # Flyby solver should return and must be a real model (not the mock)
        assert fly.success, f"Flyby/Ceres targeting failed: {fly.message}"
        assert getattr(fly, 'flyby_model', 'mock') != 'mock', "Flyby solver is still the mock implementation"

        # 6) Invariants and round-trip sanity
        vinf_out_mag = np.linalg.norm(fly.vinf_out)
        assert np.isclose(vinf_in_mag, vinf_out_mag, rtol=0, atol=1e-6), "V∞ magnitude not conserved across flyby (impulsive, no ΔV)"

        # Enforce periapsis/altitude constraints
        assert float(fly.rp) >= (R_MARS + 300.0), f"Periapsis below minimum altitude: {fly.rp} < {R_MARS + 300.0}"
        assert float(fly.rp) > R_MARS, f"Periapsis inside planet radius: {fly.rp} <= {R_MARS}"

        # Backward propagation: from post-flyby heliocentric state at Mars epoch, go backward dt and re-encounter Mars
        # Construct heliocentric state immediately after flyby
        r_helio_after = rM  # position at encounter is the same
        v_helio_after = vM + fly.vinf_out  # add V∞out to Mars heliocentric v

        # Propagate backward a short span and ensure we intersect Mars within small miss distance at encounter time
        # (Use a tiny window +/- minutes; your propagator is two-body Sun-centric)
        t_enc = arr_epoch
        for dt_sec in (-300.0, -120.0, -60.0, 0.0, 60.0, 120.0, 300.0):
            r_back, v_back = kepler_propagate(r_helio_after, v_helio_after, dt_sec, MU_SUN)
            rM_chk, vM_chk = rv_helio_spice(MARS_ID, (t_enc + (dt_sec * u.s)))
            miss_km = np.linalg.norm(r_back - rM_chk)
            # We expect ~<< 100 km near the epoch; patched-conic + two-body vs SPICE Mars heliocentric should be tight
            assert miss_km < 1000.0, f"Round-trip mismatch near encounter: {miss_km:.1f} km"

        # 7) Artifact emission for reproducibility & regression
        #   - Save min point summary + hashes of grids
        summary = {
            "window_index": widx,
            "dep_start_tdb": dep_start.tdb.isot,
            "dep_end_tdb": dep_end.tdb.isot,
            "grid_step_days": GRID_STEP_DAYS,
            "tof_min_days": TOF_MIN_DAYS,
            "tof_max_days": TOF_MAX_DAYS,
            "tof_step_days": TOF_STEP_DAYS,
            "dep_idx": int(idep),
            "tof_idx": int(jtof),
            "dep_epoch_tdb": dep_epoch.tdb.isot,
            "arr_epoch_tdb": arr_epoch.tdb.isot,
            "c3_min": float(c3_min),
            "c3_grid_hash": _hash_array(c3_grid),
            "vinf_in_mag": float(vinf_in_mag),
            "vinf_out_mag": float(vinf_out_mag),
            "rp_km": float(fly.rp),
            "turn_angle_deg": float(np.degrees(fly.turn_angle)),
            "b_plane_mag_km": float(np.linalg.norm(fly.b_vec)),
            "ceres_arrival_epoch_tdb": fly.arrival_epoch.tdb.isot,
            "ceres_c3": float(fly.c3_to_ceres),
            "success": bool(fly.success),
            "flyby_model": getattr(fly, 'flyby_model', 'mock')
        }
        out_json = ARTIFACT_DIR / f"stress_summary_window{widx}.json"
        out_json.write_text(json.dumps(summary, indent=2))

        # Optional: write a small CSV of the slice around the minimum for quick visual diffs
        i0 = max(0, idep-2); i1 = min(c3_grid.shape[0], idep+3)
        j0 = max(0, jtof-2); j1 = min(c3_grid.shape[1], jtof+3)
        csv_path = ARTIFACT_DIR / f"stress_c3_patch_window{widx}.csv"
        with csv_path.open("w", encoding="utf-8") as f:
            f.write("dep_idx,tof_idx,dep_tdb,tof_days,c3\n")
            for ii in range(i0, i1):
                for jj in range(j0, j1):
                    f.write(f"{ii},{jj},{dep_times[ii].tdb.isot},{float(tof_days[jj])},{c3_grid[ii,jj]:.6f}\n")

        window_artifacts.append(str(out_json))

        # If previous window had a different vinf_in, ensure rp/turn are not exactly identical
        if 'prev_vinf' in locals():
            if not np.allclose(vinf_in_vec, prev_vinf, atol=1e-8):
                # require rp or turn differs by at least tiny epsilon
                if np.isfinite(prev_rp) and np.isfinite(prev_turn):
                    assert (abs(float(fly.rp) - float(prev_rp)) > 1e-3) or (abs(float(fly.turn_angle) - float(prev_turn)) > 1e-6), \
                        "Different incoming v_inf produced identical rp/turn (suspicious)"

        prev_vinf = vinf_in_vec.copy()
        prev_rp = float(fly.rp)
        prev_turn = float(fly.turn_angle)

    # One final assert: we created artifacts for both windows
    assert len(window_artifacts) == len(WINDOWS)