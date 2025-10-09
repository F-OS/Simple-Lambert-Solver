"""Earth-Mars-Ceres ballistic flyby screening."""

from __future__ import annotations

import csv
import numpy as np
from astropy.time import Time
from collections import defaultdict

from ..core.config import MU_MARS, RP_MIN_MARS
from ..core.flyby_math import feasibility, powered_delta_v
from ..core.flyby_build import theta_sweep


def screen_emc(em_csv: str = 'em_porkchop.csv', mc_csv: str = 'mc_req.csv', out_csv: str = 'emc_screen.csv',
               rp_min_km: float = 300.0, theta_step: float = 5.0, dv_thresh: float = 5.0) -> None:
    """Screen Earth-Mars-Ceres trajectories for ballistic flyby feasibility.
    
    Joins em_porkchop.csv with mc_req.csv by mars_iso and computes feasibility
    for each matching combination.
    
    Args:
        em_csv: Path to Earth-Mars porkchop CSV
        mc_csv: Path to Mars-Ceres requirements CSV  
        out_csv: Output CSV filename
    """
    # Read EM data: mars_iso -> list of rows
    em_data = defaultdict(list)
    with open(em_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mars_iso = row['mars_iso']
            em_data[mars_iso].append(row)
    
    # Read MC data: mars_iso -> list of rows
    mc_data = defaultdict(list)
    with open(mc_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mars_iso = row['mars_iso']
            mc_data[mars_iso].append(row)
    
    # Output CSV
    with open(out_csv, 'w', newline='') as f:
        fieldnames = [
            'dep_iso', 'mars_iso', 'ceres_iso', 'tof1_d', 'tof2_d', 'C3_earth', 
            'vinf_req_kms', 'vinf_req_x', 'vinf_req_y', 'vinf_req_z',
            'vinf_in_x', 'vinf_in_y', 'vinf_in_z',
            'ballistic_ok', 'delta_req_rad', 'rp_needed_km', 'mag_mismatch_kms', 'angle_err_deg',
            'dv_peri_kms', 'best_theta_deg', 'best_ang_err_deg'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # For each mars_iso that appears in both
        for mars_iso in set(em_data.keys()) & set(mc_data.keys()):
            em_rows = em_data[mars_iso]
            mc_rows = mc_data[mars_iso]
            
            for em_row in em_rows:
                for mc_row in mc_rows:
                    # Extract vectors
                    vinf_in_vec = np.array([
                        float(em_row['vinf_in_x']),
                        float(em_row['vinf_in_y']), 
                        float(em_row['vinf_in_z'])
                    ])
                    
                    vinf_out_req_vec = np.array([
                        float(mc_row['vinf_req_x']),
                        float(mc_row['vinf_req_y']),
                        float(mc_row['vinf_req_z'])
                    ])
                    
                    # Compute feasibility
                    feas = feasibility(vinf_in_vec, vinf_out_req_vec, MU_MARS, rp_min_km)
                    
                    # If ballistic fails, try theta sweep
                    best_theta_deg = None
                    best_ang_err_deg = None
                    if not feas['ballistic_ok']:
                        v_mars_vec = np.array([
                            float(em_row['vM_x']),
                            float(em_row['vM_y']),
                            float(em_row['vM_z'])
                        ])
                        best_theta_deg, best_ang_err_deg = theta_sweep(
                            vinf_in_vec, v_mars_vec, feas['rp_needed_km'], vinf_out_req_vec, step_deg=theta_step
                        )
                    
                    # Calculate powered delta-V at periapsis
                    dv_peri_kms = powered_delta_v(vinf_in_vec, vinf_out_req_vec, MU_MARS, rp_min_km)
                    
                    # Write row
                    writer.writerow({
                        'dep_iso': em_row['dep_iso'],
                        'mars_iso': mars_iso,
                        'ceres_iso': mc_row['ceres_iso'],
                        'tof1_d': em_row['tof1_d'],
                        'tof2_d': mc_row['tof2_d'],
                        'C3_earth': em_row['C3_earth'],
                        'vinf_req_kms': mc_row['vinf_req_kms'],
                        'vinf_req_x': mc_row['vinf_req_x'],
                        'vinf_req_y': mc_row['vinf_req_y'],
                        'vinf_req_z': mc_row['vinf_req_z'],
                        'vinf_in_x': em_row['vinf_in_x'],
                        'vinf_in_y': em_row['vinf_in_y'],
                        'vinf_in_z': em_row['vinf_in_z'],
                        **feas,
                        'dv_peri_kms': dv_peri_kms,
                        'best_theta_deg': best_theta_deg,
                        'best_ang_err_deg': best_ang_err_deg
                    })


if __name__ == '__main__':
    screen_emc()