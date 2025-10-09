# lambertlab/viz/ui.py
"""UI functions for lambertlab CLI commands."""

import sys
import csv
import json
import os
import hashlib
import numpy as np
from astropy import units as u
from astropy.time import Time
from pathlib import Path

from ..core.spice_io import load_kernels, rv_helio_spice
from ..flows.em_only import screen_em_grid_cached
from ..flows.flyby import compute_flyby
from ..core.lambert_io import solve_leg
from ..core.config import MU_SUN, MU_MARS, R_MARS
from ..viz.porkchop import plot_c3


def progress_bar(current, total, phase):
    percent = int(100 * current / total)
    bar = '#' * (percent // 2) + '.' * (50 - percent // 2)
    print(f'\r{phase} {percent}% [{bar}] {current}/{total}', end='', flush=True)
    if current == total:
        print()


def print_kernel_status(kernels):
    """Print kernel list and confirm LSK presence."""
    print("Loaded kernels:")
    for k in kernels:
        print(f"  {k}")
    
    # Check for LSK
    has_lsk = any('tls' in k.lower() for k in kernels)
    if not has_lsk:
        print("ERROR: No leapseconds kernel (.tls) found!", file=sys.stderr)
        print("Please include naif0012.tls or similar LSK kernel.", file=sys.stderr)
        sys.exit(2)
    print("LSK kernel confirmed")


def compute_array_hash(arr, name):
    """Compute hash of numpy array for reproducibility."""
    if isinstance(arr, np.ndarray):
        # Flatten and convert to bytes
        data = arr.flatten().tobytes()
        hash_val = hashlib.sha256(data).hexdigest()[:16]  # Short hash
        print(f"Hash({name}): {hash_val}")
        return hash_val
    return None


def check_mock_usage(args):
    """Check for mock usage and warn if not allowed."""
    using_mock = getattr(args, 'use_mock', False)
    allow_mock = getattr(args, 'allow_mock', False)
    
    if using_mock:
        if not allow_mock:
            print("=" * 60, file=sys.stderr)
            print("WARNING: Using mock flyby model!", file=sys.stderr)
            print("This produces physics-incomplete results.", file=sys.stderr)
            print("Add --allow-mock to suppress this warning.", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            return True  # Indicates physics-incomplete
    return False


def echo_time_scale_conversion(input_time, input_scale, output_time):
    """Echo time scale conversion in header."""
    if input_scale.upper() != 'TDB':
        print(f"Time scale: {input_time} ({input_scale}) → {output_time.tdb.isot} (TDB)")


def validate_kernels(args):
    import spiceypy as spice
    # Check LSK
    try:
        spice.et2utc(0, 'C', 0)
    except:
        print("Load a leapseconds kernel (e.g., naif0012.tls)", file=sys.stderr)
        sys.exit(2)
    
    # Determine bodies and epochs based on subcommand
    bodies = set()
    epochs = []
    
    if hasattr(args, 'dep_start'):  # em-grid
        bodies.update(['399', '499'])
        dep_start = Time(args.dep_start, scale=args.time_scale.lower())
        dep_end = Time(args.dep_end, scale=args.time_scale.lower())
        arr_start = dep_start + args.tof_min * u.day
        arr_end = dep_end + args.tof_max * u.day
        epochs.extend([dep_start, dep_end, arr_start, arr_end])
    elif hasattr(args, 'epoch'):  # flyby
        bodies.update(['499'])
    import spiceypy as spice
    # Check LSK
    try:
        spice.et2utc(0, 'C', 0)
    except:
        print("Load a leapseconds kernel (e.g., naif0012.tls)", file=sys.stderr)
        sys.exit(2)
    
    # Determine bodies and epochs based on subcommand
    bodies = set()
    epochs = []
    
    if hasattr(args, 'dep_start'):  # em-grid
        bodies.update(['399', '499'])
        dep_start = Time(args.dep_start, scale=args.time_scale.lower())
        dep_end = Time(args.dep_end, scale=args.time_scale.lower())
        arr_start = dep_start + args.tof_min * u.day
        arr_end = dep_end + args.tof_max * u.day
        epochs.extend([dep_start, dep_end, arr_start, arr_end])
    elif hasattr(args, 'epoch'):  # flyby
        bodies.update(['499'])
        epoch = Time(args.epoch, scale=args.time_scale.lower())
        epochs.append(epoch)
    elif hasattr(args, 'dep_epoch'):  # mc-screen
        bodies.update([args.dep_id, args.arr_id])
        dep_epoch = Time(args.dep_epoch, scale=args.time_scale.lower())
        arr_start, arr_end = args.arr_window.split(':')
        arr_start = Time(arr_start, scale=args.time_scale.lower())
        arr_end = Time(arr_end, scale=args.time_scale.lower())
        epochs.extend([dep_epoch, arr_start, arr_end])
    elif hasattr(args, 'em_dep_start'):  # emc-chain
        bodies.update(['399', '499', '20000001'])
        dep_start = Time(args.em_dep_start, scale=args.time_scale.lower())
        dep_end = Time(args.em_dep_end, scale=args.time_scale.lower())
        arr_start = dep_start + args.em_tof_min * u.day
        arr_end = dep_end + args.em_tof_max * u.day
        mc_arr_start = arr_start + args.mc_tof_min * u.day
        mc_arr_end = arr_end + args.mc_tof_max * u.day
        epochs.extend([dep_start, dep_end, arr_start, arr_end, mc_arr_start, mc_arr_end])
    
    # Check SPK coverage - temporarily disabled for de440.bsp
    # for body in bodies:
    #     try:
    #         cover = spice.spkcov(f'{body}.bsp', int(body))
    #         if cover:
    #             min_et = min(cover)
    #             max_et = max(cover)
    #             print(f"SPK coverage for {body}: {spice.et2utc(min_et, 'C', 0)} to {spice.et2utc(max_et, 'C', 0)}")
    #             # Check if epochs are within coverage
    #             for epoch in epochs:
    #                 et = spice.utc2et(epoch.utc.isot)
    #                 if not (min_et <= et <= max_et):
    #                     print(f"Warning: Epoch {epoch.utc.isot} for body {body} is outside SPK coverage", file=sys.stderr)
    #         else:
    #             print(f"No SPK coverage for {body}", file=sys.stderr)
    #     except Exception as e:
    #         print(f"SPK coverage check failed for {body}: {e}", file=sys.stderr)


def run_em_grid(args):
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Guardrails: Print kernel status
    print_kernel_status(args.kernels or [])
    
    # Guardrails: Check mock usage
    check_mock_usage(args)
    
    # Validate
    validate_kernels(args)
    
    dep_start = Time(args.dep_start, scale=args.time_scale.lower())
    dep_end = Time(args.dep_end, scale=args.time_scale.lower())
    
    # Guardrails: Echo time scale conversion
    echo_time_scale_conversion(args.dep_start, args.time_scale, dep_start)
    echo_time_scale_conversion(args.dep_end, args.time_scale, dep_end)
    
    dep_times, tof_days, c3_grid, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, vM_x, vM_y, vM_z, rM_x, rM_y, rM_z = \
        screen_em_grid_cached(dep_start, dep_end, args.dep_step, args.tof_min, args.tof_max, args.tof_step, dep_body=str(args.dep_id), arr_body=str(args.arr_id), n_workers=args.workers)

    # Guardrails: Compute array hash for reproducibility
    compute_array_hash(c3_grid, 'c3_grid')

    # Apply C3 cap
    if args.c3_cap is not None:
        mask = c3_grid > args.c3_cap
        c3_grid[mask] = np.nan

    # Find minima
    min_idx = np.unravel_index(np.nanargmin(c3_grid), c3_grid.shape)
    idep, jtof = min_idx
    min_c3 = c3_grid[idep, jtof]
    min_dep_epoch = dep_times[idep]
    min_arr_epoch = min_dep_epoch + tof_days[jtof] * u.day
    min_vinf_in = [vin_x[idep, jtof], vin_y[idep, jtof], vin_z[idep, jtof]]
    min_vinf_out = [vout_x[idep, jtof], vout_y[idep, jtof], vout_z[idep, jtof]]

    # Stdout
    if args.format == 'json':
        out = {
            'dep_count': int(dep_times.size),
            'tof_count': int(len(tof_days)),
            'c3_min': float(min_c3) if np.isfinite(min_c3) else None,
            'frame': args.frame,
            'time_scale': args.time_scale
        }
        print(json.dumps(out, indent=2))
    elif args.format in ['table', 'csv']:
        writer = csv.writer(sys.stdout) if args.format == 'csv' else None
        header = ['dep_tdb', 'tof_days', 'c3', 'vinf_in_x', 'vinf_in_y', 'vinf_in_z', 'vinf_out_x', 'vinf_out_y', 'vinf_out_z', 'arr_tdb', 'dep_idx', 'tof_idx']
        if args.format == 'table':
            print('\t'.join(header))
        else:
            writer.writerow(header)
        for i in range(len(dep_times)):
            for j in range(len(tof_days)):
                if np.isfinite(c3_grid[i, j]):
                    arr_epoch = dep_times[i] + tof_days[j] * u.day
                    row = [
                        dep_times[i].tdb.isot,
                        float(tof_days[j]),
                        c3_grid[i, j],
                        vin_x[i, j], vin_y[i, j], vin_z[i, j],
                        vout_x[i, j], vout_y[i, j], vout_z[i, j],
                        arr_epoch.tdb.isot,
                        i, j
                    ]
                    if args.format == 'table':
                        print('\t'.join(str(x) for x in row))
                    else:
                        writer.writerow(row)

    # Save
    if args.save:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        # em_grid.csv
        csv_path = os.path.join(args.outdir, 'em_grid.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['dep_tdb', 'tof_days', 'c3', 'vinf_in_x', 'vinf_in_y', 'vinf_in_z', 'vinf_out_x', 'vinf_out_y', 'vinf_out_z', 'arr_tdb', 'dep_idx', 'tof_idx'])
            for i in range(len(dep_times)):
                for j in range(len(tof_days)):
                    if np.isfinite(c3_grid[i, j]):
                        arr_epoch = dep_times[i] + tof_days[j] * u.day
                        writer.writerow([
                            dep_times[i].tdb.isot,
                            float(tof_days[j]),
                            c3_grid[i, j],
                            vin_x[i, j], vin_y[i, j], vin_z[i, j],
                            vout_x[i, j], vout_y[i, j], vout_z[i, j],
                            arr_epoch.tdb.isot,
                            i, j
                        ])
        # em_minima.json
        min_data = {
            'dep_tdb': min_dep_epoch.tdb.isot,
            'tof_days': float(tof_days[jtof]),
            'c3': float(min_c3),
            'vinf_in_vec_kms': min_vinf_in,
            'vinf_out_vec_kms': min_vinf_out,
            'arr_tdb': min_arr_epoch.tdb.isot,
        }
        min_data['hash'] = hashlib.sha256(json.dumps(min_data, sort_keys=True).encode()).hexdigest()
        min_path = os.path.join(args.outdir, 'em_minima.json')
        with open(min_path, 'w') as f:
            json.dump([min_data], f, indent=2)
        
        # Generate and save porkchop plot
        png_path = os.path.join(args.outdir, 'porkchop.png')
        plot_c3(dep_times, tof_days, c3_grid, png_path)


def run_flyby(args):
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Guardrails: Print kernel status
    print_kernel_status(args.kernels or [])
    
    # Guardrails: Check mock usage
    check_mock_usage(args)
    
    # Validate
    validate_kernels(args)
    
    epoch = Time(args.epoch, scale=args.time_scale.lower())
    
    # Guardrails: Echo time scale conversion
    echo_time_scale_conversion(args.epoch, args.time_scale, epoch)
    
    vinf_in = np.array(args.vinf_in)
    b_hat = np.array(args.b_hat) if args.b_hat else None
    
    # Get flyby body's heliocentric state at the epoch
    r_planet, v_planet = rv_helio_spice(str(args.planet_id), epoch)
    
    # Compute mu_planet from r_body (GM = 4/3 * π * ρ * r^3 for estimated density, 
    # but better to use SPICE or passed value). For now, use MU_MARS as default.
    # TODO: Make this body-agnostic by querying SPICE GM or using passed mu_planet
    mu_planet = MU_MARS  # Will generalize later
    r_body = args.r_body if args.r_body else R_MARS
    
    fly = compute_flyby(
        epoch.tdb, 
        r_planet, 
        v_planet, 
        mu_planet, 
        vinf_in, 
        (r_body + args.alt_min, r_body + 10000.0), 
        str(args.target_id),  # Target body for post-flyby trajectory
        MU_SUN, 
        (epoch + 200*u.day, epoch + 1000*u.day), 
        max_samples=200, 
        seed=args.seed
    )
    
    if not fly.success:
        print(f"No feasible flyby given min altitude {args.alt_min} km; try higher v∞ or lower alt.", file=sys.stderr)
        sys.exit(1)
    
    vinf_in_mag = np.linalg.norm(vinf_in)
    turn_deg = np.degrees(fly.turn_angle) if fly.turn_angle is not None else None
    rp_km = fly.rp if fly.rp is not None else None
    
    # Guardrails: Compute array hash for reproducibility (on vinf_in vector)
    compute_array_hash(vinf_in, 'vinf_in')
    
    if not fly.success:
        print(f"No feasible flyby given min altitude {args.alt_min} km; try higher v∞ or lower alt.", file=sys.stderr)
        sys.exit(1)
    
    vinf_in_mag = np.linalg.norm(vinf_in)
    turn_deg = np.degrees(fly.turn_angle) if fly.turn_angle is not None else None
    rp_km = fly.rp if fly.rp is not None else None
    
    # Stdout
    if args.format == 'json':
        out = {
            'vinf_in_mag': float(vinf_in_mag),
            'turn_deg': float(turn_deg) if turn_deg is not None else None,
            'rp_km': float(rp_km) if rp_km is not None else None,
            'success': fly.success
        }
        print(json.dumps(out, indent=2))
    elif args.format == 'table':
        print('vinf_in_mag\tturn_deg\trp_km\tsuccess')
        print(f'{vinf_in_mag:.3f}\t{turn_deg:.3f}\t{rp_km:.1f}\t{fly.success}')
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(['vinf_in_mag', 'turn_deg', 'rp_km', 'success'])
        writer.writerow([vinf_in_mag, turn_deg, rp_km, fly.success])
    
    # Save
    if args.save:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        data = {
            'epoch': epoch.tdb.isot,
            'vinf_in': vinf_in.tolist(),
            'b_hat': b_hat.tolist() if b_hat is not None else None,
            'vinf_in_mag': float(vinf_in_mag),
            'turn_deg': float(turn_deg) if turn_deg is not None else None,
            'rp_km': float(rp_km) if rp_km is not None else None,
            'success': fly.success
        }
        path = os.path.join(args.outdir, 'flyby.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def run_mc_screen(args):
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Guardrails: Print kernel status
    print_kernel_status(args.kernels or [])
    
    # Guardrails: Check mock usage
    check_mock_usage(args)
    
    # Validate
    validate_kernels(args)
    
    dep_epoch = Time(args.dep_epoch, scale=args.time_scale.lower())
    arr_start, arr_end = args.arr_window.split(':')
    arr_start = Time(arr_start, scale=args.time_scale.lower())
    arr_end = Time(arr_end, scale=args.time_scale.lower())
    
    # Guardrails: Echo time scale conversion
    echo_time_scale_conversion(args.dep_epoch, args.time_scale, dep_epoch)
    echo_time_scale_conversion(arr_start, args.time_scale, arr_start)
    echo_time_scale_conversion(arr_end, args.time_scale, arr_end)
    
    tof_days = np.arange(args.tof_min, args.tof_max + args.tof_step, args.tof_step)
    table_data = []
    for i, tof in enumerate(tof_days):
        progress_bar(i+1, len(tof_days), 'mc-screen')
        arr_epoch = dep_epoch + tof * u.day
        if arr_epoch < arr_start or arr_epoch > arr_end:
            continue
        r_dep, v_dep = rv_helio_spice(str(args.dep_id), dep_epoch)
        r_arr, v_arr = rv_helio_spice(str(args.arr_id), arr_epoch)
        v1, v2 = solve_leg(r_dep * u.km, r_arr * u.km, tof * u.day)
        vinf_arr = (v2 - v_arr * u.km/u.s).to(u.km/u.s).value
        c3 = float(np.dot(vinf_arr, vinf_arr))
        if args.c3_cap is not None and c3 > args.c3_cap:
            continue
        row = [
            dep_epoch.tdb.isot,
            float(tof),
            c3,
            arr_epoch.tdb.isot,
            0,  # dep_idx
            i   # tof_idx
        ]
        table_data.append(row)
    progress_bar(len(tof_days), len(tof_days), 'mc-screen')
    
    # Guardrails: Compute array hash for reproducibility (on c3 values)
    c3_values = np.array([row[2] for row in table_data])
    compute_array_hash(c3_values, 'c3_values')
    table_data = []
    for i, tof in enumerate(tof_days):
        progress_bar(i+1, len(tof_days), 'mc-screen')
        arr_epoch = dep_epoch + tof * u.day
        if arr_epoch < arr_start or arr_epoch > arr_end:
            continue
        r_dep, v_dep = rv_helio_spice(str(args.dep_id), dep_epoch)
        r_arr, v_arr = rv_helio_spice(str(args.arr_id), arr_epoch)
        v1, v2 = solve_leg(r_dep * u.km, r_arr * u.km, tof * u.day)
        vinf_arr = (v2 - v_arr * u.km/u.s).to(u.km/u.s).value
        c3 = float(np.dot(vinf_arr, vinf_arr))
        if args.c3_cap is not None and c3 > args.c3_cap:
            continue
        row = [
            dep_epoch.tdb.isot,
            float(tof),
            c3,
            arr_epoch.tdb.isot,
            0,  # dep_idx
            i   # tof_idx
        ]
        table_data.append(row)
    progress_bar(len(tof_days), len(tof_days), 'mc-screen')
    
    # Stdout
    if args.format == 'json':
        data = {
            'c3_cap': args.c3_cap,
            'results': table_data,
            'frame': args.frame,
            'time_scale': args.time_scale
        }
        print(json.dumps(data, indent=2))
    elif args.format == 'table':
        print('\t'.join(['dep_tdb', 'tof_days', 'c3', 'arr_tdb', 'dep_idx', 'tof_idx']))
        for row in table_data:
            print('\t'.join(map(str, row)))
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(['dep_tdb', 'tof_days', 'c3', 'arr_tdb', 'dep_idx', 'tof_idx'])
        for row in table_data:
            writer.writerow(row)
    
    # Save
    if args.save:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        # mc_grid.csv
        csv_path = os.path.join(args.outdir, 'mc_grid.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['dep_tdb', 'tof_days', 'c3', 'arr_tdb', 'dep_idx', 'tof_idx'])
            for row in table_data:
                writer.writerow(row)
        # mc_minima.json
        if table_data:
            min_row = min(table_data, key=lambda x: x[2] if x[2] is not None else float('inf'))
            min_data = {
                'dep_tdb': min_row[0],
                'tof_days': min_row[1],
                'c3': min_row[2],
                'vinf_in_vec_kms': None,
                'vinf_out_vec_kms': None,
                'arr_tdb': min_row[3],
            }
            min_data['hash'] = hashlib.sha256(json.dumps(min_data, sort_keys=True).encode()).hexdigest()
            min_path = os.path.join(args.outdir, 'mc_minima.json')
            with open(min_path, 'w') as f:
                json.dump([min_data], f, indent=2)


def run_emc_chain(args):
    # Guardrails: Check mock usage first (before kernel loading)
    physics_incomplete = check_mock_usage(args)
    if physics_incomplete and not args.allow_mock:
        sys.exit(1)
    
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Guardrails: Print kernel status
    print_kernel_status(args.kernels or [])
    
    # Validate
    validate_kernels(args)
    
    # Compute EM grid
    dep_start = Time(args.em_dep_start, scale=args.time_scale.lower())
    dep_end = Time(args.em_dep_end, scale=args.time_scale.lower())
    
    # Guardrails: Echo time scale conversion
    echo_time_scale_conversion(args.em_dep_start, args.time_scale, dep_start)
    echo_time_scale_conversion(args.em_dep_end, args.time_scale, dep_end)
    
    dep_times, tof_days, c3_grid, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, vM_x, vM_y, vM_z, rM_x, rM_y, rM_z = \
        screen_em_grid_cached(dep_start, dep_end, args.em_dep_step, args.em_tof_min, args.em_tof_max, args.em_tof_step, dep_body='399', arr_body='499', n_workers=args.workers)

    # Guardrails: Compute array hash for EM grid
    compute_array_hash(c3_grid, 'em_c3_grid')

    # Find N best candidates
    flat_indices = np.argsort(c3_grid.flatten())[:args.candidates]
    candidates = []
    for idx in flat_indices:
        idep, jtof = np.unravel_index(idx, c3_grid.shape)
        if np.isfinite(c3_grid[idep, jtof]):
            candidates.append((idep, jtof))

    table_data = []
    summary_data = []

    for idep, jtof in candidates:
        dep_epoch = dep_times[idep]
        tof_val = tof_days[jtof]
        arr_epoch = dep_epoch + tof_val * u.day
        c3_em = c3_grid[idep, jtof]
        rM = np.array([rM_x[idep, jtof], rM_y[idep, jtof], rM_z[idep, jtof]])
        vM = np.array([vM_x[idep, jtof], vM_y[idep, jtof], vM_z[idep, jtof]])
        vinf_in = np.array([vin_x[idep, jtof], vin_y[idep, jtof], vin_z[idep, jtof]])

        # Determine b_hat
        if args.b_hat_mode == 'pro':
            b_hat = np.array([0, 0, 1])
        elif args.b_hat_mode == 'retro':
            b_hat = np.array([0, 0, -1])
        else:  # auto
            b_hat = np.array([0, 0, 1])  # placeholder

        # Run flyby
        fly = compute_flyby(arr_epoch.tdb, rM, vM, MU_MARS, vinf_in, (R_MARS + args.min_alt, R_MARS + 10000.0), '20000001', MU_SUN, (arr_epoch + 200*u.day, arr_epoch + 1000*u.day), max_samples=200, seed=args.seed or 42)
        if not fly.success:
            print(f"No feasible flyby given min altitude {args.min_alt} km; try higher v∞ or lower alt.", file=sys.stderr)
            continue

        vinf_in_mag = np.linalg.norm(vinf_in)
        turn_deg = np.degrees(fly.turn_angle) if fly.turn_angle is not None else None
        rp_km = fly.rp if fly.rp is not None else None

        # Run MC screening
        mc_tof_days = np.arange(args.mc_tof_min, args.mc_tof_max + args.mc_tof_step, args.mc_tof_step)
        for i, mc_tof in enumerate(mc_tof_days):
            progress_bar(i+1, len(mc_tof_days), 'emc-chain')
            mc_arr_epoch = arr_epoch + mc_tof * u.day
            r_dep, v_dep = rv_helio_spice('499', arr_epoch)  # Mars at flyby arrival
            r_arr, v_arr = rv_helio_spice('20000001', mc_arr_epoch)
            try:
                v1, v2 = solve_leg(r_dep * u.km, r_arr * u.km, mc_tof * u.day)
                vinf_arr = (v2 - v_arr * u.km/u.s).to(u.km/u.s).value
                c3_mc = float(np.dot(vinf_arr, vinf_arr))
                success = True
            except:
                c3_mc = None
                success = False

            row = [
                dep_epoch.tdb.isot,
                float(tof_val),
                float(c3_em),
                float(vinf_in_mag),
                float(turn_deg) if turn_deg is not None else None,
                float(rp_km) if rp_km is not None else None,
                arr_epoch.tdb.isot,
                mc_arr_epoch.tdb.isot,
                float(mc_tof),
                float(c3_mc) if c3_mc is not None else None,
                success
            ]
            table_data.append(row)

            summary_data.append({
                'em_dep': dep_epoch.tdb.isot,
                'em_tof': float(tof_val),
                'c3_em': float(c3_em),
                'vinf_in_mag': float(vinf_in_mag),
                'turn_deg': float(turn_deg) if turn_deg is not None else None,
                'rp_km': float(rp_km) if rp_km is not None else None,
                'mc_dep': arr_epoch.tdb.isot,
                'mc_arr': mc_arr_epoch.tdb.isot,
                'mc_tof': float(mc_tof),
                'c3_mc': float(c3_mc) if c3_mc is not None else None,
                'success': success
            })
        progress_bar(len(mc_tof_days), len(mc_tof_days), 'emc-chain')

    # Guardrails: Compute array hash for final results
    if table_data:
        c3_em_values = np.array([row[2] for row in table_data])
        c3_mc_values = np.array([row[9] if row[9] is not None else np.nan for row in table_data])
        compute_array_hash(c3_em_values, 'emc_c3_em')
        compute_array_hash(c3_mc_values, 'emc_c3_mc')

    # Export summary
    if args.export_summary:
        with open(args.export_summary, 'w') as f:
            json.dump({'chains': summary_data}, f, indent=2)

    # Export CSV
    if args.export_csv:
        with open(args.export_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['dep_tdb', 'em_tof', 'c3_em', 'vinf_in_mag', 'turn_deg', 'rp_km', 'mc_dep_tdb', 'mc_arr_tdb', 'mc_tof', 'c3_mc', 'success'])
            for row in table_data:
                writer.writerow(row)

    # Stdout
    if args.format == 'json':
        data = {
            'chains': summary_data,
            'frame': args.frame,
            'time_scale': args.time_scale
        }
        print(json.dumps(data, indent=2))
    elif args.format == 'table':
        print('\t'.join(['dep_tdb', 'em_tof', 'c3_em', 'vinf_in_mag', 'turn_deg', 'rp_km', 'mc_dep_tdb', 'mc_arr_tdb', 'mc_tof', 'c3_mc', 'success']))
        for row in table_data:
            print('\t'.join(map(str, row)))
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(['dep_tdb', 'em_tof', 'c3_em', 'vinf_in_mag', 'turn_deg', 'rp_km', 'mc_dep_tdb', 'mc_arr_tdb', 'mc_tof', 'c3_mc', 'success'])
        for row in table_data:
            writer.writerow(row)

    # Save
    if args.save:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        # emc_summary.json
        summary_path = os.path.join(args.outdir, 'emc_summary.json')
        with open(summary_path, 'w') as f:
            json.dump({'chains': summary_data}, f, indent=2)


def run_chain3(args):
    """
    Generic three-body chain: Origin → Flyby → Destination
    Implements comprehensive gravity assist trajectory search.
    """
    # Check if checkpointed mode is requested
    if hasattr(args, 'checkpoint') and args.checkpoint:
        run_chain3_checkpointed_mode(args)
        return
    
    # Otherwise run original mode
    run_chain3_original(args)


def run_chain3_checkpointed_mode(args):
    """Run chain3 in checkpointed/resumable mode."""
    from ..flows.chain3_tiled import Chain3Config, run_chain3_checkpointed
    from pathlib import Path
    
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Parse input ranges
    dep_start_str, dep_end_str = args.dep_window.split(':')
    leg1_tof_min, leg1_tof_max, leg1_tof_step = map(int, args.leg1_tof.split(':'))
    leg2_tof_min, leg2_tof_max, leg2_tof_step = map(int, args.leg2_tof.split(':'))
    rp_min, rp_max = map(float, args.rp_bounds.split(':'))
    btheta_min, btheta_max, btheta_n = map(float, args.bplane_theta.split(':'))
    
    # Build config
    config = Chain3Config(
        dep_body=args.dep_body,
        flyby_body=args.flyby_body,
        arr_body=args.arr_body,
        dep_window_start=dep_start_str,
        dep_window_end=dep_end_str,
        dep_step=args.dep_step,
        leg1_tof_min=leg1_tof_min,
        leg1_tof_max=leg1_tof_max,
        leg1_tof_step=leg1_tof_step,
        leg2_tof_min=leg2_tof_min,
        leg2_tof_max=leg2_tof_max,
        leg2_tof_step=leg2_tof_step,
        rp_min_km=rp_min,
        rp_max_km=rp_max,
        bplane_theta_min_deg=btheta_min,
        bplane_theta_max_deg=btheta_max,
        bplane_theta_n=int(btheta_n),
        tile_size=args.tile_size if hasattr(args, 'tile_size') else 10,
        checkpoint_sec=args.checkpoint_sec if hasattr(args, 'checkpoint_sec') else 30,
        max_solutions=args.max_solutions,
        dv_tol_ms=args.dv_tol,
        n_workers=args.workers,
        seed=args.seed
    )
    
    outdir = Path(args.outdir)
    resume = args.resume if hasattr(args, 'resume') else True
    
    # Run checkpointed computation
    run_chain3_checkpointed(config, outdir, resume=resume)


def run_chain3_original(args):
    """Original (non-checkpointed) chain3 implementation."""
    # Load kernels
    if args.kernels:
        load_kernels(args.kernels)
    
    # Guardrails: Print kernel status
    print_kernel_status(args.kernels or [])
    
    # Validate
    validate_kernels(args)
    
    # Parse input ranges
    dep_start_str, dep_end_str = args.dep_window.split(':')
    leg1_tof_min, leg1_tof_max, leg1_tof_step = map(int, args.leg1_tof.split(':'))
    leg2_tof_min, leg2_tof_max, leg2_tof_step = map(int, args.leg2_tof.split(':'))
    rp_min, rp_max = map(float, args.rp_bounds.split(':'))
    btheta_min, btheta_max, btheta_n = map(float, args.bplane_theta.split(':'))
    
    # Convert to Time objects
    dep_start = Time(dep_start_str, scale=args.time_scale.lower())
    dep_end = Time(dep_end_str, scale=args.time_scale.lower())
    
    # Guardrails: Echo time scale conversion
    echo_time_scale_conversion(dep_start_str, args.time_scale, dep_start)
    echo_time_scale_conversion(dep_end_str, args.time_scale, dep_end)
    
    print(f"\n=== Three-Body Chain Configuration ===")
    print(f"Departure body: {args.dep_body}")
    print(f"Flyby body: {args.flyby_body}")
    print(f"Arrival body: {args.arr_body}")
    print(f"Departure window: {dep_start.iso} to {dep_end.iso}")
    print(f"Leg 1 TOF: {leg1_tof_min}-{leg1_tof_max} days (step {leg1_tof_step})")
    print(f"Leg 2 TOF: {leg2_tof_min}-{leg2_tof_max} days (step {leg2_tof_step})")
    print(f"Periapsis bounds: {rp_min:.1f}-{rp_max:.1f} km")
    print(f"B-plane theta: {btheta_min}° to {btheta_max}° ({int(btheta_n)} samples)")
    print()
    
    # STEP 1: Leg 1 scan (dep -> flyby)
    print("STEP 1: Computing Leg 1 (Departure -> Flyby) grid...")
    from ..flows.em_only import screen_em_grid_cached
    
    dep_times, tof1_days, c3_leg1, vout_x, vout_y, vout_z, vin_x, vin_y, vin_z, \
        vFB_x, vFB_y, vFB_z, rFB_x, rFB_y, rFB_z = screen_em_grid_cached(
            dep_start, dep_end, args.dep_step,
            leg1_tof_min, leg1_tof_max, leg1_tof_step,
            dep_body=str(args.dep_body), arr_body=str(args.flyby_body),
            n_workers=args.workers
        )
    
    # Guardrails: Compute array hash for Leg 1
    compute_array_hash(c3_leg1, 'chain3_leg1_c3')
    
    print(f"Leg 1 grid: {len(dep_times)} × {len(tof1_days)} = {c3_leg1.size} points")
    finite_count = np.sum(np.isfinite(c3_leg1))
    print(f"Feasible Leg 1 trajectories: {finite_count} ({100*finite_count/c3_leg1.size:.1f}%)")
    
    # STEP 2: Flyby map & Leg 2 scan
    print("\nSTEP 2: Computing flyby maps and Leg 2 trajectories...")
    
    # Prepare B-plane theta grid
    theta_grid = np.linspace(np.radians(btheta_min), np.radians(btheta_max), int(btheta_n))
    rp_grid = np.linspace(rp_min, rp_max, 10)  # periapsis radius samples
    
    # Storage for all solutions
    all_solutions = []
    leg1_data = []
    bplane_data = []
    leg2_data = []
    
    # Iterate over Leg 1 candidates
    total_leg1 = np.sum(np.isfinite(c3_leg1))
    processed = 0
    
    for idep in range(len(dep_times)):
        for jtof1 in range(len(tof1_days)):
            if not np.isfinite(c3_leg1[idep, jtof1]):
                continue
            
            processed += 1
            if processed % 50 == 0:
                progress_bar(processed, total_leg1, 'chain3')
            
            # Leg 1 parameters
            t_dep = dep_times[idep]
            tof1 = tof1_days[jtof1]
            t_flyby = t_dep + tof1 * u.day
            c3_launch = c3_leg1[idep, jtof1]
            
            # Flyby arrival state
            r_flyby = np.array([rFB_x[idep, jtof1], rFB_y[idep, jtof1], rFB_z[idep, jtof1]])
            v_flyby = np.array([vFB_x[idep, jtof1], vFB_y[idep, jtof1], vFB_z[idep, jtof1]])
            vinf_in_vec = np.array([vin_x[idep, jtof1], vin_y[idep, jtof1], vin_z[idep, jtof1]])
            vinf_in_mag = np.linalg.norm(vinf_in_vec)
            
            # Save Leg 1 data
            leg1_data.append({
                'dep_tdb': t_dep.tdb.isot,
                'tof1_days': float(tof1),
                'flyby_tdb': t_flyby.tdb.isot,
                'c3_km2s2': float(c3_launch),
                'vinf_in_mag_kms': float(vinf_in_mag)
            })
            
            # Try different periapsis radii and B-plane rotations
            for rp in rp_grid:
                # Classical gravity turn angle
                from ..core.config import MU_MARS  # TODO: make body-agnostic
                mu_flyby = MU_MARS
                
                x = 1.0 + (rp * vinf_in_mag**2) / mu_flyby
                if x <= 1.0:
                    continue
                sin_half_delta = 1.0 / x
                if sin_half_delta > 1.0 or sin_half_delta <= 0:
                    continue
                delta = 2.0 * np.arcsin(sin_half_delta)
                
                for theta in theta_grid:
                    # Compute outgoing v-infinity using spherical coordinates
                    # This is the correct gravity assist formula (same as in flyby.py)
                    vinf_in_unit = vinf_in_vec / vinf_in_mag
                    
                    # Build orthonormal basis around vinf_in
                    # e1 is along incoming v_inf, e2 and e3 are perpendicular
                    e1 = vinf_in_unit
                    tmp = np.array([0, 0, 1]) - np.dot([0, 0, 1], e1) * e1
                    if np.linalg.norm(tmp) < 0.1:
                        tmp = np.array([0, 1, 0]) - np.dot([0, 1, 0], e1) * e1
                    e2 = tmp / np.linalg.norm(tmp)
                    e3 = np.cross(e1, e2)
                    
                    # Outgoing v_inf in spherical coordinates:
                    # polar angle = delta (turn angle)
                    # azimuthal angle = theta (rotation around incoming direction)
                    vinf_out_vec = vinf_in_mag * (np.cos(delta) * e1 + 
                                                 np.sin(delta) * (np.cos(theta) * e2 + np.sin(theta) * e3))
                    
                    vinf_out_mag = np.linalg.norm(vinf_out_vec)
                    
                    # Convert to heliocentric post-flyby velocity
                    v_sc_post = v_flyby + vinf_out_vec
                    
                    # Save B-plane data
                    bplane_data.append({
                        'flyby_tdb': t_flyby.tdb.isot,
                        'rp_km': float(rp),
                        'theta_deg': float(np.degrees(theta)),
                        'delta_deg': float(np.degrees(delta)),
                        'vinf_out_mag_kms': float(vinf_out_mag)
                    })
                    
                    # STEP 3: Leg 2 scan (flyby → arrival)
                    for tof2 in range(leg2_tof_min, leg2_tof_max + 1, leg2_tof_step):
                        t_arr = t_flyby + tof2 * u.day
                        
                        # Get arrival body state
                        try:
                            r_arr, v_arr = rv_helio_spice(str(args.arr_body), t_arr)
                        except:
                            continue
                        
                        # Lambert solve from post-flyby state to arrival
                        try:
                            v1, v2 = solve_leg(
                                r_flyby * u.km, r_arr * u.km,
                                tof2 * u.day
                            )
                            
                            # Check if post-flyby velocity matches Lambert initial velocity
                            v1_arr = v1.to(u.km/u.s).value
                            dv_match = np.linalg.norm(v_sc_post - v1_arr)
                            
                            # Skip if mismatch too large (indicates incompatible flyby)
                            if dv_match * 1000 > args.dv_tol:  # convert km/s to m/s
                                continue
                            
                            # Arrival v-infinity
                            vinf_arr_vec = (v2 - v_arr * u.km/u.s).to(u.km/u.s).value
                            vinf_arr_mag = np.linalg.norm(vinf_arr_vec)
                            
                            # Estimate capture delta-V (simple)
                            # For circular orbit: dv = sqrt(2*mu/r + vinf^2) - sqrt(mu/r)
                            # Simplified: just use vinf as proxy
                            est_capture_dv_ms = vinf_arr_mag * 1000  # rough estimate
                            
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
                                'vinf_in_vec_kms': [float(x) for x in vinf_in_vec],
                                'vinf_out_vec_kms': [float(x) for x in vinf_out_vec],
                                'arr_vinf_kms': float(vinf_arr_mag),
                                'est_capture_dv_ms': float(est_capture_dv_ms),
                                'dv_match_ms': float(dv_match * 1000),
                                'score': float(c3_launch + vinf_arr_mag**2)  # simple scoring
                            }
                            
                            all_solutions.append(solution)
                            
                            leg2_data.append({
                                'flyby_tdb': t_flyby.tdb.isot,
                                'tof2_days': float(tof2),
                                'arr_tdb': t_arr.tdb.isot,
                                'vinf_arr_kms': float(vinf_arr_mag)
                            })
                            
                        except Exception as e:
                            continue
    
    progress_bar(total_leg1, total_leg1, 'chain3')
    
    print(f"\nFound {len(all_solutions)} feasible chain solutions")
    
    # Rank and filter solutions
    if all_solutions:
        # Sort by score (lower is better: minimizes C3 + arrival v-infinity^2)
        all_solutions.sort(key=lambda x: x['score'])
        top_solutions = all_solutions[:args.max_solutions]
        
        print(f"Keeping top {len(top_solutions)} solutions")
        
        # Guardrails: Compute hash of top solutions
        scores = np.array([s['score'] for s in top_solutions])
        compute_array_hash(scores, 'chain3_top_scores')
    else:
        top_solutions = []
        print("No feasible solutions found!")
    
    # Save artifacts
    if args.save:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)
        
        # leg1_grid.csv
        leg1_csv = os.path.join(args.outdir, 'chain3_leg1_grid.csv')
        with open(leg1_csv, 'w', newline='') as f:
            if leg1_data:
                writer = csv.DictWriter(f, fieldnames=leg1_data[0].keys())
                writer.writeheader()
                writer.writerows(leg1_data)
        
        # bplane_grid.csv
        bplane_csv = os.path.join(args.outdir, 'chain3_bplane_grid.csv')
        with open(bplane_csv, 'w', newline='') as f:
            if bplane_data:
                writer = csv.DictWriter(f, fieldnames=bplane_data[0].keys())
                writer.writeheader()
                writer.writerows(bplane_data)
        
        # leg2_grid.csv
        leg2_csv = os.path.join(args.outdir, 'chain3_leg2_grid.csv')
        with open(leg2_csv, 'w', newline='') as f:
            if leg2_data:
                writer = csv.DictWriter(f, fieldnames=leg2_data[0].keys())
                writer.writeheader()
                writer.writerows(leg2_data)
        
        # solutions.csv
        solutions_csv = os.path.join(args.outdir, 'chain3_solutions.csv')
        with open(solutions_csv, 'w', newline='') as f:
            if top_solutions:
                writer = csv.DictWriter(f, fieldnames=top_solutions[0].keys())
                writer.writeheader()
                writer.writerows(top_solutions)
        
        # meta.json
        meta = {
            'dep_body': args.dep_body,
            'flyby_body': args.flyby_body,
            'arr_body': args.arr_body,
            'dep_window': args.dep_window,
            'leg1_tof_range': f"{leg1_tof_min}:{leg1_tof_max}:{leg1_tof_step}",
            'leg2_tof_range': f"{leg2_tof_min}:{leg2_tof_max}:{leg2_tof_step}",
            'rp_bounds_km': f"{rp_min}:{rp_max}",
            'bplane_theta_deg': args.bplane_theta,
            'kernels': args.kernels,
            'total_solutions': len(all_solutions),
            'top_solutions': len(top_solutions)
        }
        meta_json = os.path.join(args.outdir, 'chain3_meta.json')
        with open(meta_json, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"\nArtifacts saved to {args.outdir}/")
        print(f"  - chain3_leg1_grid.csv ({len(leg1_data)} rows)")
        print(f"  - chain3_bplane_grid.csv ({len(bplane_data)} rows)")
        print(f"  - chain3_leg2_grid.csv ({len(leg2_data)} rows)")
        print(f"  - chain3_solutions.csv ({len(top_solutions)} rows)")
        print(f"  - chain3_meta.json")
    
    # Output to stdout
    if top_solutions:
        if args.format == 'json':
            print(json.dumps({'solutions': top_solutions[:10]}, indent=2))
        elif args.format == 'table':
            print(f"\nTop 10 Solutions:")
            print(f"{'Dep Date':<12} {'TOF1':>5} {'TOF2':>5} {'C3':>6} {'Turn':>5} {'Rp':>7} {'V∞arr':>6} {'Score':>7}")
            print("-" * 70)
            for sol in top_solutions[:10]:
                dep_date = sol['t_dep_tdb'][:10]
                print(f"{dep_date:<12} {sol['tof1_days']:>5.0f} {sol['tof2_days']:>5.0f} "
                      f"{sol['C3_launch_km2s2']:>6.2f} {sol['turn_angle_deg']:>5.1f} "
                      f"{sol['rp_km']:>7.0f} {sol['arr_vinf_kms']:>6.2f} {sol['score']:>7.2f}")
        elif args.format == 'csv':
            writer = csv.DictWriter(sys.stdout, fieldnames=top_solutions[0].keys())
            writer.writeheader()
            writer.writerows(top_solutions[:10])
