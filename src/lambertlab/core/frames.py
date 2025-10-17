"""Frame transformations."""


def v_infinity(v_helio, v_planet):
    """Compute hyperbolic excess velocity in planet frame.

    Args:
        v_helio: heliocentric velocity vector (km/s)
        v_planet: planet heliocentric velocity vector (km/s)

    Returns:
        v_inf: excess velocity (km/s)
    """
    return v_helio - v_planet