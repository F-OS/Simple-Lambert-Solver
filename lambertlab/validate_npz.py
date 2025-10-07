import argparse
import numpy as np
from astropy.time import Time
from astropy import units as u
from src.lambertlab.solver import compute_c3_tof, load_kernels


def parse_args():
    p = argparse.ArgumentParser(description='Validate a porkchop .npz file')
    p.add_argument('--file', '-f', default='refine_porkchop.npz', help='Path to .npz to validate')
    p.add_argument('--consist-tol', type=float, default=1e-6, help='consistency tolerance')
    p.add_argument('--spike-factor', type=float, default=2.0, help='spike detection factor')
    return p.parse_args()


args = parse_args()
NPZ = args.file
CONSIST_TOL = args.consist_tol
SPIKE_FACTOR = args.spike_factor


def load_npz(path):
    d = np.load(path, allow_pickle=True)
    dep_times = [Time(s, scale='tdb') for s in d['dep_times']]
    tof_days = d['tof_days']
    C3 = d['C3']
    vinf_dep = d.get('vinf_dep')
    vinf_arr = d.get('vinf_arr')
    branch = d.get('branch_used')
    return dep_times, tof_days, C3, vinf_dep, vinf_arr, branch


def basic_stats(C3):
    N, M = C3.shape
    total = N*M
    finite = np.isfinite(C3).sum()
    pct_nan = 100.0*(1 - finite/total)
    print(f'Grid shape: {C3.shape}, finite cells: {finite}/{total} ({pct_nan:.2f}% NaN)')
    if finite>0:
        idx = np.unravel_index(np.nanargmin(C3), C3.shape)
        print('Min C3 =', C3[idx], 'at indices', idx)
        print('Min dep index, tof index:', idx)
    print('C3 stats (finite): mean/median/std:', np.nanmean(C3), np.nanmedian(C3), np.nanstd(C3))


def consistency_check(C3, vinf_dep, tol=CONSIST_TOL):
    if vinf_dep is None:
        print('vinf_dep array missing; skip consistency check.')
        return
    mags = np.linalg.norm(vinf_dep, axis=2)
    sqrtC3 = np.sqrt(np.clip(C3, 0, None))
    mask = np.isfinite(C3)
    diffs = np.abs(mags[mask] - sqrtC3[mask])
    maxdiff = np.nanmax(diffs) if diffs.size else 0.0
    bad = int((diffs > tol).sum()) if diffs.size else 0
    print(f'Consistency: checked {mask.sum()} cells, max |norm(vinf) - sqrt(C3)| = {maxdiff:.3e}, bad count (>{tol}) = {bad}')


def spike_detector(C3, factor=SPIKE_FACTOR):
    N, M = C3.shape
    spikes = []
    for i in range(N):
        for j in range(M):
            if not np.isfinite(C3[i,j]):
                continue
            neigh = []
            for ii in (i-1, i, i+1):
                for jj in (j-1, j, j+1):
                    if ii==i and jj==j:
                        continue
                    if 0 <= ii < N and 0 <= jj < M and np.isfinite(C3[ii,jj]):
                        neigh.append(C3[ii,jj])
            if not neigh:
                continue
            if C3[i,j] > factor * (sum(neigh)/len(neigh)):
                spikes.append((i,j,C3[i,j], sum(neigh)/len(neigh)))
    print('Spike detector found', len(spikes), 'spikes (factor=',factor,')')
    if spikes:
        print('Sample spikes (i,j,C3,neigh_avg):')
        for s in spikes[:10]:
            print(s)


def spot_recompute(dep_times, tof_days, C3, vinf_dep, samples=3):
    N, M = C3.shape
    # pick argmin and a couple neighbors
    if np.all(~np.isfinite(C3)):
        print('No finite cells to spot-check.')
        return
    i0, j0 = np.unravel_index(np.nanargmin(C3), C3.shape)
    candidates = [(i0, j0)]
    if i0-1 >= 0:
        candidates.append((i0-1, j0))
    if j0-1 >= 0:
        candidates.append((i0, j0-1))
    candidates = candidates[:samples]

    # Ensure kernels loaded for spot recompute
    load_kernels()

    for (i,j) in candidates:
        dep = dep_times[i]
        tof = tof_days[j]
        arr = dep + tof * u.day
        dep_iso = dep.tdb.isot
        arr_iso = arr.tdb.isot
        try:
            tof_d, c3_new, vinf_dep_new, vinf_arr_new, branch_new = compute_c3_tof(dep_iso, arr_iso)
            saved = C3[i,j]
            print(f'Spot check cell (i={i}, j={j}): dep={dep_iso}, tof={tof} d')
            print('  saved C3 =', saved)
            print('  recomputed C3 =', c3_new)
            print('  abs diff =', abs(saved - c3_new))
            if vinf_dep is not None:
                saved_v = vinf_dep[i,j]
                print('  saved vinf_dep:', saved_v)
                print('  recomputed vinf_dep:', vinf_dep_new)
                print('  vinf abs diff norm:', np.linalg.norm(saved_v - vinf_dep_new))
            print('  branch_new:', branch_new)
        except Exception as e:
            print('  recompute failed for cell', (i,j), 'error:', e)


if __name__ == '__main__':
    print('Validating', NPZ)
    dep_times, tof_days, C3, vinf_dep, vinf_arr, branch = load_npz(NPZ)
    basic_stats(C3)
    consistency_check(C3, vinf_dep)
    spike_detector(C3)
    spot_recompute(dep_times, tof_days, C3, vinf_dep)
