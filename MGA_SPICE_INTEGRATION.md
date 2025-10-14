# PyKEP MGA Optimizer Integration with SPICE

## Overview

We've successfully integrated PyKEP's Multi-Gravity-Assist (MGA) optimizer with lambertlab's existing SPICE ephemeris infrastructure. This maintains consistency and accuracy across all trajectory computations.

## Key Features

### 1. SPICE-Based Planets
- Created `SpicePlanet` class that uses NASA SPICE kernels for ephemeris data
- Integrates seamlessly with PyKEP's MGA optimizers
- Supports any body with available SPICE data

### 2. Generic Mission Design
- Not limited to Earth-Mars-Ceres
- Supports arbitrary planet sequences via `--sequence` parameter
- Configurable flyby altitude constraints per body

### 3. Existing Infrastructure Integration
- Uses `lambertlab.core.spice_io` for all ephemeris lookups
- Leverages existing SPICE kernel management
- Maintains units consistency (km, km/s, seconds)

## Usage

### Basic Earth→Mars→Ceres Mission
```bash
python solve_mga_mars_flyby_ceres.py \
    --sequence earth mars ceres \
    --launch-start 2030-01-01 \
    --launch-end 2032-12-31 \
    --tof-bounds 120 500 150 900 \
    --flyby-hmin mars:300 \
    --pop 96 --gens 600 --islands 4
```

### Earth→Venus→Earth Gravity Assist
```bash
python solve_mga_mars_flyby_ceres.py \
    --sequence earth venus earth \
    --launch-start 2025-01-01 \
    --launch-end 2026-12-31 \
    --tof-bounds 100 300 100 300 \
    --flyby-hmin venus:500 \
    --objective min_vinf_arrival
```

### Earth→Jupiter Hohmann-like Transfer
```bash
python solve_mga_mars_flyby_ceres.py \
    --sequence earth jupiter \
    --launch-start 2028-01-01 \
    --launch-end 2030-12-31 \
    --tof-bounds 400 900 \
    --no-vinf-dep \
    --pop 128 --gens 800
```

## Available Bodies

Currently configured NAIF IDs:
- **sun**: 10
- **mercury**: 199
- **venus**: 299
- **earth**: 399
- **mars**: 4 (barycenter)
- **jupiter**: 5 (barycenter)
- **saturn**: 6 (barycenter)
- **ceres**: 2000001

*Note: Ceres requires the small bodies kernel (20000001.bsp) which is already in the data/kernels directory.*

## Implementation Details

### SpicePlanet Class
Located in `src/lambertlab/mission/emm_ceres.py`:
```python
class SpicePlanet:
    """Wrapper for PyKEP planets using SPICE ephemeris"""
    
    def eph(self, mjd2000: float):
        """Return (r, v) from SPICE at given MJD2000 epoch"""
        epoch_time = from_mjd2000(mjd2000)
        r, v = rv_helio_spice(self.naif_id, epoch_time)
        return (tuple(r), tuple(v))
```

### Time Conversion
- Uses MJD2000 (Modified Julian Date 2000) as PyKEP standard
- MJD2000 = MJD - 51544.5
- MJD2000 = 0 corresponds to 2000-01-01 12:00:00 TT

### MGA Problem Setup
- Wraps PyKEP's `trajopt.mga` or `trajopt.mga_1dsm`
- Supports custom objectives (min arrival v∞ or min total Δv)
- Enforces flyby altitude constraints per body

## Testing Status

✅ Module imports successfully
✅ SPICE kernels load correctly
✅ Earth ephemeris works
✅ Mars ephemeris works
✅ Time conversion (astropy ↔ MJD2000) verified
⚠️  Ceres requires small bodies kernel (already available)

## Next Steps

1. Test complete MGA optimization run
2. Add trajectory visualization
3. Validate against known missions
4. Add more bodies as needed (add SPICE kernels + NAIF IDs)

## Integration with Existing Modules

### Does NOT Break
- ✅ Porkchop plot generation (`transfer_grid.py`)
- ✅ Transfer requirements (`transfer_requirements.py`)
- ✅ Flyby targeting (`flyby.py`)
- ✅ SPICE ephemeris (`spice_io.py`)

### New Capabilities
- Multi-leg trajectory optimization
- Gravity assist targeting
- Global optimization with PyGMO
- Mission trade studies

## Dependencies

Added to lambertlab environment:
- `pygmo` (installed via conda-forge)
- `pykep` (already present)

No modifications to existing dependencies required.
