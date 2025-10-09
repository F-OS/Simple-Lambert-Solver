# Three-Body Chain (chain3) - User Guide

## Overview

The `chain3` command implements comprehensive three-body gravity assist trajectory planning. It searches for optimal trajectories of the form:

**Origin → Flyby → Destination**

For example: Earth → Mars (flyby) → Ceres

## How It Works

### Algorithm Steps

1. **Leg 1 Scan (Departure → Flyby)**
   - Grids over departure epochs and time-of-flight values
   - Computes Lambert solutions to reach the flyby body
   - Records launch C3, arrival v-infinity at flyby, and flyby epoch

2. **Flyby Mapping**
   - For each feasible Leg 1 trajectory:
   - Samples periapsis radii within bounds
   - Samples B-plane rotation angles (theta)
   - Computes gravity turn angle based on classical patched-conic theory
   - Rotates incoming v-infinity to produce outgoing v-infinity
   - Generates post-flyby heliocentric velocity

3. **Leg 2 Scan (Flyby → Arrival)**
   - For each post-flyby state:
   - Scans time-of-flight to arrival body
   - Computes Lambert solution to arrival
   - Records arrival v-infinity and estimated capture Δv

4. **Solution Ranking**
   - Scores solutions by combined metric (C3 + v∞²_arrival)
   - Keeps top N solutions (default 200)
   - Exports comprehensive data for analysis

## Command Line Usage

### Basic Syntax

```bash
python -m lambertlab.cli.main chain3 \
  --kernels <kernel_files...> \
  --dep-body <NAIF_ID> \
  --flyby-body <NAIF_ID> \
  --arr-body <NAIF_ID> \
  --dep-window <start:end> \
  --leg1-tof <min:max:step> \
  --leg2-tof <min:max:step> \
  --rp-bounds <min_km:max_km> \
  --save
```

### Example: Earth-Mars-Ceres

```bash
python -m lambertlab.cli.main chain3 \
  --kernels data/kernels/naif0012.tls \
  --kernels data/kernels/de440.bsp \
  --kernels data/kernels/gm_de440.tpc \
  --kernels data/kernels/20000001.bsp \
  --kernels data/kernels/mar097.bsp \
  --kernels data/kernels/pck00011.tpc \
  --dep-body 399 \
  --flyby-body 499 \
  --arr-body 20000001 \
  --dep-window 2035-04-01:2035-09-01 \
  --dep-step 5 \
  --leg1-tof 150:380:10 \
  --leg2-tof 180:600:20 \
  --rp-bounds 3696.2:13396.2 \
  --bplane-theta=-30:30:7 \
  --max-solutions 200 \
  --save \
  --format table
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--dep-body` | Yes | Departure body NAIF ID | `399` (Earth) |
| `--flyby-body` | Yes | Flyby body NAIF ID | `499` (Mars) |
| `--arr-body` | Yes | Arrival body NAIF ID | `20000001` (Ceres) |
| `--dep-window` | Yes | Departure window start:end (YYYY-MM-DD:YYYY-MM-DD) | `2035-04-01:2035-09-01` |
| `--leg1-tof` | Yes | Leg 1 TOF min:max:step (days) | `150:380:10` |
| `--leg2-tof` | Yes | Leg 2 TOF min:max:step (days) | `180:600:20` |
| `--rp-bounds` | Yes | Periapsis bounds min:max (km) | `3696.2:13396.2` |
| `--dep-step` | No | Departure step (days), default 2 | `5` |
| `--bplane-theta` | No | B-plane rotation min:max:n (deg), default `-30:30:7` | `-20:20:5` |
| `--max-solutions` | No | Max solutions to keep, default 200 | `100` |
| `--dv-tol` | No | Δv match tolerance (m/s), default 100 | `50` |
| `--save` | No | Save artifacts to outdir | flag |
| `--format` | No | Output format: table/json/csv, default table | `table` |

### Tips for Selecting Parameters

**Periapsis Bounds** (`--rp-bounds`):
- Minimum should be: `body_radius + min_altitude`
- For Mars (R = 3396.2 km): use `3696.2` for 300 km altitude
- Maximum: reasonable upper bound like 10,000 km altitude

**B-plane Theta**:
- Controls search over flyby geometry
- More samples = more thorough search but slower
- Typical range: -30° to +30°, 5-7 samples

**Time-of-Flight Ranges**:
- Leg 1: Depends on departure-flyby pair (e.g., Earth-Mars: 150-380 days)
- Leg 2: Depends on flyby-arrival pair (e.g., Mars-Ceres: 180-600 days)
- Larger steps = faster computation but coarser grid

## Interactive Mode

Run the interactive menu:

```bash
python run.py
```

Select option 4: **Three Body Chain (Gravity Assist)**

The interactive flow will guide you through:
1. Selecting departure body
2. Selecting flyby body
3. Selecting arrival body
4. Setting departure window
5. Setting Leg 1 TOF range
6. Setting Leg 2 TOF range
7. Setting periapsis altitude constraints
8. Setting B-plane rotation range

## Output Artifacts

When `--save` is used, the following files are created in the output directory (default: `artifacts/`):

