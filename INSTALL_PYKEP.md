# PyKEP Migration - Step-by-Step Guide

## Step 1: Install Miniforge (Conda Package Manager)

### Why Miniforge?
- Lightweight conda distribution
- Uses conda-forge by default (where PyKEP lives)
- Works alongside your existing Python installation
- Free and open source

### Download & Install

1. **Download Miniforge:**
   - Go to: https://github.com/conda-forge/miniforge/releases/latest
   - Download: `Miniforge3-Windows-x86_64.exe`
   - Or direct link: https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe

2. **Run the Installer:**
   - Double-click the downloaded .exe
   - Click "Next"
   - **IMPORTANT:** Choose "Just Me" (recommended)
   - Accept default installation path (usually `C:\Users\<username>\miniforge3`)
   - **IMPORTANT:** Check "Add Miniforge3 to my PATH environment variable" (optional but helpful)
   - **IMPORTANT:** Check "Register Miniforge3 as my default Python 3.13" - UNCHECK THIS (keep your existing Python as default)
   - Click "Install"
   - Click "Finish"

3. **Verify Installation:**
   - Open NEW PowerShell window (important - restart shell)
   - Run: `conda --version`
   - Should see: `conda 24.x.x` or similar

---

## Step 2: Create PyKEP Environment

Open PowerShell and run these commands:

```powershell
# Create new environment with Python 3.13
conda create -n lambertlab python=3.13 -y

# Activate the environment
conda activate lambertlab

# Install PyKEP and dependencies
conda install -c conda-forge pykep -y

# Install other required packages
conda install -c conda-forge numpy scipy astropy matplotlib pandas spiceypy numba -y

# Additional packages we use
conda install -c conda-forge click typer rich beautifulsoup4 requests pyyaml -y
```

---

## Step 3: Verify PyKEP Installation

Still in the `lambertlab` environment, run:

```powershell
# Test PyKEP import
python -c "import pykep as pk; print(f'PyKEP version: {pk.__version__}')"

# Run PyKEP test suite
python -c "import pykep; pykep.test.run_test_suite()"

# Test Lambert solver
python -c "import pykep as pk; l = pk.lambert_problem([1,0,0], [0,1,0], 5*3.14159/2); print('Lambert OK:', l.get_v1()[0])"

# Test flyby propagation
python -c "import pykep as pk; vout = pk.fb_prop([1,0,0],[0,1,0],2,3.1415/2,1); print('Flyby OK:', vout)"
```

If all tests pass, PyKEP is ready! ✅

---

## Step 4: Update Project to Use Conda Environment

### Option A: Use Conda in VS Code (Recommended)

1. Open VS Code
2. Press `Ctrl+Shift+P`
3. Type "Python: Select Interpreter"
4. Choose the one that shows `lambertlab` (conda environment)
5. VS Code will now use conda environment

### Option B: Activate in Terminal

Whenever you work on the project:
```powershell
conda activate lambertlab
# Now all commands use conda environment
```

To deactivate:
```powershell
conda deactivate
```

---

## Step 5: Create environment.yml for Reproducibility

In your project root, I'll create this file:

```yaml
name: lambertlab
channels:
  - conda-forge
dependencies:
  - python=3.13
  - pykep
  - numpy
  - scipy
  - astropy
  - matplotlib
  - pandas
  - spiceypy
  - numba
  - click
  - typer
  - rich
  - beautifulsoup4
  - requests
  - pyyaml
  - pytest  # for testing
```

Then anyone can recreate the environment:
```powershell
conda env create -f environment.yml
```

---

## Step 6: Test Existing Code

Activate conda environment and test:

```powershell
conda activate lambertlab

# Navigate to project
cd C:\Users\letsf\OneDrive\Documents\GitHub\Simple-Lambert-Solver

# Try running existing code
python run.py

# Run tests if you have them
python -m pytest tests/
```

---

## Troubleshooting

### Problem: "conda: command not found"
**Solution:** Restart PowerShell after installing Miniforge. If still doesn't work, add to PATH manually or use full path: `C:\Users\<username>\miniforge3\Scripts\conda.exe`

### Problem: "CondaHTTPError: HTTP 000"
**Solution:** Network/firewall issue. Try:
```powershell
conda config --set ssl_verify false
```

### Problem: PyKEP import fails
**Solution:** Make sure environment is activated:
```powershell
conda activate lambertlab
python -c "import sys; print(sys.executable)"  # Should show conda path
```

### Problem: Conflicts with existing Python
**Solution:** Conda environments are isolated. Just activate the right one:
- For old code: use `.venv` (pip environment)
- For new code: `conda activate lambertlab`

---

## Quick Reference

### Conda Commands
```powershell
conda env list                    # List all environments
conda activate lambertlab         # Activate environment
conda deactivate                  # Deactivate environment
conda list                        # Show installed packages
conda update pykep                # Update PyKEP
conda env export > environment.yml # Save current environment
```

### Switching Between Environments
```powershell
# Old pip environment (poliastro 0.7.0)
.\.venv\Scripts\Activate.ps1

# New conda environment (PyKEP)
conda activate lambertlab
```

---

## Next Steps After Installation

1. ✅ PyKEP installed and tested
2. Create PyKEP compatibility test script
3. Compare PyKEP Lambert vs poliastro Lambert
4. Test PyKEP fb_prop() vs our custom rotation
5. Begin migration of Lambert solver
6. Migrate flyby functions

---

**Ready to install? Follow Step 1 above!**

If you run into any issues, we can troubleshoot together. The conda installation is straightforward and takes about 5-10 minutes total.
