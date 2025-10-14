# Transfer Screening Guide

## Overview

Transfer screening is a trajectory analysis technique that evaluates the v∞ (velocity at infinity) requirements for transfers from a **fixed departure date** to an arrival body across a range of time-of-flight (TOF) values. This is particularly useful for:

- **Gravity Assist Planning**: After identifying a good flyby opportunity, screen continuation legs to potential destinations
- **Mission Feasibility**: Determine if reaching a target is possible within spacecraft C3 constraints
- **Trajectory Optimization**: Find optimal TOF values for constrained departure dates

## Key Concepts

### What is v∞?
- **v∞ (v-infinity)**: The spacecraft's velocity relative to a body when far from its gravity well
- Represents the "excess" velocity beyond what's needed to just escape the body's sphere of influence
- For gravity assists, the **outbound v∞** after a flyby determines what destinations are reachable

### What is C3?
- **C3 = v∞²**: The characteristic energy, measured in km²/s²
- Common mission constraint (e.g., "C3 < 30 km²/s²" for a particular launch vehicle)
- Lower C3 = easier/cheaper mission

### The Lambert Problem
Given two positions (departure and arrival) and a transfer time:
1. Solve for the required departure and arrival velocities
2. Compare required departure velocity to the body's actual velocity
3. The difference is the required v∞

## When to Use Transfer Screening

### Scenario 1: After a Planetary Flyby
You've designed a Mars flyby on 2025-06-01 and want to continue to Ceres:
```bash
lambertlab transfer-screen \
  --kernels data/kernels/*.bsp \
  --dep-epoch 2025-06-01 \           # Fixed: Mars encounter date
  --arr-window 2025-10-01:2026-02-01 \  # Flexible: Ceres arrival window
  --tof-min 150 --tof-max 400 \
  --dep-body 499 --arr-body 20000001 \
  --c3-cap 50.0
```

**Output**: A table showing C3 values for each TOF that places arrival within the window

### Scenario 2: Constrained Launch Date
Your launch vehicle has a fixed launch date, but arrival date is flexible:
```bash
lambertlab transfer-screen \
  --dep-epoch 2026-08-15 \           # Fixed: Launch date
  --arr-window 2027-01-01:2028-01-01 \  # Flexible: Mars arrival
  --tof-min 200 --tof-max 600 \
  --dep-body 399 --arr-body 499
```

### Scenario 3: Gravity Assist Chain Design
You're building a 3-body chain and need to screen the second leg:
1. Run `transfer-grid` to get Earth→Mars opportunities
2. Pick a Mars arrival date with good C3
3. Run `transfer-screen` from that Mars date to Ceres
4. Combine results to build full chain

## Comparison: Grid vs Screening

| Feature | Transfer Grid (`transfer-grid`) | Transfer Screening (`transfer-screen`) |
|---------|--------------------------------|---------------------------------------|
| **Departure** | Range of dates | Single fixed date |
| **Output** | 2D grid (dep × TOF) | 1D array (TOF only) |
| **Use Case** | Find optimal launch windows | Evaluate continuation from fixed point |
| **Visualization** | Porkchop plot with C3 contours | Table or 1D plot of C3 vs TOF |

## Command Reference

```bash
lambertlab transfer-screen \
  --kernels <kernel_files> \      # SPICE kernel files
  --dep-epoch <date> \            # Fixed departure date (YYYY-MM-DD)
  --arr-window <start:end> \      # Arrival window (start:end dates)
  --tof-min <days> \              # Minimum TOF to evaluate
  --tof-max <days> \              # Maximum TOF to evaluate
  --tof-step <days> \             # TOF step size (default: 10)
  --dep-body <naif_id> \          # Departure body NAIF ID
  --arr-body <naif_id> \          # Arrival body NAIF ID
  --c3-cap <value> \              # Optional: Filter trajectories above this C3
  --save                          # Save results to artifacts/
```

## Output Files

When using `--save`, screening produces:

### `transfer_grid.csv`
Tabular results with columns:
- `dep_tdb`: Departure epoch (fixed for all rows)
- `tof_days`: Time of flight
- `c3`: Characteristic energy (km²/s²)
- `arr_tdb`: Arrival epoch (dep + TOF)
- `dep_idx`: Always 0 (single departure)
- `tof_idx`: Index in TOF array

