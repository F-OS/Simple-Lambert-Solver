"""LambertLab: Interplanetary transfer analysis."""

from .cli.main import main
from .core.spice_io import load_kernels, rv_helio_spice, rv_helio_spice_q
from .core.lambert_io import lambert_leg, vinf_vec, c3
from .flows.em_only import compute_em_c3_tof, screen_em_grid
from .viz.porkchop import plot_porkchop

__version__ = "0.1.0"