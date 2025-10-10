# Output Directory Cleanup - Complete ✅

**Date:** October 9, 2025  
**Status:** Consolidation Complete

## Summary

Consolidated all simulation outputs to a single `artifacts/` directory and cleaned up the old `results/` folder structure.

## What Changed

### Before
- Outputs scattered between `results/` and `artifacts/`
- Old `results/` had 36 timestamped subdirectories from previous runs
- Duplicate `lambertlab/` directory with old code
- Unclear which directory was active

### After
- ✅ **Single output directory**: `artifacts/`
- ✅ **Old results archived**: `results/` → `results_archive_pre_cleanup/`
- ✅ **Old duplicate code removed**: `lambertlab/` directory deleted
- ✅ **Clear documentation**: `artifacts/README.md` explains structure

## Output Structure

All simulations now save to `artifacts/`:

```
artifacts/
├── README.md                    # Documentation
├── porkchop.png                 # Porkchop plots (em-grid)
├── em_grid.csv                  # Full grid data
├── em_minima.json               # Best transfer points
├── flyby.json                   # Flyby trajectories
├── mc_grid.csv                  # Mars-Ceres screening
├── chain3_leg1_grid.csv         # Chain3 Earth-Mars leg
├── chain3_bplane_grid.csv       # Chain3 B-plane search
├── chain3_leg2_grid.csv         # Chain3 Mars-Target leg
├── chain3_solutions.csv         # Chain3 complete solutions
└── chain3_meta.json             # Chain3 metadata
```

## Testing

Verified with test run:

```bash
python -m lambertlab.cli.main em-grid \
  --kernels data/kernels/naif0012.tls \
  --kernels data/kernels/de440.bsp \
  --kernels data/kernels/gm_de440.tpc \
  --kernels data/kernels/mar097.bsp \
  --kernels data/kernels/pck00011.tpc \
  --dep-start 2026-06-24 \
  --dep-end 2026-06-26 \
  --dep-step 1 \
  --tof-min 195 \
  --tof-max 200 \
  --tof-step 1 \
  --dep-id 399 \
  --arr-id 499 \
  --save
```

**Result:** ✅ `Plot saved as artifacts\porkchop.png`

## Files Updated

1. **`.gitignore`** - Updated comments to clarify output structure
2. **`artifacts/README.md`** - Created documentation for output structure
3. **Deleted**: `lambertlab/` (old duplicate directory)
4. **Archived**: `results/` → `results_archive_pre_cleanup/`

## Configuration

The default output directory is `artifacts/` (set in `src/lambertlab/cli/main.py`):

```python
p.add_argument("--outdir", default="artifacts")
```

Users can override with `--outdir custom_dir` if needed.

## Archive

Old results preserved in:
```
results_archive_pre_cleanup/
├── 20251006_183634/
├── 20251006_183703/
├── ... (36 total items)
├── EMC_Porkchop_Test.npz
├── EMC_Porkchop_Test.png
└── ... (various test outputs)
```

**Note:** This archive is gitignored and can be deleted after verification.

## Next Steps

### Recommended
- ✅ Done! System is clean and working.

### Optional
- Delete `results_archive_pre_cleanup/` after confirming you don't need old outputs
- Add timestamped subdirectories if you want to preserve multiple runs:
  ```python
  timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
  outdir = f"artifacts/{timestamp}"
  ```

## Conclusion

All outputs now go to a single, well-documented `artifacts/` directory. No more confusion about where files are saved! 🎯
