# Interactive Runner - Body Input Guide

The interactive runner (`run.py`) now supports flexible body input using NAIF IDs or body names.

## Supported Input Formats

### NAIF IDs (Recommended)
- **399** - Earth
- **499** - Mars  
- **299** - Venus
- **1** - Mercury Barycenter
- **20000001** - Ceres

### Body Names
- **EARTH** - Earth (ID: 399)
- **MARS** - Mars (ID: 499)
- **VENUS** - Venus (ID: 299)
- **MERCURY** - Mercury Barycenter (ID: 1)

## Ephemeris Validation

The runner automatically validates that:
1. The body exists in the SPICE system
2. Ephemeris data is available for the specified date range

If ephemeris is not available, you'll see a warning message with details:
```
✗ Ephemeris not available for Body 999999 (ID: 999999) at 2026-06-24
Error: SPICE(SPKINSUFFDATA) -- Insufficient ephemeris data...
```

## Finding NAIF IDs

Common body IDs:
- **Sun**: 10
- **Mercury**: 199 (planet center) or 1 (barycenter)
- **Venus**: 299
- **Earth**: 399
- **Mars**: 499
- **Jupiter**: 599 or 5 (barycenter)
- **Saturn**: 699 or 6 (barycenter)
- **Uranus**: 799 or 7 (barycenter)
- **Neptune**: 899 or 8 (barycenter)

Asteroids and small bodies typically have IDs > 2000000:
- **Ceres**: 20000001
- **Vesta**: 20000004

For a complete list, see: `data/kernels/naif_ids.html` or visit:
https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/naif_ids.html

## Example Session

```
=== Two Body Grid Simulation (Porkchop Plot) ===
Compute transfer trajectories between two bodies over a date range.

Departure start date (YYYY-MM-DD) [2026-06-24]: 2026-06-24
Departure end date (YYYY-MM-DD) [2026-06-26]: 2026-06-28

Departure body (e.g., 399 for Earth, 'EARTH', 499 for Mars):
Enter NAIF ID or name [399 (Earth)]: EARTH
✓ Valid: EARTH (NAIF ID: 399)

Arrival body (e.g., 499 for Mars, 'MARS', 20000001 for Ceres):
Enter NAIF ID or name [499 (Mars)]: 20000001
✓ Valid: Body 20000001 (NAIF ID: 20000001)

Min TOF days [190]: 180
Max TOF days [200]: 220
TOF step days [1]: 1
```

## Menu Options

1. **Two Body Grid (Porkchop Plot)** - Generate transfer trajectories between any two bodies
2. **Compute Flyby** - Calculate flyby maneuvers (coming soon)
3. **Two Body Screening** - Screen for transfer opportunities (coming soon)
4. **Three Body Chain (Gravity Assist)** - Multi-body gravity assist trajectories (coming soon)

## Troubleshooting

### "Unknown body name"
- Make sure the body name is spelled correctly and in UPPERCASE
- Try using the NAIF ID instead

### "Ephemeris not available"
- Check that the required SPICE kernel is loaded
- Verify the date range is within kernel coverage
- For asteroids, ensure `data/kernels/20000001.bsp` or equivalent is present

### "Insufficient ephemeris data"
- The date range exceeds the kernel's time coverage
- Try a different date range or add extended ephemeris kernels
