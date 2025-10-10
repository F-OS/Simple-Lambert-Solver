# Simple Lambert Solver - Directory Structure

## Active Directories

### `/src/lambertlab/` - Main Source Code
The active Python package (installed with `pip install -e .`)

```
src/lambertlab/
├── __init__.py
├── cli/
│   └── main.py           # CLI entry point
├── core/
│   ├── solver.py         # Lambert solver with PyKEP
│   ├── spice_io.py       # SPICE kernel loading
│   ├── config.py         # Default configurations
│   ├── types.py          # Type definitions
│   └── checkpoint.py     # Checkpoint system
├── flows/
│   ├── em_only.py        # Earth-Mars transfers
│   ├── flyby.py          # Gravity assist computations
│   ├── emc_screen.py     # EMC screening
│   ├── chain3_tiled.py   # Three-body chains
│   └── validate_arc.py   # Trajectory validation
└── viz/
    ├── ui.py             # UI logic for all commands
    ├── porkchop.py       # Porkchop plot generation
    └── plotter.py        # General plotting utilities
```

### `/data/kernels/` - SPICE Ephemeris Data
NASA NAIF SPICE kernels for planetary ephemeris

```
data/kernels/
├── naif0012.tls        # Leapseconds kernel
├── de440.bsp           # Planetary ephemeris
├── mar097.bsp          # Mars satellites
├── gm_de440.tpc        # Gravitational parameters
├── pck00011.tpc        # Planetary constants
└── 20000001.bsp        # Ceres ephemeris
```

### `/artifacts/` - Output Directory (gitignored)
All simulation outputs save here

```
artifacts/
├── README.md           # Output documentation
├── porkchop.png        # Generated plots
├── em_grid.csv         # Grid data
├── flyby.json          # Flyby results
└── chain3_*.csv        # Chain3 outputs
```

### `/tests/` - Test Suite
PyKEP-based test battery (28 tests, 100% passing)

```
tests/
├── conftest.py                  # Pytest fixtures
├── test_01_lambert_core.py      # Lambert solver tests
├── test_02_flyby_physics.py     # Gravity assist physics
├── test_03_integration.py       # Multi-leg trajectories
├── test_04_stress.py            # Performance benchmarks
├── run_tests.py                 # Test runner utility
├── TEST_RESULTS.md              # Test results summary
└── archived_tests_pre_pykep/    # Old poliastro tests
```

### `/test_configs/` - Saved Simulation Configs
User-saved configurations for repeated runs

```
test_configs/
├── two_body_grid_*.json
├── flyby_*.json
└── three_body_chain_*.json
```

## Utility Scripts

- **`run.py`** - Interactive simulation runner (menu-driven UI)
- **`check_kernels.py`** - Verify SPICE kernels are loaded
- **`check_flyby.py`** - Test flyby computations

## Configuration Files

- **`pyproject.toml`** - Python package configuration
  - Dependencies: numpy, scipy, matplotlib, astropy, spiceypy, pykep, typer, rich
  - Package metadata and pytest configuration
  
- **`environment.yml`** - Conda environment specification
  - Use: `conda env create -f environment.yml`

- **`.vscode/`** - VS Code workspace settings
  - `settings.json` - Python interpreter: `lambertlab` conda environment
  - `launch.json` - Debug configurations

## Archived/Documentation

- **`results_archive_pre_cleanup/`** - Old outputs (can be deleted)
- **`PYKEP_MIGRATION_COMPLETE.md`** - PyKEP migration notes
- **`OUTPUT_CLEANUP.md`** - Output directory consolidation summary
- **`START_HERE.md`** - Quick start guide

## What's Gitignored

```
artifacts/              # All outputs
results*/               # Old results
test_artifacts/         # Test outputs
*.npz, *.png, *.csv    # Data files
__pycache__/           # Python cache
.venv/                 # Virtual environment
*.egg-info/            # Build artifacts
```

## Usage Examples

### Run Porkchop Plot
```bash
python -m lambertlab.cli.main em-grid \
  --kernels data/kernels/*.tls \
  --dep-start 2026-06-24 \
  --dep-end 2026-07-01 \
  --tof-min 190 --tof-max 210 \
  --save
```

### Run Interactive Menu
```bash
python run.py
```

### Run Tests
```bash
pytest tests/test_01_lambert_core.py tests/test_02_flyby_physics.py \
       tests/test_03_integration.py tests/test_04_stress.py -v
```

## Key Technologies

- **PyKEP 2.6** - Lambert solver and gravity assist propagation
- **SPICE** - NASA ephemeris system via spiceypy
- **Astropy** - Time handling and astronomical calculations
- **NumPy/SciPy** - Numerical computations
- **Matplotlib** - Plotting and visualization
- **Typer/Rich** - CLI framework and terminal UI

---

**Last Updated:** October 9, 2025  
**Branch:** Flyby-Solver  
**Status:** Production Ready ✅
