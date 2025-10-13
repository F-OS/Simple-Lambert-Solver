"""Plotter module for porkchop visualizations.

Exposes a function `plot_porkchop` that accepts the departure times, TOF array,
and C3 grid and saves a single-panel filled-contour image similar to the
example style.
"""
from typing import Sequence

import numpy as np
# Force matplotlib to use non-interactive backend for subprocess compatibility
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.time import Time
import logging

logger = logging.getLogger(__name__)


def plot_porkchop(dep_times: Sequence[Time], tof_days: np.ndarray, c3_grid: np.ndarray,
                  outname: str = "refine_porkchop_styled.png", cmap: str = 'turbo',
                  contour_levels: int = 50, tof_contour_step: int = 50,
                  jd_offset: float = None, cmin: float = 10.0, cmax: float = 100.0,
                  dep_body: str = 'Earth', arr_body: str = 'Mars') -> None:
    """Create a single-panel filled-contour porkchop similar to the reference image.

    - X axis: departure Julian Date (with numeric offset for readability)
    - Y axis: arrival Julian Date
    - Filled contour: C3 values
    - Diagonal lines: constant TOF (days) labeled
    - Valley path: minimum-C3 per departure plotted as a dotted path

    Args:
        dep_times: 1D sequence of astropy Time objects (length N)
        tof_days: 1D numpy array of TOF values in days (length M)
        c3_grid: 2D numpy array shape (N, M)
        outname: output PNG filename
        cmap: matplotlib colormap name
        contour_levels: number of filled contour levels
        tof_contour_step: step (days) for diagonal TOF contour lines
        jd_offset: numeric JD offset to subtract from JD axes (default: rounded min dep JD)
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
    logger.info('Plot saved as %s', outname)
