#!/usr/bin/env python3
"""
Interactive LambertLab Simulation Runner

Provides an interactive interface to run LambertLab simulations.
"""

import sys
import os
import subprocess
import spiceypy as sp
from datetime import datetime
import json
import glob

# Body parameters (NAIF ID -> (radius_km, mu_km3s2, name))
BODY_PARAMS = {
    '199': (2439.7, 2.2032e4, 'Mercury'),
    '299': (6051.8, 3.2486e5, 'Venus'),
    '399': (6378.1, 3.986e5, 'Earth'),
    '499': (3396.2, 4.282837e4, 'Mars'),
    '599': (71492.0, 1.26686e8, 'Jupiter'),
    '699': (60268.0, 3.7931e7, 'Saturn'),
    '799': (25559.0, 5.794e6, 'Uranus'),
    '899': (24764.0, 6.837e6, 'Neptune'),
    '20000001': (476.2, 62.6284, 'Ceres'),  # Ceres
}

# Directory for test configurations
TEST_CONFIG_DIR = "test_configs"

def save_test_config(sim_type, params, body_names=None):
    """
    Save test configuration to JSON file.
    
    Args:
        sim_type: Type of simulation (e.g., 'two_body_grid', 'flyby', 'chain3')
        params: Dictionary of parameters
        body_names: Optional list of body names for filename
    """
    # Ensure test_configs directory exists
    os.makedirs(TEST_CONFIG_DIR, exist_ok=True)
    
    # Create filename with bodies and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if body_names:
        bodies_str = "_".join(body_names)
        filename = f"{bodies_str}_{timestamp}.json"
    else:
        filename = f"{sim_type}_{timestamp}.json"
    
    filepath = os.path.join(TEST_CONFIG_DIR, filename)
    
    # Create config object
    config = {
        "simulation_type": sim_type,
        "timestamp": timestamp,
        "parameters": params
    }
    
    # Save to JSON
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Saved config to: {filepath}")
    return filepath

def load_test_config(filepath):
    """
    Load test configuration from JSON file.
    
    Args:
        filepath: Path to config file
    
    Returns:
        dict: Configuration dictionary
    """
    with open(filepath, 'r') as f:
        config = json.load(f)
    return config

def list_saved_configs(sim_type=None):
    """
    List available saved configurations.
    
    Args:
        sim_type: Optional filter by simulation type
    
    Returns:
        list: List of config file paths
    """
    if not os.path.exists(TEST_CONFIG_DIR):
        return []
    
    pattern = os.path.join(TEST_CONFIG_DIR, "*.json")
    configs = glob.glob(pattern)
    configs.sort(reverse=True)  # Most recent first
    
    if sim_type:
        # Filter by simulation type
        filtered = []
        for config_path in configs:
            try:
                config = load_test_config(config_path)
                if config.get('simulation_type') == sim_type:
                    filtered.append(config_path)
            except:
                continue
        return filtered
    
    return configs

