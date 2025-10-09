# Chain3 Leg 2 Empty Results - Root Cause Analysis

## Problem
The `chain3_leg2_grid.csv` file was empty (0 solutions found), which resulted in no feasible chain solutions, despite having:
- **5,611 Leg 1 solutions** (Earth → Mars)
- **841,501 B-plane solutions** (Mars flyby geometries)

## Root Cause
The issue is in the **deltaV tolerance filter** in `src/lambertlab/viz/ui.py` (lines 897-899):

```python
# Check if post-flyby velocity matches Lambert initial velocity
v1_arr = v1.to(u.km/u.s).value
dv_match = np.linalg.norm(v_sc_post - v1_arr)

# Skip if mismatch too large (indicates incompatible flyby)
if dv_match * 1000 > args.dv_tol:  # convert km/s to m/s
    continue
```

**What this does:**
- After computing the flyby exit velocity (`v_sc_post`) using gravity assist physics
- It solves a Lambert problem from the flyby position to the arrival body
- It checks if the Lambert solution's initial velocity matches the flyby exit velocity
- If the mismatch exceeds `dv_tol` (in m/s), it rejects the solution

## Why It Failed

**Default value:** `--dv-tol` defaults to **100 m/s** (0.1 km/s)

For an Earth → Mars → Ceres trajectory:
- Mars flyby occurs at ~5-6 km/s relative velocity
- The b-plane rotation creates different exit velocities
- Mars → Ceres requires significant deltaV change
- The velocity mismatch between the idealized flyby geometry and the Lambert solution is often **> 100 m/s**

Result: **ALL Leg 2 solutions were filtered out** because they all exceeded the 100 m/s tolerance.

## Solution

**Increase the `--dv-tol` parameter:**
- For Mars → Ceres: Use **500-1000 m/s** or higher
- For outer planet missions: May need **1000-2000 m/s**

The tolerance represents how "perfect" the flyby geometry needs to be. Higher values:
- ✅ Allow more solutions through
- ✅ Enable more flexible flyby geometries
- ⚠️ May include less optimal trajectories
- ⚠️ Require validation of final solutions

## Changes Made to run.py

1. **Added dv_tol input prompt** with default of 500 m/s:
   ```python
   print("\nDeltaV tolerance:")
   print("Maximum velocity mismatch (m/s) between flyby exit and Leg 2 entry")
   print("Higher values allow more flyby geometries but may be less accurate")
   dv_tol = input("DV tolerance (m/s) [500]: ").strip() or "500"
   ```

2. **Added to command construction:**
   ```python
   cmd.extend([
       ...
       "--dv-tol", dv_tol,
       "--save"
   ])
   ```

3. **Added to saved configuration** for reproducibility

4. **Added to config loading** with backward compatibility (defaults to 500 for old configs)

## Recommended Values

| Mission Type | Recommended dv_tol |
|--------------|-------------------|
| Earth → Mars → Inner Planet | 200-500 m/s |
| Earth → Mars → Asteroid Belt | 500-1000 m/s |
| Earth → Jupiter → Outer System | 1000-2000 m/s |
| Multi-flyby (>2 assists) | 1500-3000 m/s |

## Testing
To test if this fixes the issue, re-run your chain3 simulation with:
- Same parameters as before
- `dv_tol = 500` (or higher if still no solutions)

You should now see Leg 2 solutions appearing in `chain3_leg2_grid.csv` and final solutions in `chain3_solutions.csv`.