### 1. `chain3_leg1_grid.csv`
Leg 1 (Departure → Flyby) porkchop data:
- `dep_tdb`: Departure epoch (TDB)
- `tof1_days`: Time of flight (days)
- `flyby_tdb`: Flyby arrival epoch (TDB)
- `c3_km2s2`: Launch C3 (km²/s²)
- `vinf_in_mag_kms`: Arrival v-infinity magnitude (km/s)

### 2. `chain3_bplane_grid.csv`
B-plane map data for each flyby:
- `flyby_tdb`: Flyby epoch (TDB)
- `rp_km`: Periapsis radius (km)
- `theta_deg`: B-plane rotation angle (degrees)
- `delta_deg`: Gravity turn angle (degrees)
- `vinf_out_mag_kms`: Outgoing v-infinity magnitude (km/s)

### 3. `chain3_leg2_grid.csv`
Leg 2 (Flyby → Arrival) data:
- `flyby_tdb`: Flyby departure epoch (TDB)
- `tof2_days`: Time of flight (days)
- `arr_tdb`: Arrival epoch (TDB)
- `vinf_arr_kms`: Arrival v-infinity magnitude (km/s)

### 4. `chain3_solutions.csv`
Top-ranked complete trajectories:
- `t_dep_tdb`: Departure epoch
- `t_flyby_tdb`: Flyby epoch
- `t_arr_tdb`: Arrival epoch
- `tof1_days`, `tof2_days`, `tof_total_days`: Time of flight values
- `C3_launch_km2s2`: Launch C3
- `vinf_in_kms`, `vinf_out_kms`: Flyby v-infinity magnitudes
- `rp_km`: Periapsis radius
- `turn_angle_deg`: Gravity turn angle
- `bplane_theta_deg`: B-plane rotation angle
- `vinf_in_vec_kms`, `vinf_out_vec_kms`: 3D v-infinity vectors
- `arr_vinf_kms`: Arrival v-infinity
- `est_capture_dv_ms`: Estimated capture Δv (m/s)
- `score`: Ranking score (lower is better)

### 5. `chain3_meta.json`
Metadata and configuration:
- Input body IDs
- Search parameter ranges
- Kernel files used
- Total and top solution counts

## Interpreting Results

### Solution Scoring

Solutions are ranked by: **score = C3_launch + v∞²_arrival**

This balances:
- **Launch energy** (lower C3 = easier launch)
- **Arrival energy** (lower v∞ = easier capture)

### Key Metrics

- **C3 < 30 km²/s²**: Achievable with many launch vehicles
- **C3 30-60 km²/s²**: Requires medium-heavy lift
- **C3 > 60 km²/s²**: Challenging, requires heavy lift or staging

- **Arrival v∞ < 3 km/s**: Reasonable for orbit capture
- **Arrival v∞ 3-5 km/s**: Moderate capture requirement
- **Arrival v∞ > 5 km/s**: High energy arrival, expensive capture

- **Turn angle**: Larger turn = closer periapsis pass (riskier but more deflection)

### Analysis Workflow

1. **Review top solutions table** to identify promising trajectories
2. **Examine Leg 1 grid** to see porkchop plot data (can visualize in spreadsheet)
3. **Check B-plane map** to understand flyby geometry options
4. **Verify periapsis altitudes** meet safety constraints
5. **Assess total TOF** for mission timeline feasibility

## Common NAIF Body IDs

| Body | NAIF ID |
|------|---------|
| Mercury | 199 |
| Venus | 299 |
| Earth | 399 |
| Mars | 499 |
| Jupiter | 599 |
| Saturn | 699 |
| Uranus | 799 |
| Neptune | 899 |
| Ceres | 2000001 |

## Troubleshooting

**"No feasible solutions found"**:
- Widen departure window
- Expand TOF ranges
- Relax periapsis constraints
- Increase B-plane theta samples
- Check that kernel coverage spans all epochs

**Slow computation**:
- Reduce departure window or step size
- Increase TOF step sizes
- Reduce B-plane theta sample count
- Reduce max-solutions limit

**High Δv match values**:
- Increase `--dv-tol` parameter
- May indicate incompatible trajectory segments

## Advanced Usage

### Custom Scoring

Modify `run_chain3()` in `src/lambertlab/viz/ui.py` to change the scoring function. Current implementation:

```python
'score': float(c3_launch + vinf_arr_mag**2)
```

Examples:
- Minimize total Δv: `score = sqrt(c3_launch) + vinf_arr_mag`
- Minimize TOF: `score = tof1 + tof2`
- Pareto: rank on multiple objectives

### Plotting (Future Enhancement)

The CSV outputs can be visualized:
- **Leg 1**: Porkchop plot (dep_date vs TOF1, color = C3)
- **B-plane**: Heatmap (rp vs theta, color = downstream metric)
- **Leg 2**: Arrival performance (flyby_date vs TOF2, color = v∞)
- **Solutions**: Scatter plot (C3 vs v∞_arr, pareto frontier)

## References

- Patched-conic approximation for gravity assists
- Lambert's problem for two-body trajectory segments
- B-plane targeting for flyby geometry control
- SPICE ephemeris system for body states

---

For questions or issues, refer to the main documentation or open an issue on the repository.