def select_saved_config(sim_type=None):
    """
    Interactive menu to select a saved configuration.
    
    Args:
        sim_type: Optional filter by simulation type
    
    Returns:
        dict: Selected configuration or None if cancelled
    """
    configs = list_saved_configs(sim_type)
    
    if not configs:
        print("No saved configurations found.")
        return None
    
    print("\nSaved Configurations:")
    for i, config_path in enumerate(configs[:20], 1):  # Show max 20
        filename = os.path.basename(config_path)
        # Try to load and show details
        try:
            config = load_test_config(config_path)
            sim_type_str = config.get('simulation_type', 'unknown')
            timestamp = config.get('timestamp', '')
            print(f"{i}. {filename} ({sim_type_str})")
        except:
            print(f"{i}. {filename}")
    
    print(f"{len(configs[:20]) + 1}. Cancel")
    
    while True:
        try:
            choice = input(f"\nSelect a config (1-{len(configs[:20]) + 1}): ").strip()
            
            if choice == str(len(configs[:20]) + 1):
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(configs[:20]):
                selected = configs[choice_idx]
                config = load_test_config(selected)
                print(f"✓ Loaded: {os.path.basename(selected)}")
                return config
            else:
                print(f"Invalid choice. Please select 1-{len(configs[:20]) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

def run_command(cmd_args):
    """Run a CLI command."""
    # Set PYTHONPATH to ensure src/lambertlab is found first
    repo_root = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(repo_root, 'src')
    
    # Create a new environment with PYTHONPATH pointing to src
    env = os.environ.copy()
    pythonpath = env.get('PYTHONPATH', '')
    # Insert src at the beginning to ensure it's checked first
    env['PYTHONPATH'] = f"{src_path}{os.pathsep}{pythonpath}" if pythonpath else src_path
    # Prevent bytecode generation which can cause import warnings
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # Force matplotlib to use Agg backend (non-interactive) before Python starts
    env['MPLBACKEND'] = 'Agg'

    # Ensure we use the lambertlab environment Python, not base
    python_exe = sys.executable
    # If running from base, switch to lambertlab environment
    if 'envs\\lambertlab' not in python_exe and 'envs/lambertlab' not in python_exe:
        # Try to find lambertlab environment Python
        miniconda_root = os.path.dirname(os.path.dirname(sys.executable)) if 'miniconda3' in sys.executable else None
        if miniconda_root:
            lambertlab_python = os.path.join(miniconda_root, 'envs', 'lambertlab', 'python.exe')
            if os.path.exists(lambertlab_python):
                python_exe = lambertlab_python
                print(f"⚠️  Switched from base to lambertlab environment")
    
    cmd = [python_exe, '-W', 'ignore', '-m', 'lambertlab.cli.main'] + cmd_args

    print(f"Running command: {' '.join(cmd)}")
    print(f"Using Python: {python_exe}")
    print(f"MPLBACKEND env var: {env.get('MPLBACKEND', 'NOT SET')}")
    print(f"Current working directory: {os.getcwd()}")
    
    try:
        result = subprocess.run(cmd, env=env, cwd=os.getcwd())
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1

def load_default_kernels():
    """Load default SPICE kernels for ephemeris checks."""
    kernels = [
        "data/kernels/naif0012.tls",
        "data/kernels/de440.bsp",
        "data/kernels/gm_de440.tpc",
        "data/kernels/20000001.bsp",
        "data/kernels/mar097.bsp",
        "data/kernels/pck00011.tpc"
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

def get_body_params(naif_id_str):
    """
    Get body parameters (radius, mu, name).
    
    Args:
        naif_id_str: NAIF ID as string
    
    Returns:
        tuple: (radius_km, mu_km3s2, name) or None if not found
    """
    if naif_id_str in BODY_PARAMS:
        return BODY_PARAMS[naif_id_str]
    else:
        # Try to get from SPICE using bodvrd (if available in kernels)
        try:
            radii = sp.bodvrd(naif_id_str, 'RADII', 3)[1]
            radius = radii[0]  # Use equatorial radius
            try:
                name = sp.bodc2n(int(naif_id_str))
            except:
                name = f"Body {naif_id_str}"
            # Try to get GM from SPICE
            try:
                gm = sp.bodvrd(naif_id_str, 'GM', 1)[1][0]
                return (radius, gm, name)
            except:
                # Return None for mu if not available
                return (radius, None, name)
        except:
            return None

def get_body_input(prompt, default_id=None, default_name=None, date_str=None):
    """
    Get and validate body input from user.
    
    Args:
        prompt: Prompt text for user
        default_id: Default NAIF ID
        default_name: Default body name for display
        date_str: Date to check ephemeris coverage
    
    Returns:
        str: Valid NAIF ID as string
    """
    default_text = f"{default_id} ({default_name})" if default_id and default_name else ""
    
    while True:
        user_input = input(f"{prompt} [{default_text}]: ").strip()
        
        if not user_input and default_id:
            # Use default
            naif_id, body_name, is_valid, error = validate_body(default_id, date_str)
            if is_valid:
                print(f"Using: {body_name} (NAIF ID: {naif_id})")
                return str(naif_id)
            else:
                print(f"Warning: {error}")
                print("Please enter a different body.")
                continue
        
        if not user_input:
            print("Body input is required.")
            continue
        
        # Validate the input
        naif_id, body_name, is_valid, error = validate_body(user_input, date_str)
        
        if is_valid:
            print(f"✓ Valid: {body_name} (NAIF ID: {naif_id})")
            return str(naif_id)
        else:
            print(f"✗ {error}")
            retry = input("Try another body? (y/n): ").strip().lower()
            if retry != 'y':
                return None

def get_two_body_grid_params():
    """Get parameters for two-body grid simulation."""
    print("\n=== Two Body Grid Simulation (Porkchop Plot) ===")
    print("Compute transfer trajectories between two bodies over a date range.")
    print()
    
    # Check for saved configs
    use_saved = input("Load from saved config? (y/n) [n]: ").strip().lower()
    if use_saved == 'y':
        config = select_saved_config('two_body_grid')
        if config:
            params = config['parameters']
            # Build command from saved params
            kernels = load_default_kernels()
            sp.kclear()
            
            cmd = ["transfer-grid"]
            for k in kernels:
                cmd.extend(["--kernels", k])
            cmd.extend([
                "--dep-start", params['dep_start'],
                "--dep-end", params['dep_end'],
                "--dep-step", params['dep_step'],
                "--tof-min", params['tof_min'],
                "--tof-max", params['tof_max'],
                "--tof-step", params['tof_step'],
                "--dep-body", params['dep_id'],
                "--arr-body", params['arr_id'],
                "--save"
            ])
            print(f"\n✓ Loaded config: {params['dep_body_name']} → {params['arr_body_name']}")
            return cmd
        else:
            # No config selected or none available, fall through to manual entry
            print("Continuing with manual parameter entry...\n")
    
    # Load kernels for validation
    kernels = load_default_kernels()
    
    # Get dates first so we can validate ephemeris
    dep_start = input("Departure start date (YYYY-MM-DD) [2026-06-24]: ").strip() or "2026-06-24"
    dep_end = input("Departure end date (YYYY-MM-DD) [2026-06-26]: ").strip() or "2026-06-26"
    
    # Get bodies with ephemeris validation
    print("\nDeparture body (e.g., 399 for Earth, 'EARTH', 499 for Mars):")
    dep_id = get_body_input("Enter NAIF ID or name", 399, "Earth", dep_start)
    if not dep_id:
        print("Cancelled.")
        return None
    
    # Get body name for saving
    dep_params = get_body_params(dep_id)
    dep_body_name = dep_params[2] if dep_params else f"Body{dep_id}"
    
    print("\nArrival body (e.g., 499 for Mars, 'MARS', 20000001 for Ceres):")
    arr_id = get_body_input("Enter NAIF ID or name", 499, "Mars", dep_end)
    if not arr_id:
        print("Cancelled.")
        return None
    
    # Get body name for saving
    arr_params = get_body_params(arr_id)
    arr_body_name = arr_params[2] if arr_params else f"Body{arr_id}"
    
    # Get other parameters
    dep_step = input("Departure step days [1]: ").strip() or "1"
    tof_min = input("Min TOF days [190]: ").strip() or "190"
    tof_max = input("Max TOF days [200]: ").strip() or "200"
    tof_step = input("TOF step days [1]: ").strip() or "1"
    
    # Save configuration
    params = {
        'dep_start': dep_start,
        'dep_end': dep_end,
        'dep_step': dep_step,
        'tof_min': tof_min,
        'tof_max': tof_max,
        'tof_step': tof_step,
        'dep_id': dep_id,
        'arr_id': arr_id,
        'dep_body_name': dep_body_name,
        'arr_body_name': arr_body_name
    }
    save_test_config('two_body_grid', params, [dep_body_name, arr_body_name])
    
    # Clean up
    sp.kclear()

    cmd = ["transfer-grid"]
    for k in kernels:
        cmd.extend(["--kernels", k])
    cmd.extend([
        "--dep-start", dep_start,
        "--dep-end", dep_end,
        "--dep-step", dep_step,
        "--tof-min", tof_min,
        "--tof-max", tof_max,
        "--tof-step", tof_step,
        "--dep-body", dep_id,
        "--arr-body", arr_id,
        "--save"
    ])

    return cmd

def get_flyby_params():
    """Get parameters for flyby computation."""
    print("\n=== Compute Flyby ===")
    print("Compute a gravity assist flyby maneuver around a planet.")
    print()
    
    # Check for saved configs
    use_saved = input("Load from saved config? (y/n) [n]: ").strip().lower()
    if use_saved == 'y':
        config = select_saved_config('flyby')
        if config:
            params = config['parameters']
            # Build command from saved params
            kernels = load_default_kernels()
            sp.kclear()
            
            cmd = ["flyby"]
            for k in kernels:
                cmd.extend(["--kernels", k])
            cmd.extend([
                "--epoch", params['epoch'],
                "--planet-id", params['planet_id'],
                "--r-body", params['r_body'],
                "--alt-min", params['alt_min'],
                "--target-id", params['target_id'],
                "--vinf-in"
            ] + params['vinf_in'].split())
            
            if params.get('b_hat'):
                cmd.extend(["--b-hat"] + params['b_hat'].split())
            
            cmd.append("--save")
            print(f"\n✓ Loaded config: {params['planet_name']} flyby → {params['target_name']}")
            return cmd
        else:
            # No config selected or none available, fall through to manual entry
            print("Continuing with manual parameter entry...\n")
    
    # Load kernels for validation
    kernels = load_default_kernels()
    
    # Get epoch
    epoch = input("Flyby epoch (YYYY-MM-DD) [2026-12-25]: ").strip() or "2026-12-25"
    
    # Get flyby body
    print("\nFlyby body (planet for gravity assist):")
    print("Common: 499 (Mars), 299 (Venus), 599 (Jupiter)")
    planet_id = get_body_input("Enter NAIF ID or name", 499, "Mars", epoch)
    if not planet_id:
        print("Cancelled.")
        return None
    
    # Get body parameters
    params_tuple = get_body_params(planet_id)
    if not params_tuple:
        print(f"Warning: Body parameters not found for ID {planet_id}")
        print("Please provide them manually:")
        try:
            r_body = float(input("Body radius (km): "))
            alt_min = float(input("Minimum altitude (km) [300]: ").strip() or "300")
        except ValueError:
            print("Invalid input. Cancelled.")
            return None
        body_name = f"Body{planet_id}"
    else:
        r_body, mu, body_name = params_tuple
        print(f"Body: {body_name}, Radius: {r_body:.1f} km")
        alt_min_default = 300.0 if r_body > 1000 else 100.0
        alt_min = input(f"Minimum altitude (km) [{alt_min_default}]: ").strip()
        alt_min = float(alt_min) if alt_min else alt_min_default
    
    # Get incoming v-infinity vector
    print("\nIncoming v-infinity vector (km/s):")
    print("This is the spacecraft's velocity relative to the planet before flyby.")
    print("Example: '5.0 0.0 0.0' for 5 km/s in +X direction")
    
    vinf_input = input("Enter 3 components (x y z) [5.0 0.0 0.0]: ").strip() or "5.0 0.0 0.0"
    try:
        vinf_parts = vinf_input.split()
        if len(vinf_parts) != 3:
            print("Error: Need exactly 3 components")
            return None
        vinf_in = [float(x) for x in vinf_parts]
    except ValueError:
        print("Error: Invalid number format")
        return None
    
    # Get target body (where we're going after the flyby)
    print("\nTarget body (destination after flyby):")
    print("Common: 20000001 (Ceres), 599 (Jupiter), 699 (Saturn)")
    # Use a later date for target arrival window check
    target_window_start = epoch  # Will add 200 days in compute_flyby
    target_id = get_body_input("Enter target NAIF ID or name", 20000001, "Ceres", target_window_start)
    if not target_id:
        print("Cancelled.")
        return None
    
    # Get target body name
    target_params = get_body_params(target_id)
    target_name = target_params[2] if target_params else f"Body{target_id}"
    
    # Optional: b-plane targeting vector
    print("\nB-plane targeting (optional):")
    print("Leave blank for automatic optimization")
    b_hat_input = input("B-plane unit vector (x y z) [auto]: ").strip()
    
    b_hat_args = []
    b_hat_str = None
    if b_hat_input and b_hat_input.lower() != 'auto':
        try:
            b_hat_parts = b_hat_input.split()
            if len(b_hat_parts) != 3:
                print("Warning: B-plane vector needs 3 components, using auto")
            else:
                b_hat = [float(x) for x in b_hat_parts]
                b_hat_args = ["--b-hat"] + [str(x) for x in b_hat]
                b_hat_str = b_hat_input
        except ValueError:
            print("Warning: Invalid b-plane vector format, using auto")
    
    # Save configuration
    save_params = {
        'epoch': epoch,
        'planet_id': planet_id,
        'planet_name': body_name,
        'r_body': str(r_body),
        'alt_min': str(alt_min),
        'target_id': target_id,
        'target_name': target_name,
        'vinf_in': vinf_input,
    }
    if b_hat_str:
        save_params['b_hat'] = b_hat_str
    save_test_config('flyby', save_params, [body_name, target_name])
    
    # Clean up
    sp.kclear()
    
    cmd = ["flyby"]
    for k in kernels:
        cmd.extend(["--kernels", k])
    cmd.extend([
        "--epoch", epoch,
        "--planet-id", planet_id,
        "--r-body", str(r_body),
        "--alt-min", str(alt_min),
        "--target-id", target_id,
        "--vinf-in"
    ] + [str(x) for x in vinf_in])
    
    if b_hat_args:
        cmd.extend(b_hat_args)
    
    cmd.append("--save")
    
    return cmd

def get_transfer_screen_params():
    """Get parameters for transfer screening (v∞ requirements for fixed departure)."""
    print("\n=== Two Body Screening ===")
    print("Screen v∞ requirements from a fixed departure date to an arrival body.")
    print("Useful for evaluating continuation legs after a planetary encounter.")
    print()
    
    # Check for saved configs
    use_saved = input("Load from saved config? (y/n) [n]: ").strip().lower()
    if use_saved == 'y':
        config = select_saved_config('transfer_screen')
        if config:
            params = config['parameters']
            # Build command from saved params
            kernels = load_default_kernels()
            sp.kclear()
            
            cmd = ["transfer-screen"]
            for k in kernels:
                cmd.extend(["--kernels", k])
            cmd.extend([
                "--dep-epoch", params['dep_epoch'],
                "--arr-window", params['arr_window'],
                "--tof-min", params['tof_min'],
                "--tof-max", params['tof_max'],
                "--tof-step", params['tof_step'],
                "--dep-body", params['dep_id'],
                "--arr-body", params['arr_id']
            ])
            
            if params.get('c3_cap'):
                cmd.extend(["--c3-cap", params['c3_cap']])
            
            cmd.append("--save")
            print(f"\n✓ Loaded config: {params['dep_body_name']} (departure) → {params['arr_body_name']} (arrival)")
            return cmd
        else:
            # No config selected or none available, fall through to manual entry
            print("Continuing with manual parameter entry...\n")
    
    # Load kernels for validation
    kernels = load_default_kernels()
    
    # Get fixed departure date
    dep_epoch = input("Fixed departure date (YYYY-MM-DD) [2025-06-01]: ").strip() or "2025-06-01"
    
    # Get departure body with ephemeris validation
    print("\nDeparture body (where you're leaving from):")
    print("Common: 499 (Mars), 299 (Venus), 399 (Earth)")
    dep_id = get_body_input("Enter NAIF ID or name", 499, "Mars", dep_epoch)
    if not dep_id:
        print("Cancelled.")
        return None
    
    # Get body name for saving
    dep_params = get_body_params(dep_id)
    dep_body_name = dep_params[2] if dep_params else f"Body{dep_id}"
    
    # Get arrival window
    print("\nArrival time window:")
    print("Specify the range of acceptable arrival dates.")
    arr_start = input("Arrival start date (YYYY-MM-DD) [2025-10-01]: ").strip() or "2025-10-01"
    arr_end = input("Arrival end date (YYYY-MM-DD) [2026-02-01]: ").strip() or "2026-02-01"
    arr_window = f"{arr_start}:{arr_end}"
    
    # Get arrival body with ephemeris validation
    print("\nArrival body (destination):")
    print("Common: 20000001 (Ceres), 599 (Jupiter), 699 (Saturn)")
    arr_id = get_body_input("Enter NAIF ID or name", 20000001, "Ceres", arr_start)
    if not arr_id:
        print("Cancelled.")
        return None
    
    # Get body name for saving
    arr_params = get_body_params(arr_id)
    arr_body_name = arr_params[2] if arr_params else f"Body{arr_id}"
    
    # Get TOF parameters
    print("\nTime-of-flight (TOF) search range:")
    tof_min = input("Minimum TOF (days) [150]: ").strip() or "150"
    tof_max = input("Maximum TOF (days) [400]: ").strip() or "400"
    tof_step = input("TOF step (days) [5]: ").strip() or "5"
    
    # Get optional C3 cap
    c3_cap_input = input("\nOptional: C3 cap (km²/s²) to filter high-energy trajectories [none]: ").strip()
    c3_cap = c3_cap_input if c3_cap_input else None
    
    # Save configuration
    params = {
        'dep_epoch': dep_epoch,
        'arr_window': arr_window,
        'arr_start': arr_start,
        'arr_end': arr_end,
        'tof_min': tof_min,
        'tof_max': tof_max,
        'tof_step': tof_step,
        'dep_id': dep_id,
        'arr_id': arr_id,
        'dep_body_name': dep_body_name,
        'arr_body_name': arr_body_name,
        'c3_cap': c3_cap
    }
    save_test_config('transfer_screen', params, [dep_body_name, arr_body_name])
    
    # Clean up
    sp.kclear()
    
    cmd = ["transfer-screen"]
    for k in kernels:
        cmd.extend(["--kernels", k])
    cmd.extend([
        "--dep-epoch", dep_epoch,
        "--arr-window", arr_window,
        "--tof-min", tof_min,
        "--tof-max", tof_max,
        "--tof-step", tof_step,
        "--dep-body", dep_id,
        "--arr-body", arr_id
    ])
    
    if c3_cap:
        cmd.extend(["--c3-cap", c3_cap])
    
    cmd.append("--save")
    
    return cmd

def get_three_body_chain_params():
    """Get parameters for three-body chain (Origin → Flyby → Destination)."""
    print("\n=== Three Body Chain (Gravity Assist) ===")
    print("Plan a trajectory with a gravity assist flyby.")
    print("Example: Earth → Mars (flyby) → Ceres")
    print()
    
    # Check for saved configs
    use_saved = input("Load from saved config? (y/n) [n]: ").strip().lower()
    if use_saved == 'y':
        config = select_saved_config('chain3')
        if config:
            params = config['parameters']
            # Build command from saved params
            kernels = load_default_kernels()
            sp.kclear()
            
            cmd = ["chain3"]
            for k in kernels:
                cmd.extend(["--kernels", k])
            cmd.extend([
                "--dep-body", params['dep_id'],
                "--flyby-body", params['flyby_id'],
                "--arr-body", params['arr_id'],
                "--dep-window", params['dep_window'],
                "--dep-step", params['dep_step'],
                "--leg1-tof", params['leg1_tof'],
                "--leg2-tof", params['leg2_tof'],
                "--rp-bounds", params['rp_bounds'],
                f"--bplane-theta={params['bplane_theta']}",  # Use = syntax to avoid argparse confusion with negative numbers
                "--max-solutions", params['max_solutions'],
                "--dv-tol", params.get('dv_tol', '500'),  # Default to 500 if not in old configs
                "--save"
            ])
            print(f"\n✓ Loaded config: {params['dep_body_name']} → {params['flyby_body_name']} → {params['arr_body_name']}")
            return cmd
        else:
            # No config selected or none available, fall through to manual entry
            print("Continuing with manual parameter entry...\n")
    
    # Load kernels for validation
    kernels = load_default_kernels()
    
    # Get departure body
    print("Departure body (origin):")
    print("Common: 399 (Earth), 299 (Venus)")
    dep_start = input("Departure window start (YYYY-MM-DD) [2035-04-01]: ").strip() or "2035-04-01"
    dep_id = get_body_input("Enter departure NAIF ID or name", 399, "Earth", dep_start)
    if not dep_id:
        print("Cancelled.")
        return None
    
    # Get departure body name
    dep_params = get_body_params(dep_id)
    dep_body_name = dep_params[2] if dep_params else f"Body{dep_id}"
    
    # Get flyby body
    print("\nFlyby body (for gravity assist):")
    print("Common: 499 (Mars), 299 (Venus), 599 (Jupiter)")
    flyby_id = get_body_input("Enter flyby NAIF ID or name", 499, "Mars", dep_start)
    if not flyby_id:
        print("Cancelled.")
        return None
    
    # Get flyby body parameters
    flyby_params = get_body_params(flyby_id)
    if not flyby_params:
        print(f"Warning: Body parameters not found for ID {flyby_id}")
        try:
            r_flyby = float(input("Flyby body radius (km): "))
            alt_min = float(input("Minimum altitude (km) [300]: ").strip() or "300")
        except ValueError:
            print("Invalid input. Cancelled.")
            return None
        flyby_body_name = f"Body{flyby_id}"
    else:
        r_flyby, mu_flyby, flyby_body_name = flyby_params
        print(f"Flyby body: {flyby_body_name}, Radius: {r_flyby:.1f} km")
        alt_min_default = 300.0 if r_flyby > 1000 else 100.0
        alt_min = input(f"Minimum altitude (km) [{alt_min_default}]: ").strip()
        alt_min = float(alt_min) if alt_min else alt_min_default
    
    # Get arrival body
    print("\nArrival body (final destination):")
    print("Common: 20000001 (Ceres), 599 (Jupiter), 699 (Saturn)")
    arr_id = get_body_input("Enter arrival NAIF ID or name", 20000001, "Ceres", dep_start)
    if not arr_id:
        print("Cancelled.")
        return None
    
    # Get arrival body name
    arr_params = get_body_params(arr_id)
    arr_body_name = arr_params[2] if arr_params else f"Body{arr_id}"
    
    # Get departure window
    print("\nDeparture window:")
    dep_end = input(f"Departure window end (YYYY-MM-DD) [2035-09-01]: ").strip() or "2035-09-01"
    dep_step = input("Departure step days [2]: ").strip() or "2"
    
    # Get Leg 1 (dep → flyby) parameters
    print("\nLeg 1 (Departure → Flyby) time of flight:")
    leg1_tof_min = input("Min TOF days [150]: ").strip() or "150"
    leg1_tof_max = input("Max TOF days [380]: ").strip() or "380"
    leg1_tof_step = input("TOF step days [5]: ").strip() or "5"
    
    # Get Leg 2 (flyby → arrival) parameters
    print("\nLeg 2 (Flyby → Arrival) time of flight:")
    leg2_tof_min = input("Min TOF days [180]: ").strip() or "180"
    leg2_tof_max = input("Max TOF days [600]: ").strip() or "600"
    leg2_tof_step = input("TOF step days [10]: ").strip() or "10"
    
    # Get B-plane rotation range
    print("\nB-plane targeting (advanced):")
    print("Rotation angle range to search for optimal flyby orientation")
    btheta_min = input("Min B-plane theta (deg) [-30]: ").strip() or "-30"
    btheta_max = input("Max B-plane theta (deg) [30]: ").strip() or "30"
    btheta_n = input("Number of theta samples [7]: ").strip() or "7"
    
    # Optional parameters
    max_solutions = input("\nMax solutions to keep [200]: ").strip() or "200"
    print("\nDeltaV tolerance:")
    print("Maximum velocity mismatch (m/s) between flyby exit and Leg 2 entry")
    print("Higher values allow more flyby geometries but may be less accurate")
    dv_tol = input("DV tolerance (m/s) [500]: ").strip() or "500"
    
    # Format parameter strings
    dep_window = f"{dep_start}:{dep_end}"
    leg1_tof = f"{leg1_tof_min}:{leg1_tof_max}:{leg1_tof_step}"
    leg2_tof = f"{leg2_tof_min}:{leg2_tof_max}:{leg2_tof_step}"
    rp_bounds = f"{float(r_flyby) + float(alt_min)}:{float(r_flyby) + 10000.0}"
    bplane_theta = f"{btheta_min}:{btheta_max}:{btheta_n}"
    
    # Save configuration
    save_params = {
        'dep_id': dep_id,
        'dep_body_name': dep_body_name,
        'flyby_id': flyby_id,
        'flyby_body_name': flyby_body_name,
        'arr_id': arr_id,
        'arr_body_name': arr_body_name,
        'dep_window': dep_window,
        'dep_step': dep_step,
        'leg1_tof': leg1_tof,
        'leg2_tof': leg2_tof,
        'rp_bounds': rp_bounds,
        'bplane_theta': bplane_theta,
        'max_solutions': max_solutions,
        'dv_tol': dv_tol,
        # Store individual values for readability
        'dep_start': dep_start,
        'dep_end': dep_end,
        'r_flyby': str(r_flyby),
        'alt_min': str(alt_min)
    }
    save_test_config('chain3', save_params, [dep_body_name, flyby_body_name, arr_body_name])
    
    # Clean up
    sp.kclear()
    
    cmd = ["chain3"]
    for k in kernels:
        cmd.extend(["--kernels", k])
    
    cmd.extend([
        "--dep-body", dep_id,
        "--flyby-body", flyby_id,
        "--arr-body", arr_id,
        "--dep-window", dep_window,
        "--dep-step", dep_step,
        "--leg1-tof", leg1_tof,
        "--leg2-tof", leg2_tof,
        "--rp-bounds", rp_bounds,
        f"--bplane-theta={bplane_theta}",  # Use = syntax to avoid argparse confusion with negative numbers
        "--max-solutions", max_solutions,
        "--dv-tol", dv_tol,
        "--save"
    ])
    
    return cmd

def run_tests_menu():
    """Interactive menu to run test scripts from the tests/ directory."""
    # Get all test_*.py files in tests/ directory
    test_files = glob.glob("tests/test_*.py")
    test_files.sort()  # Sort alphabetically
    
    if not test_files:
        print("No test files found in tests/ directory.")
        return
    
    print("\nAvailable Tests:")
    for i, test_file in enumerate(test_files, 1):
        # Extract just the filename without path
        filename = os.path.basename(test_file)
        print(f"{i}. {filename}")
    
    print(f"{len(test_files) + 1}. Back to main menu")
    
    while True:
        try:
            choice = input(f"\nSelect a test to run (1-{len(test_files) + 1}): ").strip()
            
            if choice == str(len(test_files) + 1):
                return
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(test_files):
                selected_test = test_files[choice_idx]
                filename = os.path.basename(selected_test)
                
                print(f"\nRunning {filename}...")
                print("-" * 50)
                
                # Run the test script
                python_exe = sys.executable
                cmd = [python_exe, selected_test]
                
                try:
                    result = subprocess.run(cmd, cwd=os.getcwd())
                    print("-" * 50)
                    if result.returncode == 0:
                        print(f"✓ {filename} completed successfully")
                    else:
                        print(f"✗ {filename} failed with exit code {result.returncode}")
                except KeyboardInterrupt:
                    print(f"\nInterrupted {filename}")
                except Exception as e:
                    print(f"Error running {filename}: {e}")
                
                input("\nPress Enter to continue...")
                return
            else:
                print(f"Invalid choice. Please select 1-{len(test_files) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def view_saved_configs_menu():
    """Interactive menu to view saved test configurations."""
    configs = list_saved_configs()
    
    if not configs:
        print("\nNo saved configurations found.")
        input("Press Enter to continue...")
        return
    
    print("\n=== Saved Test Configurations ===")
    print(f"Found {len(configs)} saved configuration(s)\n")
    
    for i, config_path in enumerate(configs[:20], 1):  # Show max 20
        filename = os.path.basename(config_path)
        try:
            config = load_test_config(config_path)
            sim_type = config.get('simulation_type', 'unknown')
            params = config.get('parameters', {})
            
            # Get body names if available
            if sim_type == 'two_body_grid':
                bodies = f"{params.get('dep_body_name', '?')} → {params.get('arr_body_name', '?')}"
            elif sim_type == 'flyby':
                bodies = f"{params.get('planet_name', '?')} flyby → {params.get('target_name', '?')}"
            elif sim_type == 'chain3':
                bodies = f"{params.get('dep_body_name', '?')} → {params.get('flyby_body_name', '?')} → {params.get('arr_body_name', '?')}"
            else:
                bodies = "N/A"
            
            print(f"{i}. {filename}")
            print(f"   Type: {sim_type}, Bodies: {bodies}")
            
        except Exception as e:
            print(f"{i}. {filename} (error loading: {e})")
    
    input("\nPress Enter to continue...")

def main():
    print("Welcome to LambertLab Interactive Simulation Runner!")
    print("=" * 50)

    while True:
        print("\nAvailable Simulations:")
        print("1. Two Body Grid (Porkchop Plot)")
        print("2. Compute Flyby")
        print("3. Two Body Screening")
        print("4. Three Body Chain (Gravity Assist)")
        print("5. Run Tests")
        print("6. View Saved Configs")
        print("7. Exit")

        choice = input("\nSelect an option (1-7): ").strip()

        if choice == "1":
            cmd = get_two_body_grid_params()
            if cmd:
                print(f"\nRunning simulation...")
                print("This will generate data files and plots in the 'artifacts' directory.")
                run_command(cmd)

        elif choice == "2":
            cmd = get_flyby_params()
            if cmd:
                print(f"\nRunning flyby computation...")
                print("This will compute the flyby trajectory and save results to 'artifacts/flyby.json'")
                run_command(cmd)

        elif choice == "3":
            cmd = get_transfer_screen_params()
            if cmd:
                print(f"\nRunning transfer screening...")
                print("This will evaluate v∞ requirements across the TOF/arrival window.")
                print("Results will be saved to 'artifacts/transfer_grid.csv'")
                run_command(cmd)

        elif choice == "4":
            cmd = get_three_body_chain_params()
            if cmd:
                print(f"\nRunning three-body chain computation...")
                print("This will search for optimal gravity assist trajectories.")
                print("Results will be saved with porkchop plots and solution tables.")
                run_command(cmd)

        elif choice == "5":
            run_tests_menu()

        elif choice == "6":
            view_saved_configs_menu()

        elif choice == "7":
            print("\nGoodbye!")
            break

        else:
            print("Invalid choice. Please select 1-7.")

        input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()