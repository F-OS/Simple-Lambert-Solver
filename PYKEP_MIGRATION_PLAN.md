# PyKEP Installation & Migration Plan

## Current Situation
- Using Python 3.13.7 in a pip-based virtual environment (.venv)
- No conda installed on system
- Need PyKEP for better Lambert solver and native flyby functions

## Installation Options

### Option 1: Install Miniforge/Miniconda (RECOMMENDED)
**Why:** PyKEP is primarily distributed via conda-forge
**Pros:**
- Official distribution method
- Handles all C++ dependencies automatically
- win-64 packages available for Windows
**Cons:**
- Need to install conda first
- Will create separate conda environment

**Steps:**
1. Download Miniforge: https://github.com/conda-forge/miniforge/releases
2. Install Miniforge (minimal conda with conda-forge by default)
3. Create new environment:
   ```bash
   conda create -n lambertlab python=3.13
   conda activate lambertlab
   conda install pykep
   ```
4. Reinstall our dependencies in conda environment
5. Migrate project to use conda environment

### Option 2: Build from Source
**Why:** No conda, want to stay with pip
**Pros:**
- Stay in current pip environment
- Full control over build
**Cons:**
- ⚠️ **Complex** - Requires Visual Studio C++ compiler, Boost libraries, CMake
- Time-consuming
- Error-prone on Windows
- Hard to maintain

**Requirements:**
- Visual Studio 2019+ with C++ tools
- Boost libraries (1.60+)
- CMake 3.3+
- Python development headers
- Manual compilation of keplerian_toolbox C++ library

### Option 3: Try pip in case (QUICK TEST)
**Why:** Maybe there are wheels we didn't see
**Pros:**
- Easiest if it works
**Cons:**
- Documentation says Linux-only pip support
- Unlikely to work on Windows Python 3.13

**Test:**
```bash
pip install pykep
```

## Recommended Approach: HYBRID

1. **Quick Test** - Try pip first (30 seconds)
   - If it works: Amazing, proceed with migration
   - If it fails: Continue to step 2

2. **Install Miniforge** (10 minutes)
   - Minimal conda distribution
   - Download from: https://github.com/conda-forge/miniforge
   - Install alongside existing Python (won't interfere)

3. **Create Conda Environment** (5 minutes)
   ```bash
   conda create -n lambertlab python=3.13
   conda activate lambertlab  
   conda install pykep numpy scipy astropy matplotlib spiceypy
   ```

4. **Test PyKEP** (5 minutes)
   - Run compatibility tests
   - Verify Lambert solver works
   - Test fb_prop() function

5. **Migrate Project** (gradual)
   - Update development setup to use conda
   - Keep current venv as backup
   - Migrate incrementally

## Migration Checklist

### Phase 1: Setup & Validation (TODAY)
- [ ] Install Miniforge
- [ ] Create conda environment with Python 3.13
- [ ] Install PyKEP via conda
- [ ] Install other dependencies
- [ ] Run `import pykep; pykep.test.run_test_suite()`
- [ ] Create PyKEP compatibility test script

### Phase 2: Lambert Solver Migration (NEXT SESSION)
- [ ] Map poliastro Lambert API to PyKEP API
- [ ] Update `src/lambertlab/core/lambert_io.py`
- [ ] Update `src/lambertlab/core/solver.py`
- [ ] Run existing tests to validate
- [ ] Fix any breaking changes

### Phase 3: Flyby Function Migration (AFTER LAMBERT)
- [ ] Study `pykep.fb_prop()` signature and behavior
- [ ] Create comparison test: our rotation vs fb_prop()
- [ ] Update `src/lambertlab/flows/flyby.py`
- [ ] Update `src/lambertlab/viz/ui.py` (chain3)
- [ ] Update `src/lambertlab/flows/chain3_tiled.py`
- [ ] Validate chain3 still finds solutions

### Phase 4: Cleanup & Optimization
- [ ] Remove custom flyby rotation code
- [ ] Update documentation
- [ ] Create requirements-conda.txt or environment.yml
- [ ] Run full test suite
- [ ] Update README with conda setup instructions

## Files to Modify

### Lambert Solver Files:
1. `src/lambertlab/core/lambert_io.py` - Main Lambert interface
2. `src/lambertlab/core/solver.py` - Porkchop solver

### Flyby Files:
1. `src/lambertlab/flows/flyby.py` - Flyby computation
2. `src/lambertlab/viz/ui.py` - Chain3 implementation  
3. `src/lambertlab/flows/chain3_tiled.py` - Tiled chain3

### Configuration:
1. Create `environment.yml` for conda setup
2. Update `.gitignore` for conda artifacts
3. Update `README.md` with new setup instructions

## Expected Timeline

- **Setup (Today):** 30 minutes
  - Install Miniforge
  - Create environment
  - Install PyKEP
  - Validate installation

- **Lambert Migration (1-2 hours):**
  - Update 2 files
  - Test and validate
  - Fix issues

- **Flyby Migration (2-3 hours):**
  - Test fb_prop() behavior
  - Update 3 files
  - Extensive testing
  - Validate chain3 results

- **Total:** ~4-6 hours spread over 2-3 sessions

## Rollback Plan

If migration fails:
1. Git branch for migration work
2. Keep existing .venv as backup
3. Can revert to poliastro 0.7.0 anytime
4. All changes version controlled

## Success Criteria

✅ PyKEP Lambert solver produces same results as poliastro
✅ `pykep.fb_prop()` produces same results as our spherical rotation
✅ Chain3 finds solutions (passes deltaV tolerance)
✅ All existing tests pass
✅ Performance is equal or better

---

**Next Action:** Try pip install first, if fails proceed with Miniforge installation.

**Created:** October 9, 2025
**Status:** Ready to begin installation
