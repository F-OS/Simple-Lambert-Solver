"""
Quick diagnostic script to check chain3 deltaV matching values
"""
import numpy as np
from astropy.time import Time
import astropy.units as u
import sys
sys.path.insert(0, 'src')

from lambertlab.core.spice_io import load_kernels, rv_helio_spice
from lambertlab.core.lambert_io import solve_leg
from lambertlab.core.config import MU_MARS

# Load kernels
kernels = [
    "data/kernels/naif0012.tls",
    "data/kernels/de440.bsp",
    "data/kernels/gm_de440.tpc",
    "data/kernels/20000001.bsp",
    "data/kernels/mar097.bsp",
    "data/kernels/pck00011.tpc"
]
load_kernels(kernels)

# Use first Leg1 solution from the CSV
t_dep = Time("2035-04-01T00:00:00.000", scale='tdb')
tof1 = 150.0
t_flyby = t_dep + tof1 * u.day
vinf_in_mag = 8.924541589977329  # from CSV

print(f"Testing Leg1 solution:")
print(f"  Departure: {t_dep.iso}")
print(f"  Flyby: {t_flyby.iso}")
print(f"  V-infinity in: {vinf_in_mag:.3f} km/s")
print()

# Get flyby state
r_flyby, v_flyby = rv_helio_spice("499", t_flyby)
print(f"Flyby position: {r_flyby}")
print(f"Flyby velocity: {v_flyby}")
print()

# Reconstruct vinf_in vector (approximate - use radial direction for simplicity)
vinf_in_vec = vinf_in_mag * (r_flyby / np.linalg.norm(r_flyby))  # radial approximation

# Try one rp and theta
rp = 3896.2  # min rp
theta = 0.0  # deg

# Calculate turn angle
mu_flyby = MU_MARS
x = 1.0 + (rp * vinf_in_mag**2) / mu_flyby
sin_half_delta = 1.0 / x
delta = 2.0 * np.arcsin(sin_half_delta)

print(f"Flyby parameters:")
print(f"  rp = {rp:.1f} km")
print(f"  theta = {theta:.1f} deg")
print(f"  turn angle = {np.degrees(delta):.2f} deg")
print()

# Construct vinf_out (simplified rotation)
vinf_in_unit = vinf_in_vec / vinf_in_mag
perp = np.array([0, 0, 1]) - np.dot([0, 0, 1], vinf_in_unit) * vinf_in_unit
if np.linalg.norm(perp) < 0.1:
    perp = np.array([0, 1, 0]) - np.dot([0, 1, 0], vinf_in_unit) * vinf_in_unit
perp = perp / np.linalg.norm(perp)
perp2 = np.cross(vinf_in_unit, perp)

theta_rad = np.radians(theta)
rot_axis = np.cos(theta_rad) * perp + np.sin(theta_rad) * perp2

cos_d = np.cos(delta)
sin_d = np.sin(delta)
vinf_out_vec = (vinf_in_vec * cos_d + 
               np.cross(rot_axis, vinf_in_vec) * sin_d +
               rot_axis * np.dot(rot_axis, vinf_in_vec) * (1 - cos_d))

v_sc_post = v_flyby + vinf_out_vec

print(f"Post-flyby velocity: {v_sc_post}")
print()

# Try several Leg2 TOFs
tof2_values = [180, 280, 380, 480, 580]
dv_matches = []

for tof2 in tof2_values:
    t_arr = t_flyby + tof2 * u.day
    
    try:
        r_arr, v_arr = rv_helio_spice("20000001", t_arr)
        
        # Lambert solve
        v1, v2 = solve_leg(r_flyby * u.km, r_arr * u.km, tof2 * u.day)
        v1_arr = v1.to(u.km/u.s).value
        
        # Check deltaV match
        dv_match = np.linalg.norm(v_sc_post - v1_arr)
        dv_match_ms = dv_match * 1000
        
        dv_matches.append(dv_match_ms)
        
        print(f"TOF2 = {tof2} days:")
        print(f"  Lambert v1 = {v1_arr}")
        print(f"  v_sc_post  = {v_sc_post}")
        print(f"  DV match = {dv_match_ms:.1f} m/s")
        
    except Exception as e:
        print(f"TOF2 = {tof2} days: FAILED - {e}")
    
    print()

if dv_matches:
    print(f"\nDelta-V match statistics:")
    print(f"  Min: {min(dv_matches):.1f} m/s")
    print(f"  Max: {max(dv_matches):.1f} m/s")
    print(f"  Mean: {np.mean(dv_matches):.1f} m/s")
    print()
    print(f"With dv_tol = 1000 m/s: {sum(1 for dv in dv_matches if dv <= 1000)} / {len(dv_matches)} would pass")
    print(f"With dv_tol = 5000 m/s: {sum(1 for dv in dv_matches if dv <= 5000)} / {len(dv_matches)} would pass")
