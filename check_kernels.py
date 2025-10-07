import sys
sys.path.append('lambertlab/src')
from lambertlab.config import DEFAULT_KERNELS
print('DEFAULT_KERNELS:')
for k in DEFAULT_KERNELS:
    print(f'{k}: {k.exists()}')

# Try to load
import spiceypy as sp
for kernel in DEFAULT_KERNELS:
    if kernel.exists():
        try:
            sp.furnsh(kernel.as_posix())
            print(f"Loaded {kernel}")
        except Exception as e:
            print(f"Error loading {kernel}: {e}")
    else:
        print(f"Missing {kernel}")