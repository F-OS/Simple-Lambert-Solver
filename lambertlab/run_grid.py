"""Compute a porkchop-style C3 grid and save results to an .npz file.

Usage (defaults are a small test grid):
  python run_grid.py --start-date 2035-06-25 --end-date 2035-06-30 --dep-step 1 --min-tof 190 --max-tof 210 --tof-step 2

Outputs:
 - prints a short summary
 - writes `porkchop_output.npz` in the current folder containing dep_times, tof_days, C3, vinf_dep, vinf_arr, branch_used
"""
import argparse
import os
import numpy as np
from astropy.time import Time
from astropy import units as u
from src.lambertlab.solver import load_kernels, rv_helio_spice, best_lambert_branch


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--dep-body', default='399')
    p.add_argument('--arr-body', default='4')
    p.add_argument('--start-date', required=True)
    p.add_argument('--end-date', required=True)
    p.add_argument('--dep-step', type=int, default=1)
    p.add_argument('--min-tof', type=int, default=180)
    p.add_argument('--max-tof', type=int, default=220)
    p.add_argument('--tof-step', type=int, default=2)
    p.add_argument('--out', default='porkchop_output.npz')
    p.add_argument('--out-dir', default='.', help='Directory to write outputs into')
    return p.parse_args()


def compute_grid(dep_body, arr_body, start_date, end_date, dep_step, min_tof, max_tof, tof_step):
    dep_start = Time(start_date, scale='tdb')
    dep_end = Time(end_date, scale='tdb')
    dep_times = Time(np.arange(dep_start.jd, dep_end.jd + 1, dep_step), format='jd')
    tof_days = np.arange(min_tof, max_tof + 1, tof_step)

    N = len(dep_times)
    M = len(tof_days)

    # Arrays to fill
    C3 = np.full((N, M), np.nan, dtype=float)
    vinf_dep = np.full((N, M, 3), np.nan, dtype=float)
    vinf_arr = np.full((N, M, 3), np.nan, dtype=float)
    branch_used = np.full((N, M, 3), -1, dtype=int)  # M, prograde (1/0), lowpath (1/0)

    # Preload kernels
    load_kernels()

    for i, dep in enumerate(dep_times):
        # Precompute departure state once (use dep_body as target name)
        r_dep, v_dep_planet = rv_helio_spice(dep_body, dep)

        # Precompute arrival states for all tof values (unique per dep)
        arr_times = dep + tof_days * u.day
        r_arr_list = []
        v_arr_list = []
        for arr in arr_times:
            r_a, v_a = rv_helio_spice(arr_body, arr)
            r_arr_list.append(r_a)
            v_arr_list.append(v_a)

        # Compute each cell
        for j, tof in enumerate(tof_days):
            r_arr = r_arr_list[j]
            v_arr_planet = v_arr_list[j]
            # Call best_lambert_branch; it will attempt default lambert and re-enumerate if inconsistent
            res = best_lambert_branch(r_dep, v_dep_planet, r_arr, v_arr_planet, (arr_times[j] - dep), prograde=None, lowpath=None)
            if res is None:
                # leave NaN
                continue
            min_C3, v_dep_best, v_arr_best, used = res
            # Compute v_inf arrays
            v_inf_dep = v_dep_best - v_dep_planet
            v_inf_arr = v_arr_best - v_arr_planet

            # Store
            C3[i, j] = min_C3
            vinf_dep[i, j, :] = v_inf_dep
            vinf_arr[i, j, :] = v_inf_arr
            Mflag, pr, lp = used
            branch_used[i, j, 0] = int(Mflag)
            branch_used[i, j, 1] = 1 if pr else 0
            branch_used[i, j, 2] = 1 if lp else 0

        # After row computed, apply spike detector for each interior j
        for j in range(1, M - 1):
            c = C3[i, j]
            if not np.isfinite(c):
                continue
            prevC3 = C3[i, j - 1]
            nextC3 = C3[i, j + 1]
            if np.isfinite(prevC3) and np.isfinite(nextC3):
                if c > 2.0 * 0.5 * (prevC3 + nextC3):
                    # try alternate lowpath first (toggle current stored lowpath)
                    cur_lp = bool(branch_used[i, j, 2] == 1)
                    alt_lp = not cur_lp
                    # recompute trying same prograde but alt lowpath
                    pr_flag = bool(branch_used[i, j, 1] == 1) if branch_used[i, j, 1] >= 0 else None
                    try:
                        res_alt = best_lambert_branch(r_dep, v_dep_planet, r_arr_list[j], v_arr_list[j], (arr_times[j] - dep), prograde=pr_flag, lowpath=alt_lp)
                        if res_alt is not None:
                            C3_alt, v_dep_alt, v_arr_alt, used_alt = res_alt
                            if np.isfinite(C3_alt) and C3_alt < c:
                                # accept alt
                                C3[i, j] = C3_alt
                                vinf_dep[i, j, :] = v_dep_alt - v_dep_planet
                                vinf_arr[i, j, :] = v_arr_alt - v_arr_planet
                                Mflag, pr, lp = used_alt
                                branch_used[i, j, 0] = int(Mflag)
                                branch_used[i, j, 1] = 1 if pr else 0
                                branch_used[i, j, 2] = 1 if lp else 0
                    except Exception:
                        pass

    return dep_times, tof_days, C3, vinf_dep, vinf_arr, branch_used


if __name__ == '__main__':
    args = parse_args()
    dep_times, tof_days, C3, vinf_dep, vinf_arr, branch_used = compute_grid(
        args.dep_body, args.arr_body, args.start_date, args.end_date, args.dep_step, args.min_tof, args.max_tof, args.tof_step
    )

    # Ensure output directory exists and save results there
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(out_dir, args.out)
    np.savez(out_path,
             dep_times=[t.tdb.isot for t in dep_times],
             tof_days=tof_days,
             C3=C3,
             vinf_dep=vinf_dep,
             vinf_arr=vinf_arr,
             branch_used=branch_used)

    # Quick summary
    total = C3.size
    finite = np.isfinite(C3).sum()
    pct_nan = 100.0 * (1 - finite / total)
    print(f"Grid shape: {C3.shape}, finite cells: {finite}/{total} ({pct_nan:.2f}% NaN)")
    if finite > 0:
        idx = np.unravel_index(np.nanargmin(C3), C3.shape)
        print(f"Minimum C3 = {C3[idx]:.3f} km^2/s^2 at dep={dep_times[idx[0]].tdb.isot}, tof={tof_days[idx[1]]} days")
    print(f"Saved output to {out_path}")
