# Simple Lambert Solver

A comprehensive tool for Lambert solver calculations with SPICE integration for trajectory optimization and mission planning.

## Features

- Earth-Mars porkchop plot generation
- Flyby trajectory optimization
- Multi-body trajectory screening
- SPICE kernel integration for accurate ephemerides
- Command-line interface with multiple subcommands
- Reproducible results with array hashing

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

```bash
# Generate Earth-Mars porkchop plot
lambertlab em-grid --kernels data/kernels/*.bsp --dep-start 2035-01-01 --dep-end 2038-01-01 --tof-min 200 --tof-max 600

# Optimize flyby trajectory
lambertlab flyby --kernels data/kernels/*.bsp --epoch 2025-06-01 --vinf-in 5.0 0.0 0.0

# Screen multi-body trajectories
lambertlab mc-screen --kernels data/kernels/*.bsp --dep-epoch 2025-01-01 --arr-window 2025-04-01:2025-08-01
```

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