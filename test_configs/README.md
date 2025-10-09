# Test Configuration Files

This directory contains saved test configurations for LambertLab simulations.

## Purpose

When you run a simulation manually through the interactive runner (`run.py`), the parameters you enter are automatically saved as a JSON configuration file in this directory. This allows you to:

1. **Re-run tests easily**: Load a previous configuration instead of re-entering all parameters
2. **Track test history**: See what tests you've run and when
3. **Share configurations**: Share test configs with colleagues or for reproducibility

## File Naming Convention

Configuration files are named using the pattern:
```
{BodyNames}_{Timestamp}.json
```

Examples:
- `Earth_Mars_20251007_120000.json` - Two-body grid from Earth to Mars
- `Mars_Ceres_20251007_130000.json` - Flyby at Mars targeting Ceres
- `Earth_Mars_Ceres_20251007_140000.json` - Three-body chain: Earth → Mars → Ceres

## File Format

Each configuration file is a JSON document with the following structure:

```json
{
  "simulation_type": "chain3",
  "timestamp": "20251007_120000",
  "parameters": {
    "dep_id": "399",
    "dep_body_name": "Earth",
    "flyby_id": "499",
    "flyby_body_name": "Mars",
    "arr_id": "20000001",
    "arr_body_name": "Ceres",
    "dep_window": "2035-04-01:2035-09-01",
    "dep_step": "2",
    "leg1_tof": "150:380:5",
    "leg2_tof": "180:600:10",
    "rp_bounds": "3696.2:13396.2",
    "bplane_theta": "-30:30:7",
    "max_solutions": "200"
  }
}
```

## Simulation Types

- `two_body_grid`: Two-body porkchop plot (Earth → Mars style transfers)
- `flyby`: Single gravity assist flyby computation
- `chain3`: Three-body chain with gravity assist (Earth → Mars → Ceres)

## Usage

### Loading a Configuration

When starting a simulation in the interactive runner:
1. Select the simulation type (1-4)
2. When prompted "Load from saved config? (y/n)", enter `y`
3. Select from the list of available configurations
4. The simulation will run with those saved parameters

### Viewing Configurations

Use menu option 6 "View Saved Configs" to see all saved configurations without running them.

## Notes

- Configurations are saved automatically when you run a test manually
- The most recent configurations are shown first
- Up to 20 configurations are displayed at once
- SPICE kernel files are NOT saved in configs - they use the default kernels
