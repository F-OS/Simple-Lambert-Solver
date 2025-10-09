# Interactive Runner Updates - Summary

## Changes Made

### 1. Updated Menu Options
The menu options have been renamed to be more generic and descriptive:

**Before:**
1. Earth-Mars Grid (Porkchop Plot)
2. Mars Flyby
3. Mars-Ceres Screening
4. Earth-Mars-Ceres Chain

**After:**
1. Two Body Grid (Porkchop Plot)
2. Compute Flyby
3. Two Body Screening
4. Three Body Chain (Gravity Assist)

### 2. Added Flexible Body Input
Users can now enter bodies using either:
- **NAIF IDs**: `399`, `499`, `20000001`, etc.
- **Body Names**: `EARTH`, `MARS`, `VENUS`, etc.

### 3. Added Ephemeris Validation
Before running a simulation, the tool now:
- Validates that the body exists in SPICE
- Checks if ephemeris data is available for the specified date
- Provides clear error messages if validation fails

### 4. New Functions Added

#### `load_default_kernels()`
Loads the standard SPICE kernels needed for validation.

#### `validate_body(body_input, date_str=None)`
Validates a body and checks ephemeris availability:
- Accepts NAIF ID or name
- Converts name to ID using `bodn2c()`
- Checks ephemeris coverage at specified date
- Returns: `(naif_id, body_name, is_valid, error_message)`

#### `get_body_input(prompt, default_id, default_name, date_str)`
Interactive function to get and validate body input from user:
- Displays helpful prompts
- Shows validation status (✓ or ✗)
- Allows retry on validation failure
- Returns validated NAIF ID as string

#### `get_two_body_grid_params()` (renamed from `get_em_grid_params()`)
Updated to support any two-body combination:
- Prompts for departure and arrival bodies
- Validates ephemeris availability
- Passes `--dep-id` and `--arr-id` to CLI

### 5. Enhanced User Experience

**Visual Feedback:**
```
Departure body (e.g., 399 for Earth, 'EARTH', 499 for Mars):
Enter NAIF ID or name [399 (Earth)]: MARS
✓ Valid: MARS (NAIF ID: 499)
```

**Error Handling:**
```
Enter NAIF ID or name [399 (Earth)]: 999999
✗ Ephemeris not available for Body 999999 (ID: 999999) at 2026-06-24
Error: SPICE(SPKINSUFFDATA) -- Insufficient ephemeris data...
Try another body? (y/n):
```

## Example Usage

### Earth to Mars (Traditional)
```
Departure body: 399
Arrival body: 499
```

### Earth to Ceres
```
Departure body: EARTH
Arrival body: 20000001
```

### Venus to Mars
```
Departure body: VENUS
Arrival body: MARS
```

## Technical Details

### Dependencies Added
- `import spiceypy as sp` - For body validation
- `from datetime import datetime` - For date handling

### CLI Integration
The tool now passes custom body IDs to the CLI:
```python
cmd.extend([
    "--dep-id", dep_id,
    "--arr-id", arr_id,
])
```

### Kernel Management
- Kernels are loaded temporarily for validation
- `sp.kclear()` is called after validation to clean up
- Default kernels remain unchanged

## Testing

A test script (`test_interactive.py`) was created to validate:
- ✓ Numeric IDs (399, 499)
- ✓ Body names (EARTH, MARS, VENUS)
- ✓ Asteroid IDs (20000001)
- ✓ Invalid bodies (proper error handling)
- ✓ Bodies without ephemeris data

## Documentation

Two new files were created:
1. **INTERACTIVE_GUIDE.md** - User guide for body input
2. **CHANGES_SUMMARY.md** - This technical summary

## Backward Compatibility

The changes are **fully backward compatible**:
- Default values still use Earth (399) and Mars (499)
- Existing CLI commands unchanged
- Kernel loading unchanged
