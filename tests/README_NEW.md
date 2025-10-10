# LambertLab Test Suite - PyKEP Migration Edition

**Modern, comprehensive test battery for interplanetary trajectory planning**

## Overview

This test suite validates the complete LambertLab system after migration to PyKEP. Tests use realistic mission scenarios with physics-based validation.

## Test Structure

### 🧪 Unit Tests
- **`test_01_lambert_core.py`** - Lambert solver with realistic Earth-Mars transfers
- **`test_02_flyby_physics.py`** - Gravity assist physics validation

### 🔗 Integration Tests
- **`test_03_integration.py`** - Multi-leg trajectories (Earth-Mars-Ceres chains)

### 🚀 Stress Tests
- **`test_04_stress.py`** - Large grids, edge cases, performance benchmarks

### 📦 Configuration
- **`conftest.py`** - Pytest fixtures for SPICE kernels, PyKEP availability

---

## Quick Start

### Run All Tests (Fast)
```bash
conda activate lambertlab
pytest tests/ -v
```

### Run Specific Test Suite
```bash
pytest tests/test_01_lambert_core.py -v
pytest tests/test_02_flyby_physics.py -v
pytest tests/test_03_integration.py -v
```

### Run Stress Tests (Slow)
```bash
pytest tests/test_04_stress.py -v -m slow
```

### Skip Slow Tests
```bash
pytest tests/ -v -m "not slow"
```

---

## Test Coverage

### ✅ Lambert Solver Tests
| Test | Description | Validates |
|------|-------------|-----------|
| `test_earth_mars_2025_transfer` | Realistic 2025 opportunity | C3, TOF, v_inf ranges |
| `test_short_transfer_fails` | Impossible 30-day transfer | Error handling |
| `test_hohmann_approximation` | Long TOF efficiency | C3 < 25 km²/s² |
| `test_multiple_departure_dates` | 5 different departures | C3 variation |

**Expected Results**:
- Earth-Mars C3: 10-30 km²/s²
- TOF: 180-250 days
- Departure v_inf: 2-10 km/s
- Arrival v_inf: 1-8 km/s

### ✅ Flyby Physics Tests
| Test | Description | Validates |
|------|-------------|-----------|
| `test_magnitude_conservation` | Ballistic flyby | \|Δv_inf\| < 1e-6 km/s |
| `test_turn_angle_limit` | Hyperbolic deflection | δ ≤ δ_max |
| `test_low_altitude_high_turn` | rp vs turn angle | δ_low > δ_high |
| `test_bplane_angle_effect` | B-plane rotation | v_inf direction change |

**Physics Constraints**:
- Magnitude conservation: < 1 μm/s error
- Turn angle: δ = 2·arcsin(1/(1 + rp·v²/μ))
- B-plane: Rotation preserves magnitude

### ✅ Integration Tests
| Test | Description | Validates |
|------|-------------|-----------|
| `test_two_leg_missions` | Earth → Mars direct | Porkchop points |
| `test_full_earth_mars_target_chain` | E → M → Target | 3-body chain |
| `test_small_porkchop_grid` | 5x5 grid generation | Grid integrity |

**Chain Validation**:
1. Leg 1 Lambert solve
2. Mars flyby propagation
3. Magnitude conservation at flyby
4. Leg 2 feasibility

### ✅ Stress Tests
| Test | Description | Load |
|------|-------------|------|
| `test_full_month_porkchop` | 30x20 grid (600 pts) | Production scale |
| `test_high_resolution_porkchop` | 0.5-day steps | High precision |
| `test_numerical_stability` | 5 repeated runs | Determinism |
| `test_magnitude_conservation_precision` | 100 random flybys | Physics |
| `test_lambert_solve_speed` | 100 Lambert solves | < 50 ms/solve |
| `test_flyby_propagation_speed` | 1000 propagations | < 500 μs/prop |

**Performance Targets**:
- Lambert solve: < 10 ms
- Flyby propagation: < 100 μs
- Porkchop grid: > 5 points/sec

---

## Fixtures

### `kernel_paths`
Provides SPICE kernel paths. Auto-skips if kernels missing.

```python
@pytest.fixture(scope="session")
def kernel_paths():
    """Required SPICE kernels."""
    return [
        "data/kernels/naif0012.tls",
        "data/kernels/de440.bsp",
        "data/kernels/mar097.bsp",
        "data/kernels/gm_de440.tpc",
        "data/kernels/pck00011.tpc",
    ]
```

### `pykep_available`
Checks PyKEP availability. Auto-skips if not in conda environment.

### `spice_loaded`
Loads SPICE kernels once for all tests (session scope).

---

## Pytest Markers

### `@pytest.mark.slow`
Marks long-running tests (> 30 seconds).

Usage:
```python
@pytest.mark.slow
def test_full_month_porkchop(...):
    # Large grid calculation
    ...
```

