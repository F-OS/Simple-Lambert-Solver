"""Minimal CLI: iterate a departure date range and TOF range and print
V1, V2, C3 per line. Keeps things intentionally small for testing the solver.

Example:
  python -m src.lambertlab.main --start-date 2035-06-25 --end-date 2035-06-27 --step 1 --min-tof 190 --max-tof 192
"""

import argparse
import numpy as np
from astropy.time import Time
from astropy import units as u

try:
    from .solver import load_kernels, compute_c3_tof
except ImportError:
    # allow direct execution from package dir
    from solver import load_kernels, compute_c3_tof


def parse_args():
    p = argparse.ArgumentParser(description='Print V1, V2, C3 lines for a date range')
    p.add_argument('--dep-body', type=str, default='399')
    p.add_argument('--arr-body', type=str, default='4')
    p.add_argument('--start-date', type=str, required=True)
    p.add_argument('--end-date', type=str, required=True)
    p.add_argument('--step', type=int, default=1)
    p.add_argument('--min-tof', type=int, default=180)
    p.add_argument('--max-tof', type=int, default=220)
    return p.parse_args()


def main():
    args = parse_args()
    load_kernels()

    dep_start = Time(args.start_date)
    dep_end = Time(args.end_date)
    dep_times = Time(np.arange(dep_start.jd, dep_end.jd + 1, args.step), format='jd')

    tof_days = np.arange(args.min_tof, args.max_tof + 1, 1)

    # Print CSV header
    print('dep_tdb,arr_tdb,tof_days,vinf_dep_x,vinf_dep_y,vinf_dep_z,vinf_arr_x,vinf_arr_y,vinf_arr_z,C3,branch_M,branch_prograde,branch_lowpath')
    for dep in dep_times:
        # Buffer results for this departure across tof values so we can do neighbor spike checks
        rows = []
        C3_grid = np.full(len(tof_days), np.nan)
        for j, tof in enumerate(tof_days):
            arr = dep + tof * u.day
            tof_d, c3, v_inf_dep, v_inf_arr, branch = compute_c3_tof(dep.isot, arr.isot,
                                                                    dep_body=args.dep_body,
                                                                    arr_body=args.arr_body)
            rows.append((dep.tdb.isot, arr.tdb.isot, tof_d, c3, v_inf_dep, v_inf_arr, branch))
            C3_grid[j] = c3 if np.isfinite(c3) else np.nan

        # Spike detection and simple correction per your suggested guard
        for j in range(len(rows)):
            dep_iso, arr_iso, tof_d, c3, v_inf_dep, v_inf_arr, branch = rows[j]
            M, prograde, lowpath = branch

            # Guard 2: spike detector comparing neighbors
            if j > 0 and j + 1 < len(tof_days):
                prevC3 = C3_grid[j - 1]
                nextC3 = C3_grid[j + 1]
                if np.isfinite(prevC3) and np.isfinite(nextC3) and np.isfinite(c3):
                    if c3 > 2.0 * 0.5 * (prevC3 + nextC3):
                        # try alternate lowpath first
                        alt_candidates = [not lowpath]
                        for alt_lowpath in alt_candidates:
                            try:
                                # Recompute using solver's re-enumeration path by passing lowpath
                                tof_q = (Time(dep_iso, scale='tdb'), Time(arr_iso, scale='tdb'))
                                # call compute_c3_tof with same dep/arr but forcing lowpath
                                _, c3_alt, v_inf_dep_alt, v_inf_arr_alt, branch_alt = compute_c3_tof(
                                    dep_iso, arr_iso,
                                    dep_body=args.dep_body, arr_body=args.arr_body,
                                    prograde=prograde, lowpath=alt_lowpath
                                )
                                if np.isfinite(c3_alt) and c3_alt < c3:
                                    c3 = c3_alt
                                    v_inf_dep = v_inf_dep_alt
                                    v_inf_arr = v_inf_arr_alt
                                    M, prograde, lowpath = branch_alt
                                    C3_grid[j] = c3
                                    break
                            except Exception:
                                pass

            # Print CSV row with 3-decimal formatting
            print(
                f"{dep_iso},{arr_iso},{tof_d:.1f},"
                f"{v_inf_dep[0]:.3f},{v_inf_dep[1]:.3f},{v_inf_dep[2]:.3f},"
                f"{v_inf_arr[0]:.3f},{v_inf_arr[1]:.3f},{v_inf_arr[2]:.3f},"
                f"{c3:.3f},{M},{prograde},{lowpath}"
            )


if __name__ == '__main__':
    main()

