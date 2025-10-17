"""Check Ceres kernel coverage."""
import spiceypy as sp

# Load kernels
sp.furnsh('data/kernels/naif0012.tls')
sp.furnsh('data/kernels/20000001.bsp')

# Check what IDs are in the file
ids = sp.spkobj('data/kernels/20000001.bsp')
print(f'Objects in kernel: {[ids[i] for i in range(len(ids))]}')

# Try both possible IDs
for naif_id in [2000001, 20000001]:
    print(f'\nChecking NAIF ID: {naif_id}')
    cover = sp.stypes.SPICEDOUBLE_CELL(2000)
    sp.spkcov('data/kernels/20000001.bsp', naif_id, cover)
    n = sp.wncard(cover)
    
    print(f'  Coverage intervals: {n}')
    
    if n > 0:
        bounds = sp.wnfetd(cover, 0)
        print(f'  First interval (ET seconds): {bounds}')
        
        # Convert to calendar dates
        start_cal = sp.timout(bounds[0], 'YYYY-MM-DD ::TDB')
        end_cal = sp.timout(bounds[1], 'YYYY-MM-DD ::TDB')
        
        print(f'  Coverage: {start_cal} to {end_cal}')
