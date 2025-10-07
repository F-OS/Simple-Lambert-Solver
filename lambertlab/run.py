#!/usr/bin/env python3
r"""Run a porkchop generation end-to-end: compute grid, save .npz, and produce a styled plot.

Usage example (PowerShell):
    & 'C:/path/to/.venv/Scripts/python.exe' run.py --start-date 2035-06-15 --end-date 2035-07-05 --dep-step 1 --min-tof 180 --max-tof 210 --tof-step 1

Output:
 - saves a .npz in --out-dir (default: results)
 - saves a styled PNG into the same folder
"""
import os
import sys
import argparse
import numpy as np
from astropy.time import Time
from datetime import datetime

# Allow importing the package from local `src` directory (same pattern used elsewhere)
ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from run_grid import compute_grid
from lambertlab.plotter import plot_porkchop


def parse_args():
    p = argparse.ArgumentParser(description='Compute porkchop grid and produce a styled plot')
    p.add_argument('--dep-body', default='399', help='Departure body (NAIF id or name)')
    p.add_argument('--arr-body', default='4', help='Arrival body (NAIF id or name)')
    p.add_argument('--start-date', required=False, default='', help='Departure start date (ISO, e.g. 2035-06-01)')
    p.add_argument('--end-date', required=False, default='', help='Departure end date (ISO)')
    p.add_argument('--dep-step', type=float, default=1.0, help='Departure step in days (can be fractional)')
    p.add_argument('--min-tof', type=float, default=180.0, help='Minimum time-of-flight in days')
    p.add_argument('--max-tof', type=float, default=210.0, help='Maximum time-of-flight in days')
    p.add_argument('--tof-step', type=float, default=1.0, help='TOF step in days (can be fractional)')
    p.add_argument('--out-dir', default='results', help='Directory to save outputs (default: results/)')
    p.add_argument('--out-npz', default='porkchop_output.npz', help='Output .npz filename')
    p.add_argument('--out-png', default='porkchop.png', help='Output PNG filename')
    p.add_argument('--cmin', type=float, default=10.0, help='Minimum C3 value to display (values below rendered white)')
    p.add_argument('--cmax', type=float, default=100.0, help='Maximum C3 value to display (values above rendered white)')
    p.add_argument('--tof-contour-step', type=int, default=50, help='Step (days) between TOF contour labels')
    p.add_argument('--interactive', action='store_true', help='Run in interactive prompt mode')
    # (batch mode removed; single-run script)
    return p.parse_args()


