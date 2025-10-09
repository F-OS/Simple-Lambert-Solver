"""Plotter module for porkchop visualizations.

Exposes a function `plot_porkchop` that accepts the departure times, TOF array,
and C3 grid and saves a single-panel filled-contour image similar to the
example style.
"""
from typing import Sequence

import numpy as np
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.time import Time
import csv
from collections import defaultdict


def create_feasibility_mask(em_csv: str, emc_csv: str, dep_times: Sequence[Time], tof_days: np.ndarray, 
                           threshold_deg: float = 5.0, dv_threshold_kms: float = 0.15) -> np.ndarray:
    """Create a feasibility mask from emc_screen.csv.
    
    Args:
        em_csv: path to em_porkchop.csv for dep/mars mapping
        emc_csv: path to emc_screen.csv
        dep_times: departure times
        tof_days: TOF array
        threshold_deg: angle error threshold for feasibility
        dv_threshold_kms: delta-V threshold for powered flyby feasibility
        
    Returns:
        mask: 2D boolean array (N, M) True where feasible (ballistic or low-delta-V powered)
    """
    # Load EM data to get dep_iso -> mars_iso mapping
    dep_to_mars = {}
    with open(em_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep_iso = row['dep_iso']
            mars_iso = row['mars_iso']
            dep_to_mars[dep_iso] = mars_iso
    
    # Load EMC data
    emc_data = defaultdict(list)
    with open(emc_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep_iso = row['dep_iso']
            mars_iso = row['mars_iso']
            if dep_to_mars.get(dep_iso) == mars_iso:  # Match
                emc_data[(dep_iso, mars_iso)].append(row)
    
    # Create mask
    N = len(dep_times)
    M = len(tof_days)
    mask = np.zeros((N, M), dtype=bool)
    
    dep_iso_list = [t.isot for t in dep_times]
    
    for i, dep_iso in enumerate(dep_iso_list):
        mars_iso = dep_to_mars.get(dep_iso)
        if mars_iso and (dep_iso, mars_iso) in emc_data:
            rows = emc_data[(dep_iso, mars_iso)]
            # Check if any row has low angle error OR low delta-V
            for row in rows:
                ang_err = float(row['best_ang_err_deg']) if row['best_ang_err_deg'] else float('inf')
                dv_peri = float(row['dv_peri_kms']) if row['dv_peri_kms'] else float('inf')
                
                if ang_err < threshold_deg or dv_peri < dv_threshold_kms:
                    # Find corresponding TOF
                    tof1_d = float(row['tof1_d'])
                    j = np.argmin(np.abs(tof_days - tof1_d))
                    mask[i, j] = True
                    break  # Mark as feasible
    
    return mask
    
def create_rp_grid(em_csv: str, emc_csv: str, dep_times: Sequence[Time], tof_days: np.ndarray) -> np.ndarray:
    """Create rp_needed grid from emc_screen.csv.
    
    Args:
        em_csv: path to em_porkchop.csv for dep/mars mapping
        emc_csv: path to emc_screen.csv
        dep_times: departure times
        tof_days: TOF array
        
    Returns:
        rp_grid: 2D array (N, M) of rp_needed_km values
    """
    # Load EM data
    dep_to_mars = {}
    with open(em_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep_iso = row['dep_iso']
            mars_iso = row['mars_iso']
            dep_to_mars[dep_iso] = mars_iso
    
    # Load EMC data
    emc_data = defaultdict(list)
    with open(emc_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep_iso = row['dep_iso']
            mars_iso = row['mars_iso']
            if dep_to_mars.get(dep_iso) == mars_iso:
                emc_data[(dep_iso, mars_iso)].append(row)
    
    # Create rp grid
    N = len(dep_times)
    M = len(tof_days)
    rp_grid = np.full((N, M), np.nan)
    
    dep_iso_list = [t.isot for t in dep_times]
    
    for i, dep_iso in enumerate(dep_iso_list):
        mars_iso = dep_to_mars.get(dep_iso)
        if mars_iso and (dep_iso, mars_iso) in emc_data:
            rows = emc_data[(dep_iso, mars_iso)]
            for row in rows:
                tof1_d = float(row['tof1_d'])
                rp_km = float(row['rp_needed_km'])
                j = np.argmin(np.abs(tof_days - tof1_d))
                rp_grid[i, j] = rp_km
    
    return rp_grid


def plot_porkchop(dep_times: Sequence[Time], tof_days: np.ndarray, c3_grid: np.ndarray,
                  outname: str = "refine_porkchop_styled.png", cmap: str = 'turbo',
                  contour_levels: int = 50, tof_contour_step: int = 50,
                  jd_offset: float = None, cmin: float = 10.0, cmax: float = 100.0,
                  dep_body: str = 'Earth', arr_body: str = 'Mars',
                  overlay_mask: np.ndarray = None, overlay_label: str = None) -> None:
    """Create a single-panel filled-contour porkchop similar to the reference image.

    - X axis: departure Julian Date (with numeric offset for readability)
    - Y axis: arrival Julian Date
    - Filled contour: C3 values
    - Diagonal lines: constant TOF (days) labeled
    - Valley path: minimum-C3 per departure plotted as a dotted path
    - Optional overlay: hatched mask for feasible regions

    Args:
        dep_times: 1D sequence of astropy Time objects (length N)
        tof_days: 1D numpy array of TOF values in days (length M)
        c3_grid: 2D numpy array shape (N, M)
        outname: output PNG filename
        cmap: matplotlib colormap name
        contour_levels: number of filled contour levels
        tof_contour_step: step (days) for diagonal TOF contour lines
        jd_offset: numeric JD offset to subtract from JD axes (default: rounded min dep JD)
        overlay_mask: 2D boolean array shape (N, M), True where to overlay hatch
        overlay_label: label for the overlay legend
    """
    dep_times = Time(dep_times)
    dep_jd = dep_times.tdb.jd  # shape (N,)

    N = len(dep_jd)
    M = len(tof_days)

    # Arrival JD grid: arr_jd[i,j] = dep_jd[i] + tof_days[j]
    arr_jd = dep_jd[:, None] + tof_days[None, :]

    # X and Y mesh for plotting: X (N,M) of departure JD, Y (N,M) of arrival JD
    X = np.repeat(dep_jd[:, None], M, axis=1)
    Y = arr_jd

    # Determine JD offset for x-axis labeling
    if jd_offset is None:
        jd_offset = float(np.round(dep_jd.min() / 1000.0) * 1000.0)

    # Prepare Z (C3) and mask NaNs
    Z = np.array(c3_grid, dtype=float)
    # Clip display to [cmin, cmax] and mask values outside that range (they'll be rendered white)
    display_min = float(cmin)
    display_max = float(cmax)
    Z_display = np.ma.masked_where((~np.isfinite(Z)) | (Z < display_min) | (Z > display_max), Z)

    # Choose contour levels across display range
    levels = np.linspace(display_min, display_max, contour_levels)

    fig, ax = plt.subplots(figsize=(9, 6))
    # Use a colormap for the valid range
    cmap_obj = plt.get_cmap(cmap)
    cf = ax.contourf(X - jd_offset, Y, Z_display, levels=levels, cmap=cmap_obj, extend='both')
    # Render out-of-range values as white by overlaying a white background where masked
    # Create a mask for values outside [display_min, display_max]
    outside_mask = np.isnan(Z) | (Z < display_min) | (Z > display_max)
    if np.any(outside_mask):
        ax.contourf(X - jd_offset, Y, outside_mask.astype(float), levels=[0.5, 1.5], colors=['white'], alpha=1.0)
    cbar = fig.colorbar(cf, ax=ax)
    cbar.set_label('C3 (km$^2$/s$^2$)')

    # Optional overlay mask
    if overlay_mask is not None:
        overlay_data = np.ma.masked_where(~overlay_mask, np.ones_like(Z))
        ax.contourf(X - jd_offset, Y, overlay_data, levels=[0.5, 1.5], 
                   colors=['none'], hatches=['///'], alpha=0.3)
        if overlay_label:
            # Add a legend entry for the overlay
            ax.fill_between([], [], facecolor='none', hatch='///', label=overlay_label)
            ax.legend(loc='upper right')

    # Diagonal TOF contours: compute TOF grid and draw lines
    TOF = Y - X
    tof_min = int(np.nanmin(tof_days))
    tof_max = int(np.nanmax(tof_days))
    tof_levels = np.arange(tof_min, tof_max + 1, tof_contour_step)
    cs = ax.contour(X - jd_offset, Y, TOF, levels=tof_levels, colors='k', linewidths=0.7)
    ax.clabel(cs, fmt='%d d', inline=True, fontsize=8)

    # Plot valley: for each departure (row) find TOF index of min C3
    valley_tofs = []
    valley_arrs = []
    for i in range(N):
        row = Z[i, :]
        if np.all(~np.isfinite(row)):
            valley_tofs.append(np.nan)
            valley_arrs.append(np.nan)
            continue
        jmin = np.nanargmin(row)
        tof_min_val = tof_days[jmin]
        arr_jd_val = dep_jd[i] + tof_min_val
        valley_tofs.append(tof_min_val)
        valley_arrs.append(arr_jd_val)

    valley_tofs = np.array(valley_tofs)
    valley_arrs = np.array(valley_arrs)
    ax.plot(dep_jd - jd_offset, valley_arrs, color='white', linestyle='--', linewidth=1.5, marker='o', markersize=3, markerfacecolor='white', markeredgecolor='black')

    # Axis labels and title — use human-friendly calendar labels now
    ax.set_xlabel('Departure date')
    ax.set_ylabel('Arrival date')
    # Title reflects the actual bodies used
    # Try to map common numeric NAIF IDs to friendly names
    id_map = {
        '399': 'Earth',
        '499': 'Mars',
        '20000001': 'Ceres'
    }
    def _name(x):
        if x is None:
            return ''
        sx = str(x).strip()
        return id_map.get(sx, sx)

    ax.set_title(f'C3 Porkchop ({_name(dep_body)} → {_name(arr_body)})')

    # Tidy ticks: show a few x ticks as calendar dates (YYYY-MM-DD)
    # We compute tick positions in JD, then subtract jd_offset for plotting coordinates
    def _nice_ticks(start, stop, max_ticks=6):
        if np.isclose(start, stop):
            return np.array([start])
        return np.linspace(start, stop, min(max_ticks, 6))

    xticks_jd = _nice_ticks(dep_jd.min(), dep_jd.max(), max_ticks=6)
    xtick_locs = xticks_jd - jd_offset
    # Convert to YYYY-MM-DD strings
    xtick_labels = []
    from astropy.time import Time as _Time
    for jd in xticks_jd:
        try:
            t = _Time(jd, format='jd', scale='tdb')
            xtick_labels.append(t.strftime('%Y-%m-%d'))
        except Exception:
            xtick_labels.append(str(int(round(jd))))
    ax.set_xticks(xtick_locs)
    ax.set_xticklabels(xtick_labels, rotation=30, ha='right')

    # Y ticks: arrival calendar dates
    y_min = arr_jd.min()
    y_max = arr_jd.max()
    yticks_jd = _nice_ticks(y_min, y_max, max_ticks=6)
    ytick_labels = []
    for jd in yticks_jd:
        try:
            t = _Time(jd, format='jd', scale='tdb')
            ytick_labels.append(t.strftime('%Y-%m-%d'))
        except Exception:
            ytick_labels.append(str(int(round(jd))))
    ax.set_yticks(yticks_jd)
    ax.set_yticklabels(ytick_labels)

    plt.tight_layout()
    fig.savefig(outname, dpi=200)
    plt.close(fig)
    print(f'Plot saved as {outname}')


def plot_rp_heatmap(dep_times: Sequence[Time], tof_days: np.ndarray, rp_grid: np.ndarray,
                    outname: str = "rp_heatmap.png", cmap: str = 'plasma',
                    rp_min: float = 300.0, dep_body: str = 'Earth', arr_body: str = 'Mars') -> None:
    """Create a heatmap of required periapsis radius for Mars flyby.
    
    Args:
        dep_times: 1D sequence of astropy Time objects (length N)
        tof_days: 1D numpy array of TOF values in days (length M)
        rp_grid: 2D numpy array of rp_needed_km values shape (N, M)
        outname: output PNG filename
        cmap: matplotlib colormap name
        rp_min: minimum rp value for clipping/colorbar
        dep_body, arr_body: body names for title
    """
    dep_times = Time(dep_times)
    dep_jd = dep_times.tdb.jd

    N = len(dep_jd)
    M = len(tof_days)

    # Arrival JD grid
    arr_jd = dep_jd[:, None] + tof_days[None, :]

    # X and Y mesh
    X = np.repeat(dep_jd[:, None], M, axis=1)
    Y = arr_jd

    # Determine JD offset
    jd_offset = float(np.round(dep_jd.min() / 1000.0) * 1000.0)

    # Prepare RP data - clip at rp_min for display
    Z = np.array(rp_grid, dtype=float)
    Z_clipped = np.clip(Z, rp_min, None)
    Z_display = np.ma.masked_where(~np.isfinite(Z), Z_clipped)

    fig, ax = plt.subplots(figsize=(9, 6))
    cmap_obj = plt.get_cmap(cmap)
    cf = ax.contourf(X - jd_offset, Y, Z_display, cmap=cmap_obj, levels=50)
    cbar = fig.colorbar(cf, ax=ax)
    cbar.set_label('Required rp (km)')

    # TOF contours
    TOF = Y - X
    tof_min = int(np.nanmin(tof_days))
    tof_max = int(np.nanmax(tof_days))
    tof_levels = np.arange(tof_min, tof_max + 1, 50)
    cs = ax.contour(X - jd_offset, Y, TOF, levels=tof_levels, colors='k', linewidths=0.7)
    ax.clabel(cs, fmt='%d d', inline=True, fontsize=8)

    # Axis labels and title
    ax.set_xlabel('Departure date')
    ax.set_ylabel('Arrival date')
    ax.set_title(f'Mars Flyby rp Requirements ({dep_body} → {arr_body})')

    # Tidy ticks
    xticks_jd = np.linspace(dep_jd.min(), dep_jd.max(), 6)
    xtick_locs = xticks_jd - jd_offset
    xtick_labels = [Time(jd, format='jd', scale='tdb').strftime('%Y-%m-%d') for jd in xticks_jd]
    ax.set_xticks(xtick_locs)
    ax.set_xticklabels(xtick_labels, rotation=30, ha='right')

    yticks_jd = np.linspace(Y.min(), Y.max(), 6)
    ytick_labels = [Time(jd, format='jd', scale='tdb').strftime('%Y-%m-%d') for jd in yticks_jd]
    ax.set_yticks(yticks_jd)
    ax.set_yticklabels(ytick_labels)

    plt.tight_layout()
    fig.savefig(outname, dpi=200)
    plt.close(fig)
    print(f'Plot saved as {outname}')


def plot_c3(dep_times, tof_days, c3_grid, out_png):
    """Plot C3 porkchop plot."""
    plot_porkchop(dep_times, tof_days, c3_grid, outname=out_png)

