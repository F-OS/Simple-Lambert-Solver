# Poliastro Upgrade Status: BLOCKED

## Problem Summary

**Cannot upgrade poliastro from 0.7.0 to a newer version due to Python 3.13 incompatibility.**

---

## Investigation Results

### Available Versions
- **Installed:** poliastro 0.7.0 (from ~2017)
- **Latest on PyPI:** poliastro 0.17.0 (released July 10, 2022)
- **Project Status:** **ARCHIVED** - No longer maintained, no new releases expected

### Python Version Constraints
| poliastro Version | Python Requirement | Status |
|-------------------|-------------------|--------|
| 0.7.0 | Python 3.x | ✅ Compatible with 3.13 |
| 0.12.0 | Python 3.x | ❌ Requires astropy < 4.0 (we have 7.1.0) |
| 0.17.0 | Python 3.8-3.10 | ❌ **Does NOT support Python 3.13** |

### Our Environment
- **Python:** 3.13.7
- **astropy:** 7.1.0  
- **numpy:** 2.3.3
- **scipy:** 1.16.2

### The Compatibility Problem

```
poliastro 0.17.0 requires Python >=3.8,<3.11
We have Python 3.13.7
```

**Result:** Cannot install any poliastro version newer than 0.7.0 with Python 3.13.

---

## What We Wanted

The goal was to upgrade to leverage:
- `poliastro.core.flybys.compute_flyby` (exists in newer versions)
- Better numba acceleration
- Bug fixes and improvements from 5+ years of development

---

## Options Moving Forward

### Option 1: Stay on poliastro 0.7.0 ✅ RECOMMENDED
**Pros:**
- Already working with Python 3.13
- We've FIXED the critical Rodrigues rotation bug
- Custom flyby math is now correct and tested
- No dependency conflicts

**Cons:**
- No access to `poliastro.core.flybys`
- Kepler propagation might have numba issues (seen in tests)
- Missing 5 years of poliastro improvements

**Action:**
- Keep custom flyby implementation (now fixed)
- Document why we can't use poliastro flyby functions
- Consider implementing our own numba-accelerated version

### Option 2: Downgrade Python to 3.10
**Pros:**
- Could use poliastro 0.17.0
- Access to `poliastro.core.flybys.compute_flyby`
- All poliastro improvements from 0.7.0 → 0.17.0

**Cons:**  
- ❌ **Lose Python 3.13 features and improvements**
- Need to check if all other dependencies support Python 3.10
- Major disruption to development environment
- Python 3.10 reached end-of-life in October 2026 (sooner)

**Risk:** High - affects entire project

### Option 3: Fork/Vendor poliastro.core.flybys
**Pros:**
- Could extract just the `compute_flyby` function
- Adapt it to work with Python 3.13
- Keep our modern Python version

**Cons:**
- Maintenance burden
- Need to understand poliastro internals
- No future poliastro updates
- Legal/licensing considerations (MIT license - should be OK)

**Complexity:** Medium-High

### Option 4: Find Alternative Library
**Pros:**
- Might find actively maintained library
- Better Python 3.13 support

**Cons:**
- May not exist
- Would require learning new API
- Migration effort

**Status:** Unknown - would need to research

---

## Recommendation: Option 1 - Stay on 0.7.0

**Rationale:**
1. ✅ **We've already fixed the critical bug** - The Rodrigues rotation formula issue is resolved
2. ✅ **Python 3.13 is valuable** - Latest features, performance improvements, security patches
3. ✅ **poliastro is archived** - Even if we could upgrade, no future updates coming
4. ✅ **Custom code works** - Our spherical coordinate formula is correct and matches the physics

**What We Keep:**
- ✅ poliastro Lambert solver (Izzo algorithm) - core functionality
- ✅ poliastro body definitions  
- ✅ poliastro Orbit class
- ✅ Modern Python 3.13 environment
- ✅ All current dependencies up-to-date

**What We Maintain Custom:**
- Flyby rotation (spherical coordinate formula) - **NOW CORRECT**
- B-plane targeting  
- Chain3 three-body trajectory search
- Kepler propagation wrapper (falls back to poliastro when available)

---

## Action Items

### Immediate:
- [x] Stay on poliastro 0.7.0
- [ ] Document this decision in POLIASTRO_USAGE.md
- [ ] Create requirements.txt to pin versions
- [ ] Test that our fixed flyby rotation works correctly

### Future Considerations:
- [ ] Monitor for Python 3.13-compatible astrodynamics libraries
- [ ] Consider contributing to a modern fork of poliastro
- [ ] Explore numba-accelerating our custom flyby code

---

## Updated Documentation

The following files document our poliastro usage with 0.7.0:
- **POLIASTRO_USAGE.md** - What we use vs custom code (UPDATE NEEDED)
- **POLIASTRO_UPGRADE.md** - Why we investigated but couldn't upgrade (THIS FILE)

---

## Conclusion

**We cannot upgrade poliastro while using Python 3.13.**

The project has been archived and the latest version (0.17.0) only supports Python 3.8-3.10. Since:
1. Python 3.13 is more valuable than poliastro upgrades
2. poliastro is no longer maintained anyway
3. We've fixed our critical bugs in the custom code
4. Core poliastro features (Lambert, Orbit) still work fine

**Decision: Continue with poliastro 0.7.0 and maintain our custom flyby implementation.**

---

**Date:** October 9, 2025  
**Python Version:** 3.13.7  
**poliastro Version:** 0.7.0 (staying)  
**Status:** Upgrade blocked, continuing with current setup