def main():
    args = parse_args()

    # If user requested interactive mode or called without args, enter prompt-driven mode
    if args.interactive or len(sys.argv) == 1:
        args = interactive_prompt(args)

    # Ensure base output directory exists
    os.makedirs(args.out_dir, exist_ok=True)

    # Ensure base output directory exists, then create a timestamped subfolder
    os.makedirs(args.out_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    # If the user provided a directory that already includes a trailing separator or a timestamp,
    # we still create a fresh subfolder to avoid accidental overwrite.
    run_subdir = os.path.join(args.out_dir, ts)
    os.makedirs(run_subdir, exist_ok=True)
    print(f'Outputs will be written into: {run_subdir}')

    # (batch mode removed)

    print('Computing grid: dep %s..%s step %s d, tof %s..%s step %s d' % (
        args.start_date, args.end_date, args.dep_step, args.min_tof, args.max_tof, args.tof_step))

    dep_times, tof_days, C3, vinf_dep, vinf_arr, branch_used = compute_grid(
        args.dep_body, args.arr_body, args.start_date, args.end_date, args.dep_step,
        int(args.min_tof), int(args.max_tof), args.tof_step
    )

    # Build output file paths inside the timestamped run_subdir and execute the compute+plot
    out_npz = args.out_npz if os.path.isabs(args.out_npz) else os.path.join(run_subdir, args.out_npz)
    np.savez(out_npz,
             dep_times=[t.tdb.isot for t in dep_times],
             tof_days=tof_days,
             C3=C3,
             vinf_dep=vinf_dep,
             vinf_arr=vinf_arr,
             branch_used=branch_used)
    print('Saved grid to', out_npz)

    out_png = args.out_png if os.path.isabs(args.out_png) else os.path.join(run_subdir, args.out_png)
    # Matplotlib contour/fill requires at least a 2x2 grid. For tiny smoke tests (1x1)
    # skip plotting and inform the user. The .npz is still saved.
    if C3.shape[0] < 2 or C3.shape[1] < 2:
        print(f'Grid shape {C3.shape} too small for contour plot; skipping plot. .npz saved to {out_npz}')
    else:
        print('Generating plot ->', out_png)
        plot_porkchop(dep_times, tof_days, C3, outname=out_png, contour_levels=60,
                      tof_contour_step=args.tof_contour_step, cmin=args.cmin, cmax=args.cmax,
                      dep_body=args.dep_body, arr_body=args.arr_body)
        print('Plot saved to', out_png)


def _prompt(prompt_text: str, default: str = '') -> str:
    try:
        raw = input(f"{prompt_text} [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print('\nAborted by user')
        sys.exit(1)
    return raw if raw else default


def interactive_prompt(parsed_args):
    """Prompt the user interactively for inputs with validation and return a namespace-like object.

    Accepts the partially parsed args (to reuse defaults) and returns an object with the required attributes.
    """
    from types import SimpleNamespace
    ns = SimpleNamespace()

    print('Interactive porkchop run — enter values or press Enter to accept defaults')

    # Departure body
    ns.dep_body = _prompt('Departure body (NAIF id or name)', getattr(parsed_args, 'dep_body', '399'))
    ns.arr_body = _prompt('Arrival body (NAIF id or name)', getattr(parsed_args, 'arr_body', '4'))

    # Dates: validate using astropy.Time
    while True:
        sdate = _prompt('Start date (YYYY-MM-DD or ISO)', getattr(parsed_args, 'start_date', '2035-06-25'))
        try:
            _ = Time(sdate)
            ns.start_date = sdate
            break
        except Exception as e:
            print('Invalid start date format:', e)
            print('Please try again (e.g. 2035-06-25 or 2035-06-25T00:00:00)')

    while True:
        edate = _prompt('End date (YYYY-MM-DD or ISO)', getattr(parsed_args, 'end_date', ns.start_date))
        try:
            t_end = Time(edate)
            t_start = Time(ns.start_date)
            if t_end < t_start:
                print('End date must be the same or after the start date. Please try again.')
                continue
            ns.end_date = edate
            break
        except Exception as e:
            print('Invalid end date format:', e)
            print('Please try again')

    # Steps and TOF: numeric validation
    def _float_input(prompt_name, default_val, min_val=None):
        while True:
            val = _prompt(prompt_name, str(default_val))
            try:
                f = float(val)
                if min_val is not None and f <= min_val:
                    print(f'Value must be greater than {min_val}; got {f}. Try again.')
                    continue
                return f
            except ValueError:
                print('Invalid number, please try again.')

    ns.dep_step = _float_input('Departure step (days)', getattr(parsed_args, 'dep_step', 1.0), min_val=0.0)
    ns.tof_step = _float_input('TOF step (days)', getattr(parsed_args, 'tof_step', 1.0), min_val=0.0)
    ns.min_tof = _float_input('Min TOF (days)', getattr(parsed_args, 'min_tof', 180.0), min_val=-1e9)
    # Ensure max_tof is >= min_tof
    while True:
        ns.max_tof = _float_input('Max TOF (days)', getattr(parsed_args, 'max_tof', 210.0), min_val=ns.min_tof - 1.0)
        if ns.max_tof < ns.min_tof:
            print('Max TOF must be >= Min TOF. Please try again.')
            continue
        break

    # Output options
    ns.out_dir = _prompt('Output directory', getattr(parsed_args, 'out_dir', 'results'))
    ns.out_npz = _prompt('Output .npz filename', getattr(parsed_args, 'out_npz', 'porkchop_output.npz'))
    ns.out_png = _prompt('Output PNG filename', getattr(parsed_args, 'out_png', 'porkchop.png'))

    ns.cmap = 'cividis'
    ns.tof_contour_step = getattr(parsed_args, 'tof_contour_step', 50)
    ns.cmin = getattr(parsed_args, 'cmin', 10.0)
    ns.cmax = getattr(parsed_args, 'cmax', 100.0)
    ns.batch_file = getattr(parsed_args, 'batch_file', '')

    return ns


if __name__ == '__main__':
    main()