### `transfer_minima.json`
Single best (minimum C3) trajectory found:
```json
[
  {
    "dep_tdb": "2025-06-01T00:00:00.000",
    "tof_days": 215,
    "c3": 32.45,
    "arr_tdb": "2025-12-03T00:00:00.000",
    "dep_body": "499",
    "arr_body": "20000001"
  }
]
```

## Interactive Mode

Run `python run.py` and select option **3. Two Body Screening**:

```
=== Two Body Screening ===
Screen v∞ requirements from a fixed departure date to an arrival body.
Useful for evaluating continuation legs after a planetary encounter.

Fixed departure date (YYYY-MM-DD) [2025-06-01]: 
Departure body (where you're leaving from):
Common: 499 (Mars), 299 (Venus), 399 (Earth)
Enter NAIF ID or name [499 Mars]: 

Arrival time window:
Specify the range of acceptable arrival dates.
Arrival start date (YYYY-MM-DD) [2025-10-01]: 
Arrival end date (YYYY-MM-DD) [2026-02-01]: 

Arrival body (destination):
Common: 20000001 (Ceres), 599 (Jupiter), 699 (Saturn)
Enter NAIF ID or name [20000001 Ceres]: 

Time-of-flight (TOF) search range:
Minimum TOF (days) [150]: 
Maximum TOF (days) [400]: 
TOF step (days) [5]: 

Optional: C3 cap (km²/s²) to filter high-energy trajectories [none]: 50
```

## Tips & Best Practices

1. **Choose TOF Range Wisely**: 
   - Too narrow: May miss optimal solutions
   - Too wide: Wastes computation on infeasible trajectories
   - Use Hohmann transfer time as a starting point

2. **Set C3 Cap Appropriately**:
   - Launch vehicles: 20-40 km²/s² typical
   - Gravity assists: 10-100+ km²/s² depending on velocity
   - No cap: See full solution space, filter later

3. **Arrival Window Selection**:
   - Must overlap with (dep_epoch + TOF range)
   - Wider windows give more flexibility
   - Can post-process to further constrain

4. **Common NAIF IDs**:
   - 10: Sun
   - 199: Mercury
   - 299: Venus
   - 399: Earth
   - 499: Mars
   - 599: Jupiter
   - 699: Saturn
   - 20000001: Ceres (dwarf planet)

## Example Workflow: Mars→Ceres Transfer

```bash
# 1. First, find good Earth→Mars opportunities
lambertlab transfer-grid \
  --kernels data/kernels/*.bsp \
  --dep-start 2025-01-01 --dep-end 2025-06-01 \
  --tof-min 180 --tof-max 300 \
  --dep-body 399 --arr-body 499 \
  --save

# Review porkchop plot → Identify Mars arrival on 2025-06-01 with C3=15 km²/s²

# 2. Screen Mars→Ceres continuation opportunities
lambertlab transfer-screen \
  --kernels data/kernels/*.bsp \
  --dep-epoch 2025-06-01 \
  --arr-window 2025-10-01:2026-03-01 \
  --tof-min 150 --tof-max 400 \
  --dep-body 499 --arr-body 20000001 \
  --c3-cap 50.0 \
  --save

# Review transfer_minima.json → Best TOF is 215 days with C3=32 km²/s²

# 3. Verify if Mars flyby can deliver required v∞
# (Use flyby command to check if C3_in=15 can bend to C3_out=32)
```

## Troubleshooting

### "No feasible trajectories found"
- Widen TOF range
- Relax C3 cap
- Check arrival window overlaps with dep+TOF range
- Verify SPICE kernels cover time period

### "All C3 values too high"
- Departure geometry may be poor
- Try different departure date
- Consider gravity assist to reduce energy

### "Arrival window too restrictive"
- Widen the window
- Check if window placement makes sense
- May need intermediate flyby

## Further Reading

- Lambert Problem: Classical orbital mechanics textbook topic
- Pykep Documentation: https://esa.github.io/pykep/
- NAIF SPICE Toolkit: https://naif.jpl.nasa.gov/naif/
