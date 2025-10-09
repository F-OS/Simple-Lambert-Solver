# Quick Reference: Common NAIF IDs

## Planets (Planet Centers)
| Body | NAIF ID | Name in SPICE |
|------|---------|---------------|
| Mercury | 199 | MERCURY |
| Venus | 299 | VENUS |
| Earth | 399 | EARTH |
| Mars | 499 | MARS |
| Jupiter | 599 | JUPITER |
| Saturn | 699 | SATURN |
| Uranus | 799 | URANUS |
| Neptune | 899 | NEPTUNE |

## Planets (Barycenters)
| Body | NAIF ID | Name in SPICE |
|------|---------|---------------|
| Mercury | 1 | MERCURY BARYCENTER |
| Venus | 2 | VENUS BARYCENTER |
| Earth | 3 | EARTH BARYCENTER |
| Mars | 4 | MARS BARYCENTER |
| Jupiter | 5 | JUPITER BARYCENTER |
| Saturn | 6 | SATURN BARYCENTER |
| Uranus | 7 | URANUS BARYCENTER |
| Neptune | 8 | NEPTUNE BARYCENTER |

## Sun and Moon
| Body | NAIF ID | Name in SPICE |
|------|---------|---------------|
| Sun | 10 | SUN |
| Moon | 301 | MOON |

## Major Asteroids
| Body | NAIF ID | Name in SPICE |
|------|---------|---------------|
| Ceres | 20000001 | (No standard name) |
| Pallas | 20000002 | (No standard name) |
| Vesta | 20000004 | (No standard name) |

## When to Use Planet Center vs Barycenter

### Planet Center (e.g., 399 for Earth)
- Use for spacecraft trajectories
- Surface launches and landings
- Close planetary flybys
- **Most common for trajectory analysis**

### Barycenter (e.g., 3 for Earth-Moon barycenter)
- Use for system-wide dynamics
- Multi-body gravitational interactions
- Outer planet missions where moons matter
- **Less common in typical use**

## Example Missions

### Inner Solar System
```
Earth to Venus:    Dep: 399, Arr: 299
Earth to Mars:     Dep: 399, Arr: 499
Venus to Mars:     Dep: 299, Arr: 499
```

### Asteroid Missions
```
Earth to Ceres:    Dep: 399, Arr: 20000001
Mars to Vesta:     Dep: 499, Arr: 20000004
```

### Outer Solar System
```
Earth to Jupiter:  Dep: 399, Arr: 599 (or 5 for barycenter)
Mars to Saturn:    Dep: 499, Arr: 699 (or 6 for barycenter)
```

## Finding More NAIF IDs

1. **Local file**: `data/kernels/naif_ids.html`
2. **Online**: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/naif_ids.html
3. **Small bodies**: IDs typically in the 2000000+ range
4. **Spacecraft**: Negative IDs (e.g., -61 for Juno)

## Tips

- **Use names when available**: `EARTH` is easier to remember than `399`
- **Planet centers recommended**: Use 399/499/299 rather than barycenters
- **Check ephemeris**: Not all bodies have data for all dates
- **Asteroids use IDs**: Most don't have standard SPICE names
