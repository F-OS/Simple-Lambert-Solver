"""Run a refined porkchop grid around a previously detected minimum.

Refine parameters (hard-coded for now):
 - dep center: 2035-06-25T00:01:09.184
 - dep window: +/- 7 days, step 0.5 d
 - tof center: 195 d
 - tof window: 185..205 d, step 0.5 d

Saves `refine_porkchop.npz` in the current folder.
"""
from run_grid import compute_grid
import numpy as np
import argparse
import os


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--out-dir', default='.', help='Directory to write outputs into')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    dep_center = '2035-06-25T00:01:09.184'
    dep_start = '2035-06-18'
    dep_end = '2035-07-02'

    tof_min = 185
    tof_max = 205

    print('Running refined grid: dep %s..%s step 0.5 d, tof %d..%d step 0.5 d' % (dep_start, dep_end, tof_min, tof_max))
    dep_times, tof_days, C3, vinf_dep, vinf_arr, branch_used = compute_grid('399', '4', dep_start, dep_end, 0.5, tof_min, tof_max, 0.5)

    out = 'refine_porkchop.npz'
    os.makedirs(args.out_dir, exist_ok=True)
    out_path = out if os.path.isabs(out) else os.path.join(args.out_dir, out)
    np.savez(out_path,
             dep_times=[t.tdb.isot for t in dep_times],
             tof_days=tof_days,
             C3=C3,
             vinf_dep=vinf_dep,
             vinf_arr=vinf_arr,
             branch_used=branch_used)
    print('Saved', out_path)
    total = C3.size
    finite = np.isfinite(C3).sum()
    print(f'Grid shape: {C3.shape}, finite cells: {finite}/{total}')
