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

```bash
pip install -e .
```

## Usage

```bash
# Generate Earth-Mars porkchop plot
lambertlab em-grid --kernels data/kernels/*.bsp --dep-start 2025-01-01 --dep-end 2025-02-01 --tof-min 100 --tof-max 300

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