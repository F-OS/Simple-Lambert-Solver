#!/usr/bin/env python3
"""
Quick test of the body validation functionality
"""
import sys
import os

# Add src to path
sys.path.insert(0, '../src')

# Import the validation function from run.py
import spiceypy as sp

def load_default_kernels():
    """Load default SPICE kernels for ephemeris checks."""
    kernels = [
        "../data/kernels/naif0012.tls",
        "../data/kernels/de440.bsp",
        "../data/kernels/gm_de440.tpc",
        "../data/kernels/20000001.bsp",
        "../data/kernels/mar097.bsp",
        "../data/kernels/pck00011.tpc"
    ]
    
    # Clear any existing kernels
    sp.kclear()
    
    # Load kernels
    for kernel in kernels:
        if os.path.exists(kernel):
            try:
                sp.furnsh(kernel)
            except Exception as e:
                print(f"Warning: Could not load kernel {kernel}: {e}")
    
    return kernels

def validate_body(body_input, date_str=None):
    """
    Validate that a body exists and has ephemeris data.
    
    Args:
        body_input: NAIF ID (int/str) or body name (str)
        date_str: Optional date string to check ephemeris coverage (YYYY-MM-DD)
    
    Returns:
        tuple: (naif_id, body_name, is_valid, error_message)
    """
    try:
        # Try to convert to integer first (NAIF ID)
        try:
            naif_id = int(body_input)
            body_str = str(naif_id)
        except ValueError:
            # It's a name, convert to NAIF ID
            body_str = str(body_input).upper()
            try:
                naif_id = sp.bodn2c(body_str)
            except:
                return None, body_str, False, f"Unknown body name: {body_input}"
        
        # Try to get body name if we have ID
        try:
            body_name = sp.bodc2n(naif_id)
        except:
            body_name = f"Body {naif_id}"
        
        # Check if ephemeris is available
        if date_str:
            try:
                et = sp.str2et(date_str)
                state, _ = sp.spkezr(body_str, et, "J2000", "NONE", "SUN")
                return naif_id, body_name, True, None
            except Exception as e:
                error_msg = f"Ephemeris not available for {body_name} (ID: {naif_id}) at {date_str}\n"
                error_msg += f"Error: {str(e)}"
                return naif_id, body_name, False, error_msg
        else:
            # Just check if body is known
            return naif_id, body_name, True, None
            
    except Exception as e:
        return None, str(body_input), False, f"Error validating body: {str(e)}"

# Test cases
print("Testing Body Validation")
print("=" * 60)

load_default_kernels()

test_cases = [
    ("Earth by ID", "399", "2026-06-24"),
    ("Earth by name", "EARTH", "2026-06-24"),
    ("Mars by ID", "499", "2026-06-24"),
    ("Mars by name", "MARS", "2026-06-24"),
    ("Ceres by ID", "20000001", "2026-06-24"),
    ("Mercury by ID", "1", "2026-06-24"),
    ("Venus by name", "VENUS", "2026-06-24"),
    ("Invalid body", "999999", "2026-06-24"),
    ("Invalid name", "PLUTO", "2026-06-24"),
]

for desc, body, date in test_cases:
    naif_id, body_name, is_valid, error = validate_body(body, date)
    if is_valid:
        print(f"✓ {desc:20} -> {body_name:20} (ID: {naif_id})")
    else:
        print(f"✗ {desc:20} -> FAILED")
        if error:
            print(f"  {error[:60]}")

sp.kclear()
print("\nTest complete!")
