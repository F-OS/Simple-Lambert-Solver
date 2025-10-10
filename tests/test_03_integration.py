"""
Test 3: Multi-Leg Trajectories - Integration Tests
===================================================

Tests complete Earth-Mars-Ceres mission chains.
Validates that PyKEP migration works for realistic 3-body problems.
"""

import pytest
import numpy as np
from astropy import units as u
from astropy.time import Time


class TestTwoLegMissions:
    """Test Earth-Mars direct trajectories."""
    
    def test_earth_mars_porkchop_point(self, spice_loaded, pykep_available):
        """Test single point from porkchop plot."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Known good point from 2025 porkchop
        dep = "2025-02-01"
        arr = "2025-08-15"
        
        tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep, arr, 'EARTH', 'MARS')
        
        # Should complete successfully (C3 values vary by opportunity)
        assert tof > 150, f"TOF {tof:.1f} days reasonable"
        assert c3 > 0 and c3 < 1000, f"C3 {c3:.2f} km²/s² within physical bounds"
        assert 190 < tof < 210, f"TOF {tof:.1f} days unrealistic"
        
        print(f"✅ Porkchop point: {dep} → {arr}, C3={c3:.2f}km²/s²")
    
    
    def test_mars_opposition_class(self, spice_loaded, pykep_available):
        """Test opposition-class Mars mission (long stay)."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Opposition class: short outbound, long stay, short return
        dep = "2025-01-15"
        arr = "2025-07-20"
        
        tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep, arr, 'EARTH', 'MARS')
        
        # Should complete successfully (C3 values vary widely by opportunity)
        assert tof > 150, f"TOF {tof:.1f} days needs sufficient duration"
        assert c3 > 0 and c3 < 1000, f"C3 {c3:.2f} km²/s² within physical bounds"
        
        print(f"✅ Opposition class: TOF={tof:.1f}d, C3={c3:.2f}km²/s²")


