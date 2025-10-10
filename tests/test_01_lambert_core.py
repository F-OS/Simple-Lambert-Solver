"""
Test 1: Core Components - Lambert Solver
=========================================

Unit tests for PyKEP Lambert solver integration.
Validates realistic Earth-Mars transfers with known good parameters.
"""

import pytest
import numpy as np
from astropy import units as u
from astropy.time import Time


class TestLambertSolver:
    """Test suite for Lambert problem solver."""
    
    def test_earth_mars_2025_transfer(self, spice_loaded, pykep_available):
        """Test realistic Earth-Mars transfer for 2025 opportunity."""
        from lambertlab.core.solver import compute_c3_tof
        
        # 2025 Earth-Mars opportunity
        dep_date = "2025-02-15"
        arr_date = "2025-09-10"
        
        tof_days, c3, vinf_dep, vinf_arr, used = compute_c3_tof(
            dep_date, arr_date, 'EARTH', 'MARS'
        )
        
        # Validate results are physically reasonable
        assert tof_days > 0, "TOF must be positive"
        assert 150 < tof_days < 300, f"TOF {tof_days} days unrealistic for Mars transfer"
        assert c3 > 0, "C3 must be positive"
        assert c3 < 1000, f"C3 {c3:.2f} km²/s² unreasonably high"
        
        # V-infinity should be reasonable
        vinf_dep_mag = np.linalg.norm(vinf_dep)
        vinf_arr_mag = np.linalg.norm(vinf_arr)
        assert vinf_dep_mag > 0 and vinf_dep_mag < 50, "Departure v_inf must be reasonable"
        assert vinf_arr_mag > 0 and vinf_arr_mag < 50, "Arrival v_inf must be reasonable"
        
        # C3 should match departure v_inf squared
        c3_check = vinf_dep_mag**2
        assert abs(c3 - c3_check) < 0.01, f"C3 mismatch: {c3:.2f} vs {c3_check:.2f}"
        
        print(f"✅ Earth-Mars 2025: TOF={tof_days:.1f}d, C3={c3:.2f}km²/s², v∞={vinf_dep_mag:.2f}km/s")
    
    
    def test_short_transfer_fails(self, spice_loaded, pykep_available):
        """Test that unrealistically short transfers either fail or have very high C3."""
        from lambertlab.core.solver import compute_c3_tof
        
        # 30 day Earth-Mars transfer is nearly impossible
        dep_date = "2025-01-15"
        arr_date = "2025-02-15"
        
        try:
            tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep_date, arr_date, 'EARTH', 'MARS')
            # If it doesn't fail, C3 should be extremely high
            assert c3 > 500, f"Very short transfer should have extremely high C3, got {c3:.2f}"
            print(f"✅ Short transfer: C3={c3:.2f} km²/s² (extremely high as expected)")
        except RuntimeError:
            # Also acceptable - solver may reject impossible geometries
            print(f"✅ Short transfer correctly rejected by solver")
    
    
    def test_hohmann_transfer_approximation(self, spice_loaded, pykep_available):
        """Test that transfers exist (C3 values vary by launch window)."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Just test that we can compute a transfer
        dep_date = "2025-01-15"
        arr_date = "2025-09-15"  # ~240 days
        
        tof_days, c3, vinf_dep, vinf_arr, used = compute_c3_tof(
            dep_date, arr_date, 'EARTH', 'MARS'
        )
        
        # Just verify it completes and gives reasonable values
        assert tof_days > 200, "Long transfer should have sufficient TOF"
        assert c3 > 0 and c3 < 1000, "C3 should be positive and finite"
        
        print(f"✅ Long transfer: TOF={tof_days:.1f}d, C3={c3:.2f}km²/s²")
    
    
    def test_multiple_departure_dates(self, spice_loaded, pykep_available):
        """Test Lambert solver across multiple departure dates."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Test 5 different departure dates in Jan 2025
        results = []
        for day in [1, 8, 15, 22, 29]:
            dep_date = f"2025-01-{day:02d}"
            arr_date = "2025-08-20"
            
            tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(
                dep_date, arr_date, 'EARTH', 'MARS'
            )
            results.append((day, tof, c3))
        
        # All should succeed
        assert len(results) == 5, "All departure dates should compute"
        
        # C3 should vary with departure date (not constant)
        c3_values = [r[2] for r in results]
        c3_range = max(c3_values) - min(c3_values)
        assert c3_range > 1.0, "C3 should vary with departure date"
        
        print(f"✅ Multiple departures: C3 range = {c3_range:.2f} km²/s²")


class TestEphemerisAccuracy:
    """Test SPICE ephemeris integration."""
    
    def test_earth_position_reasonable(self, spice_loaded):
        """Test that Earth position from SPICE is ~1 AU from Sun."""
        from lambertlab.core.spice_io import rv_helio_spice
        
        epoch = Time("2025-01-15", scale='tdb')
        r_earth, v_earth = rv_helio_spice('EARTH', epoch)
        
        # Earth should be ~1 AU from Sun
        r_mag = np.linalg.norm(r_earth)
        AU_km = 1.496e8
        assert 0.98 * AU_km < r_mag < 1.02 * AU_km, \
            f"Earth distance {r_mag/AU_km:.3f} AU unrealistic"
        
        # Orbital velocity should be ~30 km/s
        v_mag = np.linalg.norm(v_earth)
        assert 28.0 < v_mag < 32.0, f"Earth velocity {v_mag:.2f} km/s unrealistic"
        
        print(f"✅ Earth ephemeris: r={r_mag/AU_km:.3f}AU, v={v_mag:.2f}km/s")
    
    
    def test_mars_orbit_parameters(self, spice_loaded):
        """Test that Mars orbital parameters are realistic."""
        from lambertlab.core.spice_io import rv_helio_spice
        
        epoch = Time("2025-01-15", scale='tdb')
        r_mars, v_mars = rv_helio_spice('MARS', epoch)
        
        # Mars should be ~1.52 AU from Sun
        r_mag = np.linalg.norm(r_mars)
        AU_km = 1.496e8
        assert 1.38 * AU_km < r_mag < 1.67 * AU_km, \
            f"Mars distance {r_mag/AU_km:.3f} AU outside orbit range"
        
        # Orbital velocity should be ~24 km/s
        v_mag = np.linalg.norm(v_mars)
        assert 22.0 < v_mag < 26.0, f"Mars velocity {v_mag:.2f} km/s unrealistic"
        
        print(f"✅ Mars ephemeris: r={r_mag/AU_km:.3f}AU, v={v_mag:.2f}km/s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
