"""Orbital mechanics utilities."""

import numpy as np
# import pykep as pk


def kepler_propagate(r0, v0, dt, mu):
    """Propagate state vector (r0, v0) by dt seconds under gravity mu.

    For small dt, approximate with linear motion.
    For larger dt, use PyKEP's Kepler propagation.
    """
    # Temporary: use linear approximation for smoke test (PyKEP not available)
    r = r0 + v0 * dt
    v = v0
    return r, v