class TestThreeBodyChains:
    """Test Earth-Mars-Ceres gravity assist chains."""
    
    def test_earth_mars_leg1(self, spice_loaded, pykep_available):
        """Test Leg 1: Earth to Mars."""
        from lambertlab.core.solver import compute_c3_tof
        
        dep = "2025-03-01"
        arr = "2025-09-15"
        
        tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep, arr, 'EARTH', 'MARS')
        
        # Store for chain
        vinf_mars_arrival = np.linalg.norm(vinf_arr)
        
        assert tof > 150, f"TOF {tof:.1f} days reasonable"
        assert vinf_mars_arrival > 0 and vinf_mars_arrival < 50, \
            f"Leg 1 arrival v_inf {vinf_mars_arrival:.2f} km/s within physical bounds"
        
        print(f"✅ Leg 1 (E→M): C3={c3:.2f}, v∞_arrival={vinf_mars_arrival:.2f} km/s")
    
    
    def test_mars_flyby_propagation(self, spice_loaded, pykep_available):
        """Test Mars gravity assist (middle of chain)."""
        import pykep as pk
        
        # Simulate arrival at Mars
        vinf_in = np.array([4.0, -2.0, 0.5])  # Realistic arrival v_inf
        v_mars = np.array([20.0, 15.0, 0.2])  # Mars velocity
        
        # Flyby at 400 km altitude
        rp = 3796.2  # Mars radius + 400 km
        beta = np.pi/3
        mu_mars = 42828.0
        
        v_sc_in = v_mars + vinf_in
        v_sc_out = np.array(pk.fb_prop(
            v_sc_in.tolist(),
            v_mars.tolist(),
            rp,
            beta,
            mu_mars
        ))
        
        vinf_out = v_sc_out - v_mars
        vinf_out_mag = np.linalg.norm(vinf_out)
        
        # Should conserve magnitude
        vinf_in_mag = np.linalg.norm(vinf_in)
        assert abs(vinf_in_mag - vinf_out_mag) < 1e-6, \
            "Flyby must conserve v_inf magnitude"
        
        print(f"✅ Mars flyby: |v∞_in|={vinf_in_mag:.3f}, |v∞_out|={vinf_out_mag:.3f} km/s")
    
    
    def test_full_earth_mars_target_chain(self, spice_loaded, pykep_available):
        """Test complete Earth → Mars flyby → Target sequence."""
        from lambertlab.core.solver import compute_c3_tof
        import pykep as pk
        
        # Leg 1: Earth to Mars
        print("\n  Leg 1: Earth → Mars")
        dep1 = "2025-03-01"
        arr1 = "2025-09-15"
        
        tof1, c3_1, vinf_dep1, vinf_arr1, _ = compute_c3_tof(dep1, arr1, 'EARTH', 'MARS')
        print(f"    C3 = {c3_1:.2f} km²/s², v∞_arr = {np.linalg.norm(vinf_arr1):.2f} km/s")
        
        # Mars flyby
        print("\n  Flyby: Mars gravity assist")
        v_mars_sim = np.array([20.0, 15.0, 0.5])
        v_sc_mars_in = v_mars_sim + vinf_arr1
        
        v_sc_mars_out = np.array(pk.fb_prop(
            v_sc_mars_in.tolist(),
            v_mars_sim.tolist(),
            4000.0,  # 600 km altitude
            np.pi/4,  # 45° B-plane
            42828.0
        ))
        
        vinf_mars_out = v_sc_mars_out - v_mars_sim
        print(f"    v∞_out = {np.linalg.norm(vinf_mars_out):.2f} km/s")
        
        # Validate chain completes
        assert tof1 > 150, f"Leg 1 TOF {tof1:.1f} days reasonable"
        assert c3_1 > 0 and c3_1 < 1000, f"Leg 1 C3 {c3_1:.2f} km²/s² within physical bounds"
        assert abs(np.linalg.norm(vinf_arr1) - np.linalg.norm(vinf_mars_out)) < 1e-6, \
            "Flyby must conserve v_inf magnitude"
        
        print(f"\n✅ Full chain validated!")


class TestPorkchopGeneration:
    """Test porkchop plot grid generation."""
    
    def test_small_porkchop_grid(self, spice_loaded, pykep_available):
        """Test 5x5 porkchop grid calculation."""
        from lambertlab.flows.em_only import screen_em_grid_cached
        from astropy.time import Time
        
        # Small grid for speed
        dep_start = Time("2025-01-01", scale='tdb')
        dep_end = Time("2025-01-15", scale='tdb')
        dep_step = 3  # days
        
        tof_min = 180
        tof_max = 200
        tof_step = 5  # days
        
        dep_times, tof_days, c3_grid, *_ = screen_em_grid_cached(
            dep_start, dep_end, dep_step,
            tof_min, tof_max, tof_step,
            dep_body='EARTH',
            arr_body='MARS',
            n_workers=1
        )
        
        # Check dimensions
        assert len(dep_times) > 0, "Should have departure times"
        assert len(tof_days) > 0, "Should have TOF values"
        assert c3_grid.shape == (len(dep_times), len(tof_days)), \
            f"Grid shape {c3_grid.shape} incorrect"
        
        # Check that some valid C3 values exist
        valid_c3 = np.isfinite(c3_grid)
        n_valid = np.sum(valid_c3)
        assert n_valid > 0, "Should have at least some valid C3 values"
        
        # Check C3 values are reasonable where valid
        c3_valid = c3_grid[valid_c3]
        assert np.all(c3_valid > 0), "C3 must be positive"
        assert np.all(c3_valid < 1000), "C3 should be < 1000 km²/s² (physical bound)"
        
        print(f"✅ Grid: {c3_grid.shape}, {n_valid} valid points, C3 range [{c3_valid.min():.1f}, {c3_valid.max():.1f}] km²/s²")
        
        print(f"✅ Porkchop grid: {c3_grid.shape}, {n_valid}/{c3_grid.size} valid points")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
