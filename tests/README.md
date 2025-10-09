# LambertLab Test Suite

This directory contains the test suite for LambertLab, a trajectory planning toolkit for interplanetary missions.

## Test Structure

- `conftest.py`: Pytest fixtures for kernel paths and test dates
- `test_shakedown.py`: Shakedown tests for core functionality

## Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest test_shakedown.py::test_kernel_loading

# Run with verbose output
pytest -v
```

## Test Fixtures

### `kernel_paths`
Provides paths to required SPICE kernels:
- Leap seconds kernel (naif0012.tls)
- Planetary ephemeris (de440.bsp)
- Mars gravity model (mar097.bsp)
- Ceres ephemeris (20000001.bsp)

### `dates`
Provides test dates for trajectory computations:
- `em_dep`: Earth-Mars departure time
- `em_arr`: Earth-Mars arrival time
- `mc_arr`: Mars-Ceres arrival time

## Test Coverage

The shakedown tests verify:
1. **Kernel Loading**: SPICE kernels can be loaded without errors
2. **Earth-Mars Trajectories**: Trajectory computation produces valid C3 values
3. **Mars-Ceres Requirements**: Flyby requirement computation works
4. **End-to-End Workflow**: Complete Earth-Mars-Ceres mission analysis

## Handling Kernel Coverage Issues

Tests automatically skip if the available SPICE kernels don't cover the test dates, ensuring the test suite works with different kernel sets.

## Adding New Tests

1. Add test functions to `test_*.py` files
2. Use the `kernel_paths` and `dates` fixtures
3. Handle SPICE errors gracefully with try/except blocks
4. Skip tests when kernel coverage is insufficient