Run without slow tests:
```bash
pytest -m "not slow"
```

Run only slow tests:
```bash
pytest -m slow
```

---

## Test Data

### Realistic Mission Parameters

**Earth-Mars 2025 Opportunity**:
```python
EARTH_MARS_2025 = {
    "dep_date": "2025-01-15",
    "arr_date": "2025-08-20",
    "expected_c3_range": (10.0, 30.0),  # km²/s²
    "expected_tof_days": 217,
}
```

**Mars Flyby Scenario**:
```python
MARS_FLYBY_SCENARIO = {
    "altitude_km": 300.0,
    "rp_km": 3696.2,  # Mars radius + 300 km
    "mu_mars": 42828.0,  # km³/s²
    "expected_max_turn_deg": 90.0,
}
```

**Physics Tolerances**:
```python
PHYSICS_TOLERANCES = {
    "vmag_conservation": 1e-6,  # km/s
    "energy_conservation": 1e-3,  # km²/s²
    "position_accuracy": 1e-3,  # km
}
```

---

## Expected Output

### Successful Test Run
```
tests/test_01_lambert_core.py::TestLambertSolver::test_earth_mars_2025_transfer PASSED
✅ Earth-Mars 2025: TOF=217.0d, C3=15.23km²/s², v∞=3.90km/s

tests/test_02_flyby_physics.py::TestFlybyPhysics::test_magnitude_conservation PASSED
✅ Magnitude conservation: |v∞_in|=7.071068, |v∞_out|=7.071068

tests/test_03_integration.py::TestThreeBodyChains::test_full_earth_mars_target_chain PASSED
  Leg 1: Earth → Mars
    C3 = 15.23 km²/s², v∞_arr = 4.12 km/s
  Flyby: Mars gravity assist
    v∞_out = 4.12 km/s
✅ Full chain validated!

tests/test_04_stress.py::TestPerformanceBenchmarks::test_lambert_solve_speed PASSED
✅ Lambert performance: 8.23 ms/solve (100 runs)

========================= 24 passed in 45.3s =========================
```

---

## Troubleshooting

### PyKEP Import Error
```
ImportError: No module named 'pykep'
```

**Solution**: Activate conda environment
```bash
conda activate lambertlab
pytest tests/
```

### Missing SPICE Kernels
```
pytest.skip: Missing SPICE kernels: ['data/kernels/de440.bsp']
```

**Solution**: Download kernels or adjust `kernel_paths` fixture

### Tests Timeout
```
tests/test_04_stress.py::test_full_month_porkchop TIMEOUT
```

**Solution**: Skip slow tests
```bash
pytest -m "not slow"
```

---

## Adding New Tests

### Template
```python
def test_my_new_feature(spice_loaded, pykep_available):
    """Test description."""
    from src.lambertlab.core.solver import compute_c3_tof
    
    # Setup
    dep = "2025-01-15"
    arr = "2025-08-15"
    
    # Execute
    tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep, arr, 'EARTH', 'MARS')
    
    # Validate
    assert 10.0 < c3 < 30.0, f"C3 {c3:.2f} unrealistic"
    
    print(f"✅ My test: C3={c3:.2f}km²/s²")
```

### Best Practices
1. **Use realistic values** - Base on actual missions
2. **Validate physics** - Check energy, momentum conservation
3. **Add print statements** - Show key results
4. **Use descriptive assertions** - Include actual values in error messages
5. **Mark slow tests** - Use `@pytest.mark.slow` for > 30s tests

---

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: conda-incubator/setup-miniconda@v2
        with:
          environment-file: environment.yml
          activate-environment: lambertlab
      - run: pytest tests/ -v -m "not slow"
```

---

## Migration Notes

### Old Tests (Archived)
Old poliastro-based tests moved to `tests/old/`:
- `test_02_lambert_em.py` → Replaced by `test_01_lambert_core.py`
- `test_08_compute_flyby_invariants.py` → Replaced by `test_02_flyby_physics.py`
- `test_12_end_to_end_em_flyby_ceres.py` → Replaced by `test_03_integration.py`
- `test_13_all_up_stress.py` → Replaced by `test_04_stress.py`

### What's Different
- ✅ **PyKEP-based** (was poliastro)
- ✅ **Realistic scenarios** (actual mission parameters)
- ✅ **Physics validation** (magnitude conservation, turn angles)
- ✅ **Performance benchmarks** (speed measurements)
- ✅ **Better organization** (4 clear test modules)

---

## Summary

🎯 **Test Suite Coverage**:
- ✅ 24 tests across 4 modules
- ✅ Unit, integration, stress tests
- ✅ Realistic mission scenarios
- ✅ Physics-based validation
- ✅ Performance benchmarks

**All tests passing** = System ready for production! 🚀
