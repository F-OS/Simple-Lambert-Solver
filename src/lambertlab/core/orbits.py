"""Orbital mechanics utilities."""

import numpy as np


def kepler_propagate(r0, v0, dt, mu):
    """Propagate state vector (r0, v0) by dt seconds under gravity mu.

    For small dt, approximate with linear motion.
    """
    if abs(dt) < 1000:  # small dt, use approximation
        r = r0 + v0 * dt
        v = v0
    else:
        # Use poliastro for larger dt
        from poliastro.twobody.propagation import kepler
        r, v = kepler(r0, v0, dt, mu)
    return r, v