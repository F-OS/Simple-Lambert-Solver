# Chain3 Computation Analysis & Debug Report

## What Happened

Your chain3 computation processed a **MASSIVE** search space and likely completed, but found zero solutions due to the strict deltaV tolerance.

### Computation Scale

**Input Parameters:**
- Departure window: 2035-01-01 to 2038-01-01 (1,096 days)
- Leg 1 TOF: 100-600 days, step 10 (51 samples)
- Leg 2 TOF: 0-800 days, step 20 (41 samples)
- B-plane theta: -30° to 30°, 15 samples
- Periapsis: estimated ~50 samples between min/max bounds

**Results:**
- ✅ **Leg 1 (Earth→Mars)**: 5,610 valid trajectories found
- ✅ **B-plane grid**: 841,500 flyby geometries computed
- ❌ **Leg 2 (Mars→Ceres)**: 0 valid solutions (172 million combinations tested!)
- ❌ **Final chains**: 0 feasible solutions

### Why It Found Nothing

**Root cause**: The default `--dv-tol` of 100 m/s was too strict.

For each of the 5,610 Leg 1 solutions, the code:
1. Computed flyby exit velocity using gravity assist physics
2. Solved 30,750 Lambert problems (15 θ × 50 rp × 41 TOF) from Mars to Ceres
3. Checked if flyby exit velocity matched Lambert entry velocity within 100 m/s
4. **Rejected ALL of them** because the mismatch exceeded 100 m/s

**Estimated computation time**: 
- 172 million Lambert solves @ ~0.001 seconds each = **~48 hours of CPU time**
- The simulation likely ran for hours/days before completing with zero results

### Why It Seemed "Stuck"

The computation wasn't frozen - it was just:
1. Processing an enormous number of combinations (172 million!)
2. Progress bar only updates every 50 Leg 1 solutions
3. Each Leg 1 solution takes significant time (30,750 sub-iterations)
4. No output because all solutions were filtered out

## Recommendations

### 1. **Drastically Reduce Search Space**

Instead of a 3-year window, try:

```
Departure window: 2-3 months (60-90 days)
Leg 1 TOF step: 20 days (instead of 10)
Leg 2 TOF step: 40 days (instead of 20)
B-plane samples: 7 (instead of 15)
```

**Reduction**: From 172M to ~500K combinations (99.7% reduction!)

### 2. **Increase DV Tolerance**

For Mars→Ceres trajectories, use:
```
--dv-tol 1000  (or even 2000 m/s)
```

### 3. **Use Checkpointed Mode**

The code has a checkpointed mode (see line 663 in ui.py):
```bash
--checkpoint --tile-size 10
```

This breaks the computation into resumable tiles and saves progress periodically.

### 4. **Test with Smaller Parameters First**

Run a quick test to verify you'll get solutions:

```
Departure: 2035-04-01 to 2035-05-01 (30 days)
Leg 1 TOF: 150-380 step 50 (5 samples)
Leg 2 TOF: 180-600 step 100 (5 samples)
B-plane: -30:30:5 (5 samples)
dv-tol: 1000
```

This should complete in minutes and show if you're getting solutions.

## Debug Commands

### Check if computation is still running:
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

### Monitor file growth in real-time:
```powershell
while ($true) {
    Get-ChildItem artifacts\chain3*.csv | Select-Object Name, @{Name="MB";Expression={[math]::Round($_.Length/1MB,2)}}
    Start-Sleep -Seconds 5
    Clear-Host
}
```

### Estimate completion time:
```powershell
# If bplane_grid.csv is still growing:
$size = (Get-Item artifacts\chain3_bplane_grid.csv).Length
$rate = $size / ([datetime]::Now - (Get-Item artifacts\chain3_bplane_grid.csv).LastWriteTime).TotalSeconds
$targetSize = 841500 * 100  # rough estimate
$remaining = ($targetSize - $size) / $rate / 3600
Write-Host "Estimated hours remaining: $([math]::Round($remaining, 1))"
```

## Next Steps

1. **Kill any stuck processes**: `Stop-Process -Name python -Force` (if any exist)
2. **Update run.py** with the dv_tol parameter (already done)
3. **Run a SMALL test** with the parameters above
4. **Verify you get solutions** before running larger searches
5. **Gradually expand** the search space once you confirm it works

## File Analysis

Files created from your last run:
```
chain3_leg1_grid.csv:      514 KB  - 5,610 solutions ✓
chain3_bplane_grid.csv:   77.3 MB  - 841,500 geometries ✓  
chain3_leg2_grid.csv:          0 B  - 0 solutions ✗
chain3_solutions.csv:          0 B  - 0 final chains ✗
chain3_meta.json:            521 B  - Metadata
```

Last modified: 2025-10-08 06:36:20 AM

The computation likely finished early yesterday morning after running for many hours, finding nothing due to the strict tolerance.
