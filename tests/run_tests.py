"""
Test Runner - Quick access to PyKEP test suite

Usage:
    python run_tests.py               # Run all tests
    python run_tests.py --fast        # Skip stress tests
    python run_tests.py --module core # Run specific module
    python run_tests.py --coverage    # Run with coverage report
"""

import sys
import subprocess

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "--fast":
            cmd = ["pytest", 
                   "tests/test_01_lambert_core.py",
                   "tests/test_02_flyby_physics.py", 
                   "tests/test_03_integration.py",
                   "-v"]
            
        elif arg == "--coverage":
            cmd = ["pytest",
                   "tests/test_01_lambert_core.py",
                   "tests/test_02_flyby_physics.py",
                   "tests/test_03_integration.py",
                   "tests/test_04_stress.py",
                   "--cov=lambertlab",
                   "--cov-report=html",
                   "-v"]
            
        elif arg == "--module":
            if len(sys.argv) < 3:
                print("Usage: python run_tests.py --module <core|flyby|integration|stress>")
                return
            
            module_map = {
                "core": "tests/test_01_lambert_core.py",
                "lambert": "tests/test_01_lambert_core.py",
                "flyby": "tests/test_02_flyby_physics.py",
                "physics": "tests/test_02_flyby_physics.py",
                "integration": "tests/test_03_integration.py",
                "stress": "tests/test_04_stress.py",
            }
            
            module = sys.argv[2].lower()
            if module not in module_map:
                print(f"Unknown module: {module}")
                print(f"Available: {', '.join(module_map.keys())}")
                return
            
            cmd = ["pytest", module_map[module], "-v"]
        
        else:
            print(__doc__)
            return
    else:
        # Run all tests
        cmd = ["pytest",
               "tests/test_01_lambert_core.py",
               "tests/test_02_flyby_physics.py",
               "tests/test_03_integration.py",
               "tests/test_04_stress.py",
               "-v"]
    
    print(f"Running: {' '.join(cmd)}\n")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
