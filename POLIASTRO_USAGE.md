# Poliastro Usage Analysis

## Current Status: Maximized Poliastro Integration ✅

This document explains what functionality from poliastro (version 0.7.0) is being used and what custom math is necessary.

---

## ✅ Already Using Poliastro For:

### 1. **Lambert Solver** (Primary Mission)
- **Module:** `poliastro.iod.izzo.lambert`
- **Where:** `src/lambertlab/core/lambert_io.py`, `src/lambertlab/core/solver.py`
- **Purpose:** Solve Lambert's problem using Izzo's algorithm
- **Status:** ✅ Fully integrated

### 2. **Kepler Propagation**
- **Module:** `poliastro.twobody.propagation.kepler`
- **Where:** `src/lambertlab/core/orbits.py`
- **Purpose:** Propagate orbital state vectors under two-body dynamics
- **Status:** ✅ Used for dt > 1000 seconds

### 3. **Orbit Class**
- **Module:** `poliastro.twobody.Orbit`
- **Where:** `src/lambertlab/flows/validate_arc.py`
- **Purpose:** Validate trajectory arcs and orbital elements
- **Status:** ✅ Fully integrated

### 4. **Body Definitions**
- **Module:** `poliastro.bodies.Sun`
- **Where:** Multiple files
- **Purpose:** Standard gravitational parameters and body properties
- **Status:** ✅ Fully integrated

---

## ❌ Custom Math Required (Not in Poliastro 0.7.0):

### 1. **Gravity Assist / Flyby Rotation**
- **Why Custom:** Poliastro 0.7.0 has NO gravity assist or flyby functions
- **What We Need:** 
  - Turn angle calculation: `sin(δ/2) = 1 / (1 + rp·v∞²/μ)`
  - Velocity rotation in B-plane using spherical coordinates
- **Where Implemented:** 
  - `src/lambertlab/flows/flyby.py` (compute_flyby function)
  - `src/lambertlab/viz/ui.py` (run_chain3_original function)
  - `src/lambertlab/flows/chain3_tiled.py` (chain3 computation)
- **Formula Used:** Spherical coordinate rotation
  ```python
  vinf_out = v_inf_mag * (cos(δ) * e1 + sin(δ) * (cos(θ) * e2 + sin(θ) * e3))
  ```
- **Status:** ✅ Correct implementation (as of latest fix)

### 2. **B-Plane Targeting**
- **Why Custom:** No B-plane utilities in poliastro 0.7.0
- **What We Need:** Grid search over periapsis radius and rotation angle
- **Where Implemented:** 
  - `src/lambertlab/flows/flyby.py`
  - `src/lambertlab/viz/ui.py`
  - `src/lambertlab/flows/chain3_tiled.py`
- **Status:** ✅ Required for mission design

### 3. **Three-Body Trajectory Search (Chain3)**
- **Why Custom:** Highly mission-specific optimization problem
- **What We Need:** 
  - Leg1 (Earth → Mars) Lambert solve
  - Mars flyby with B-plane grid
  - Leg2 (Mars → Ceres) Lambert solve
  - deltaV matching filter
- **Where Implemented:**
  - `src/lambertlab/viz/ui.py` (run_chain3_original)
  - `src/lambertlab/flows/chain3_tiled.py` (checkpointed version)
- **Status:** ✅ Mission-specific, cannot be replaced

---

## 🔍 Investigation Results:

### Checked for Availability:
- ❌ `poliastro.maneuver.powered_swing_by` - Does not exist in 0.7.0
- ❌ `poliastro.flyby` module - Does not exist
- ✅ `poliastro.patched_conics` - EXISTS but only contains `compute_soi()`
- ❌ Gravity assist utilities - Not available
- ❌ B-plane targeting - Not available

### Why Some Math Uses numpy Directly:
Vector operations like `np.linalg.norm()`, `np.dot()`, `np.cross()` are fundamental and **should** use numpy directly. Poliastro doesn't provide wrappers for these - they're building blocks.

---

## 🐛 Bugs Fixed:

### Issue: Incorrect Rodrigues Rotation Formula
- **Location:** `src/lambertlab/flows/chain3_tiled.py` (line 223-229)
- **Problem:** Used Rodrigues rotation formula instead of spherical coordinate formula
- **Impact:** Caused ALL chain3 Leg2 solutions to fail deltaV matching (14-22 km/s errors)
- **Fix:** Replaced with correct spherical coordinate formula matching `flyby.py`
- **Status:** ✅ Fixed

---

## 📊 Coverage Assessment:

| Category | Using Poliastro? | Reason |
|----------|-----------------|---------|
| Lambert Solver | ✅ YES | `poliastro.iod.izzo.lambert` |
| Kepler Propagation | ✅ YES | `poliastro.twobody.propagation.kepler` |
| Orbit Validation | ✅ YES | `poliastro.twobody.Orbit` |
| Gravity Assists | ❌ CUSTOM | Not in poliastro 0.7.0 |
| B-Plane Targeting | ❌ CUSTOM | Not in poliastro 0.7.0 |
| Chain3 Search | ❌ CUSTOM | Mission-specific algorithm |
| Vector Math | ❌ NUMPY | Basic operations (norm, dot, cross) |

---

## ✅ Conclusion:

**The code is now using poliastro to its MAXIMUM capability for version 0.7.0.**

All core orbital mechanics (Lambert, Kepler, Orbit) use poliastro. The custom gravity assist math is **necessary** because poliastro 0.7.0 doesn't provide these functions. The implementation is now using the **correct** spherical coordinate formula for flyby rotation.

### Why We Stay on 0.7.0:

**Upgrade Investigation Result:** ❌ **BLOCKED**

We investigated upgrading to poliastro 0.17.0 (which has `poliastro.core.flybys.compute_flyby`), but:
- poliastro 0.17.0 requires Python 3.8-3.10 (we use Python 3.13.7)
- poliastro project is ARCHIVED (no longer maintained, no future updates)
- No versions support Python 3.13

**Decision:** Continue with poliastro 0.7.0 + custom flyby math (now fixed and correct).

See **POLIASTRO_UPGRADE_BLOCKED.md** for full analysis.

---

## 📝 Notes for Future:

Alternative approaches if needed:
- Monitor for Python 3.13-compatible astrodynamics libraries
- Consider contributing to a modern poliastro fork
- Explore numba-accelerating our custom flyby code

**Current poliastro version:** 0.7.0  
**Python version:** 3.13.7  
**Last updated:** October 9, 2025  
**Status:** Using maximum poliastro capability for Python 3.13 environment
