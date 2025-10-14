# Simple Lambert Solver

A comprehensive tool for Lambert solver calculations with SPICE integration for trajectory optimization and mission planning.

## Features

- **Two-Body Transfer Grid (Porkchop Plots)**: Generate comprehensive departure/arrival grids showing C3 contours for optimal launch windows
- **Transfer Screening**: Evaluate v∞ requirements for specific departure dates across time-of-flight ranges
- **Flyby Optimization**: Compute gravity assist trajectories with B-plane targeting
- **Three-Body Chains**: Find optimal gravity assist sequences through intermediate bodies
- **SPICE Integration**: Accurate ephemerides using NASA's SPICE toolkit
- **Command-Line Interface**: Multiple subcommands for different trajectory analysis modes
- **Reproducible Results**: Array hashing and checkpointing for computational integrity

## Installation

### Prerequisites
- Python 3.8+
- Conda (required for PyKEP)

### Setup

1. **Create and activate the lambertlab conda environment:**
   ```bash
   conda create -n lambertlab python=3.13
   conda activate lambertlab
   ```

2. **Install PyKEP (conda only - not available on PyPI):**
   ```bash
   conda install -c conda-forge pykep
   ```

3. **Install the package:**
   ```bash
   pip install -e .
   ```

### Important: Environment Activation
**Always activate the `lambertlab` conda environment before running any commands:**
```bash
conda activate lambertlab
python run.py         # For interactive menu
# OR
python -m lambertlab.cli.main em-grid [options]  # For command-line
```

If you see `ModuleNotFoundError: No module named 'lambertlab'` or missing porkchop plots, you're likely in the wrong environment!

## Documentation

- **[Transfer Screening Guide](docs/TRANSFER_SCREENING.md)** - Comprehensive guide to v∞ screening functionality
- **[Repository Structure](STRUCTURE.md)** - Directory organization and module layout
- **[Checkpoint System](CHECKPOINT_SYSTEM.md)** - Resumable computation details

## Usage

### Quick Start: Earth-Mars Transfer (2035-2037 Window)
The **2035-2037** transfer window offers excellent Earth-Mars geometry with C3 values as low as 10.34 km²/s²:

```bash
conda activate lambertlab
python run.py
# Select option 1 (Two Body Grid)
# Use defaults: 2035-04-01 to 2035-09-01, TOF 200-600 days
```

### Command-Line Examples

#### 1. Two-Body Transfer Grid (Porkchop Plot)
Generate a comprehensive departure/arrival grid showing C3 contours:

```bash
lambertlab transfer-grid \
  --kernels data/kernels/*.bsp \
  --dep-start 2035-01-01 --dep-end 2035-09-01 --dep-step 3 \
  --tof-min 200 --tof-max 600 --tof-step 10 \
  --dep-body 399 --arr-body 499 \
  --save
```

This creates a porkchop plot showing launch C3 for Earth→Mars transfers.

#### 2. Transfer Screening
Screen v∞ requirements for a fixed departure date across multiple arrival windows:

```bash
lambertlab transfer-screen \
  --kernels data/kernels/*.bsp \
  --dep-epoch 2025-06-01 \
  --arr-window 2025-10-01:2026-02-01 \
  --tof-min 150 --tof-max 400 --tof-step 5 \
  --dep-body 499 --arr-body 20000001 \
  --c3-cap 50.0 \
  --save
```

**What it does:**
- Fixes departure at Mars on 2025-06-01
- Evaluates all TOF values (150-400 days in 5-day steps)
- Filters to arrivals at Ceres between 2025-10-01 and 2026-02-01
- Computes required C3 (v∞²) for each feasible trajectory
- Filters out trajectories exceeding C3 = 50 km²/s²

**Use cases:**
- Screening flyby opportunities after a fixed planetary encounter
- Computing v∞ requirements for gravity assist design
- Identifying optimal TOF for constrained departure dates

#### 3. Flyby Trajectory Optimization
Optimize a gravity assist maneuver with B-plane targeting:

```bash
lambertlab flyby \
  --kernels data/kernels/*.bsp \
  --epoch 2025-06-01 \
  --planet-id 499 --target-id 20000001 \
  --r-body 3396 --alt-min 300 \
  --vinf-in 5.0 0.0 0.0 \
  --save
```

#### 4. Three-Body Chain (Gravity Assist Sequence)
Find optimal Earth→Mars→Ceres trajectories with gravity assist:

```bash
lambertlab chain3 \
  --kernels data/kernels/*.bsp \
  --dep-body 399 --flyby-body 499 --arr-body 20000001 \
  --dep-window 2025-01-01:2025-06-01 --dep-step 3 \
  --leg1-tof 150:300:5 --leg2-tof 200:500:10 \
  --rp-bounds 3696:10000 \
  --checkpoint --tile-size 10 \
  --save
```

## CLI Commands Reference

### `transfer-grid`
Generate two-body transfer grids (porkchop plots) showing C3 contours across departure/TOF space.

**Key Parameters:**
- `--dep-start/--dep-end/--dep-step`: Departure window and step size (days)
- `--tof-min/--tof-max/--tof-step`: Time-of-flight range (days)
- `--dep-body/--arr-body`: NAIF IDs for departure/arrival bodies
- `--c3-cap`: Optional C3 limit for filtering trajectories

### `transfer-screen`
Screen v∞ requirements for a fixed departure date across TOF/arrival windows.

**Key Parameters:**
- `--dep-epoch`: Fixed departure date (ISO format: YYYY-MM-DD)
- `--arr-window`: Arrival time window as "start:end"
- `--tof-min/--tof-max/--tof-step`: Time-of-flight search range
- `--c3-cap`: Optional C3 limit (km²/s²)

**Typical Use:** After identifying a good departure opportunity from a porkchop plot, use screening to evaluate continuation legs to other destinations.

### `flyby`
Compute gravity assist flyby trajectories with B-plane targeting.

**Key Parameters:**
- `--epoch`: Flyby epoch
- `--planet-id/--target-id`: Flyby body and post-flyby target
- `--vinf-in`: Incoming v∞ vector (3 components, km/s)
- `--rp/--alt-min`: Periapsis radius or minimum altitude (km)

### `chain3`
Find optimal three-body gravity assist sequences.

**Key Parameters:**
- `--dep-body/--flyby-body/--arr-body`: NAIF IDs for origin/flyby/destination
- `--dep-window`: Departure time window
- `--leg1-tof/--leg2-tof`: TOF ranges as "min:max:step"
- `--rp-bounds`: Flyby periapsis range as "min:max" (km)
- `--checkpoint`: Enable resumable checkpointed computation

## Project Structure

```
simple-lambert-solver/
├── src/lambertlab/
│   ├── core/          # Core math and SPICE utilities
│   ├── flows/         # High-level workflow functions
│   ├── viz/           # Plotting and visualization
│   └── cli/           # Command-line interface
├── data/kernels/      # SPICE kernel files
├── artifacts/         # Temporary outputs
├── results/           # Reproducible artifacts
└── tests/             # Unit tests
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
isort src/
```