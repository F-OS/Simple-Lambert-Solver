# Quick Reference: Debugging Chain3 Computations

## TL;DR - What Happened

Your computation **didn't freeze** - it processed **172 MILLION** combinations over many hours and found **ZERO solutions** because the deltaV tolerance (100 m/s) was too strict for Mars→Ceres transfers.

## Quick Diagnosis

```powershell
# Check if Python is still running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Check output file sizes
Get-ChildItem artifacts\chain3*.csv | Select Name, @{N="MB";E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime

# Count solutions in each stage
(Get-Content artifacts\chain3_leg1_grid.csv).Count - 1    # Leg 1 count
(Get-Content artifacts\chain3_bplane_grid.csv).Count - 1  # B-plane count
(Get-Content artifacts\chain3_leg2_grid.csv).Count - 1    # Leg 2 count
(Get-Content artifacts\chain3_solutions.csv).Count - 1    # Final count
```

## Your Last Run Analysis

| Stage | Expected | Got | Status |
|-------|----------|-----|--------|
| Leg 1 solutions | ~5,600 | 5,610 | ✓ Complete |
| B-plane geometries | ~840K | 841,500 | ✓ Complete |
| Leg 2 Lambert solves | 172M | 172M | ✓ Complete |
| Leg 2 solutions | ??? | 0 | ✗ All filtered |
| Final chains | ??? | 0 | ✗ No valid chains |

**Computation completed**: ~2025-10-08 06:36 AM (ran for many hours)

## Why Zero Solutions

The code checks if the flyby exit velocity matches the Leg 2 Lambert entry velocity:

```python
dv_match = np.linalg.norm(v_sc_post - v1_arr)
if dv_match * 1000 > args.dv_tol:  # 100 m/s default
    continue  # REJECT!
```

For Mars→Ceres with gravity assist, typical mismatches are **200-1000 m/s**, so with `dv_tol=100`, everything was rejected.

## Quick Test (Run This First!)

I've created a test config that will complete in **5-10 minutes**:

### Option 1: Use the saved config
```bash
# In run.py menu:
# Select option 4 (Three Body Chain)
# When asked "Load from saved config?", enter: y
# Select: Earth_Mars_Ceres_QUICK_TEST.json
```

### Option 2: Manual entry
```
Departure window start: 2035-04-01
Departure window end:   2035-05-01
Departure step:         5 days
Leg 1 TOF min:          150 days
Leg 1 TOF max:          380 days
Leg 1 TOF step:         50 days
Leg 2 TOF min:          180 days
Leg 2 TOF max:          600 days
Leg 2 TOF step:         100 days
B-plane theta min:      -30 degrees
B-plane theta max:      30 degrees
B-plane theta samples:  5
DV tolerance:           1000 m/s  ← KEY FIX!
```

This reduces the search space from 172M to ~500K combinations (99.7% smaller).

## Computation Size Calculator

```
Total combinations = 
  (departure_days) × 
  (leg1_tof_samples) × 
  (bplane_samples) × 
  (rp_samples) × 
  (leg2_tof_samples)

Your last run:
  1096 × 51 × 15 × 50 × 41 = 172,569,000 combinations

Recommended test:
  30 × 5 × 5 × 50 × 5 = 187,500 combinations
```

## Checkpointed Mode (For Large Runs)

For computations > 1 million combinations, use checkpoint mode:

```bash
python -m lambertlab.cli.main chain3 \
  --checkpoint \
  --tile-size 10 \
  --checkpoint-sec 30 \
  --resume \
  [other parameters...]
```

Benefits:
- Saves progress every 30 seconds
- Resumable if interrupted
- Shows tile-by-tile progress

## Recommended Parameters for Production

Once the quick test works, gradually expand:

### Phase 1: Find the best month
```
Departure window: 3-month scan with 10-day steps
Leg 1/2 TOF: Coarse steps (50-100 days)
B-plane: 5-7 samples
DV tolerance: 1000 m/s
```

### Phase 2: Refine the best month  
```
Departure window: Best month ± 2 weeks with 2-day steps
Leg 1/2 TOF: Finer steps (10-20 days)
B-plane: 15 samples
DV tolerance: 500 m/s
```

### Phase 3: Polish the best solution
```
Departure window: Best week with 1-day steps
Leg 1/2 TOF: Fine steps (5 days)
B-plane: 30 samples
DV tolerance: 200 m/s
```

## Signs Your Computation Is Working

✓ `chain3_leg1_grid.csv` grows to several KB
✓ `chain3_bplane_grid.csv` grows to several MB
✓ **`chain3_leg2_grid.csv` is NOT empty** ← This should now work!
✓ `chain3_solutions.csv` has at least a few solutions

## Debug Checklist

- [ ] Ran quick test and got solutions?
- [ ] Verified dv_tol is set to 500+ m/s?
- [ ] Search space is reasonable (< 1M combinations)?
- [ ] Checked file timestamps show recent activity?
- [ ] Progress bar showing updates?
- [ ] No Python processes consuming 100% CPU for days?

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| leg2_grid.csv is empty | dv_tol too strict | Increase to 500-1000 m/s |
| Computation takes forever | Search space too large | Reduce window/steps |
| No progress updates | Nested loops too deep | Enable checkpoint mode |
| "Import Error" messages | Bytecode cache stale | Delete `__pycache__` folders |

## Emergency Stop

If a computation is stuck or taking too long:

```powershell
# Force stop all Python processes
Stop-Process -Name python -Force

# Clean up cache
Remove-Item -Recurse -Force __pycache__, src\**\__pycache__

# Delete partial results (if desired)
Remove-Item artifacts\chain3*.csv, artifacts\chain3*.json
```

## Next Steps

1. ✅ Delete old results: `Remove-Item artifacts\chain3*.*`
2. ✅ Run quick test with dv_tol=1000
3. ✅ Verify you get solutions in `chain3_leg2_grid.csv`
4. ✅ Gradually expand search space
5. ✅ Use checkpoint mode for large runs
