# Poliastro Upgrade Recommendation

## 🎯 CRITICAL FINDING: poliastro.core.flybys EXISTS!

You've discovered that the **latest stable version** of poliastro (0.12.0) includes `poliastro.core.flybys.compute_flyby` - exactly what we need for gravity assists!

---

## Current Status

- **Installed:** poliastro 0.7.0
- **Latest:** poliastro 0.12.0
- **Gap:** 5 major versions behind

### What 0.7.0 is Missing:
❌ `poliastro.core` module (didn't exist yet)
❌ `poliastro.core.flybys.compute_flyby` function
❌ Modern gravity assist utilities

---

## What poliastro 0.12.0 Offers

According to the documentation you found:

### `poliastro.core.flybys.compute_flyby(v_spacecraft, v_body, k, r_p, theta)`

**Purpose:** Computes outbound velocity after a flyby and the turn angle

**Parameters:**
- `v_spacecraft` (float): Velocity of the spacecraft, relative to the attractor of the body
- `v_body` (float): Velocity of the body, relative to its attractor  
- `k` (float): Standard Gravitational parameter
- `r_p` (float): Radius of periapsis, measured from the center of the body
- `theta` (float): Aim angle of the B vector

**Returns:**
- `v_spacecraft_out` (float): Outbound velocity of the spacecraft
- `delta` (float): Turn angle

**This is EXACTLY what our custom code does!**

---

## Upgrade Benefits

### 1. **Replace Custom Flyby Math** ✅
Our current implementation in:
- `src/lambertlab/flows/flyby.py` 
- `src/lambertlab/viz/ui.py`
- `src/lambertlab/flows/chain3_tiled.py`

Could potentially be replaced with poliastro's **tested and validated** implementation.

### 2. **Bug Prevention** ✅
- No more manual spherical coordinate rotations
- No risk of Rodrigues formula bugs
- Battle-tested library code

### 3. **Performance** ✅
- poliastro.core uses numba-accelerated code
- Likely faster than our numpy implementation

### 4. **Maintainability** ✅
- Less custom code to maintain
- Leverage community bug fixes and improvements

---

## Upgrade Risks & Considerations

### Potential Breaking Changes

**Need to verify:**
1. **Lambert solver API** - Has `poliastro.iod.izzo.lambert` signature changed?
2. **Units handling** - Does 0.12.0 require astropy units more strictly?
3. **Orbit class** - Are there breaking changes in `poliastro.twobody.Orbit`?
4. **Dependencies** - Does 0.12.0 require newer Python/numpy/scipy versions?

### Compatibility Check Required

Current dependencies that might conflict:
```
Python: (check version)
numpy: 2.3.3
scipy: 1.16.2  
astropy: 7.1.0
```

---

## Upgrade Strategy

### Option 1: Test Upgrade (Recommended First Step)

1. **Create a test branch**
   ```bash
   git checkout -b test-poliastro-upgrade
   ```

2. **Upgrade poliastro**
   ```bash
   pip install --upgrade poliastro
   ```

3. **Run existing tests**
   - Test Lambert solver still works
   - Check if any imports break
   - Validate porkchop plots

4. **Test new compute_flyby function**
   - Create small test comparing our formula vs poliastro's
   - Verify results match

5. **If successful:** Refactor to use poliastro.core.flybys
6. **If failures:** Document issues and decide if worth fixing

### Option 2: Pin Version & Continue

If upgrade causes too many breaking changes:
- Stay on 0.7.0
- Keep custom flyby math (now FIXED with correct formula)
- Create requirements.txt to lock versions:
  ```
  poliastro==0.7.0
  ```

---

## Action Items

### Immediate (Before Upgrade):
- [ ] Create requirements.txt with current versions
- [ ] Run and document all current tests passing
- [ ] Commit current working state to git

### Test Upgrade:
- [ ] Create test branch
- [ ] Upgrade to poliastro 0.12.0
- [ ] Check for breaking changes in existing code
- [ ] Test `poliastro.core.flybys.compute_flyby`
- [ ] Compare results with our custom implementation

### If Upgrade Successful:
- [ ] Refactor `flyby.py` to use poliastro.core.flybys
- [ ] Refactor `ui.py` chain3 to use poliastro.core.flybys  
- [ ] Refactor `chain3_tiled.py` to use poliastro.core.flybys
- [ ] Update POLIASTRO_USAGE.md
- [ ] Remove obsolete custom flyby math
- [ ] Update documentation

### If Upgrade Fails:
- [ ] Document breaking changes
- [ ] Revert to 0.7.0
- [ ] Create requirements.txt pinning 0.7.0
- [ ] Keep custom implementation (already fixed)

---

## Recommendation

**🚀 YES, attempt the upgrade!**

**Reasons:**
1. We just spent significant effort fixing the Rodrigues bug
2. poliastro.core.flybys could eliminate that entire class of bugs
3. 5 versions worth of bug fixes and improvements
4. Better performance with numba
5. Can always revert if it breaks

**Next Step:**
Create a test branch and try upgrading to see what breaks. The potential benefits of using library code for gravity assists far outweigh the risk of trying.

---

## Version Comparison

| Feature | poliastro 0.7.0 | poliastro 0.12.0 |
|---------|----------------|------------------|
| Lambert Solver | ✅ | ✅ |
| Kepler Propagation | ✅ | ✅ |
| Orbit Class | ✅ | ✅ (enhanced) |
| `poliastro.core` | ❌ | ✅ |
| Gravity Assist | ❌ | ✅ |
| compute_flyby | ❌ | ✅ |
| numba acceleration | ❓ | ✅ |

---

**Created:** October 9, 2025  
**Triggered by:** Discovery of poliastro.core.flybys documentation  
**Current Version:** 0.7.0  
**Target Version:** 0.12.0
