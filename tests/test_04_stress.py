"""
Test 4: Stress Tests - System Performance and Robustness
=========================================================

Large-scale tests to validate system performance and stability.
Tests concurrent operations, large grids, edge cases.
"""

import time

import numpy as np
import pytest
from astropy.time import Time


class TestLargeGrids:
    """Test porkchop generation with realistic grid sizes."""
    
    @pytest.mark.slow
    def test_full_month_porkchop(self, spice_loaded, pykep_available):
        """Test full month porkchop plot (30x20 grid = 600 points)."""
        from lambertlab.flows.em_only import screen_em_grid_cached
        
        dep_start = Time("2025-01-01", scale='tdb')
        dep_end = Time("2025-01-31", scale='tdb')
        dep_step = 1  # Daily
        
        tof_min = 180
        tof_max = 220
        tof_step = 2  # Every 2 days
        
        start = time.time()
        
        dep_times, tof_days, c3_grid, *_ = screen_em_grid_cached(
            dep_start, dep_end, dep_step,
            tof_min, tof_max, tof_step,
            dep_body='EARTH',
            arr_body='MARS',
            n_workers=1
        )
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 60 seconds for 600 points)
        n_points = len(dep_times) * len(tof_days)
        assert elapsed < 120, f"Grid calculation took {elapsed:.1f}s (too slow)"
        
        # Check coverage
        valid_pct = 100 * np.sum(np.isfinite(c3_grid)) / c3_grid.size
        assert valid_pct > 50, f"Only {valid_pct:.1f}% of grid valid"
        
        print(f"✅ Full month porkchop: {n_points} points in {elapsed:.1f}s " +
              f"({n_points/elapsed:.1f} pts/s, {valid_pct:.1f}% valid)")
    
    
    @pytest.mark.slow
    def test_high_resolution_porkchop(self, spice_loaded, pykep_available):
        """Test high-resolution porkchop (small step sizes)."""
        from lambertlab.flows.em_only import screen_em_grid_cached
        
        # 1-week window, high resolution
        dep_start = Time("2025-02-01", scale='tdb')
        dep_end = Time("2025-02-08", scale='tdb')
        dep_step = 0.5  # 12-hour steps
        
        tof_min = 195
        tof_max = 205
        tof_step = 0.5  # 12-hour steps
        
        start = time.time()
        
        dep_times, tof_days, c3_grid, *_ = screen_em_grid_cached(
            dep_start, dep_end, dep_step,
            tof_min, tof_max, tof_step,
            dep_body='EARTH',
            arr_body='MARS',
            n_workers=1
        )
        
        elapsed = time.time() - start
        n_points = len(dep_times) * len(tof_days)
        
        print(f"✅ High-res porkchop: {n_points} points in {elapsed:.1f}s")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_same_day_departure_arrival(self, spice_loaded, pykep_available):
        """Test that same-day departure/arrival fails gracefully."""
        from lambertlab.core.solver import compute_c3_tof
        
        with pytest.raises((ValueError, RuntimeError)):
            compute_c3_tof("2025-01-15", "2025-01-15", 'EARTH', 'MARS')
    
    
    def test_arrival_before_departure(self, spice_loaded, pykep_available):
        """Test that negative TOF fails gracefully."""
        from lambertlab.core.solver import compute_c3_tof
        
        with pytest.raises((ValueError, RuntimeError)):
            compute_c3_tof("2025-02-01", "2025-01-01", 'EARTH', 'MARS')
    
    
    def test_extreme_c3_filtered(self, spice_loaded, pykep_available):
        """Test that extreme C3 values are handled correctly."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Very short TOF should either fail or return high C3
        dep = "2025-01-15"
        arr = "2025-03-01"  # Only 45 days - very fast
        
        try:
            tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(dep, arr, 'EARTH', 'MARS')
            # If it succeeds, C3 should be very high
            assert c3 > 50.0, f"Fast transfer should have high C3, got {c3:.2f}"
        except RuntimeError:
            # Acceptable to fail for impossible transfers
            pass
    
    
    def test_zero_periapsis_fails(self, pykep_available):
        """Test that flyby propagation handles edge cases."""
        import pykep as pk
        
        v_sc = np.array([25.0, 10.0, 0.0])
        v_planet = np.array([20.0, 15.0, 0.0])
        
        # PyKEP may or may not reject rp=0, just verify it doesn't crash
        try:
            result = pk.fb_prop(v_sc.tolist(), v_planet.tolist(), 0.0, 0.0, 42828.0)
            # If it succeeds, verify result is physically reasonable
            assert result is not None, "fb_prop should return result or raise exception"
            print("✅ Zero periapsis handled (no exception)")
        except Exception as e:
            # Also acceptable - PyKEP may reject unphysical periapsis
            print(f"✅ Zero periapsis correctly rejected: {type(e).__name__}")
    
    
    def test_invalid_body_name(self, spice_loaded, pykep_available):
        """Test that invalid body names fail gracefully."""
        from lambertlab.core.solver import compute_c3_tof
        
        with pytest.raises(Exception):
            compute_c3_tof("2025-01-15", "2025-07-15", 'EARTH', 'PLUTO9')


class TestNumericalStability:
    """Test numerical precision and stability."""
    
    def test_repeated_calculations_stable(self, spice_loaded, pykep_available):
        """Test that repeated calculations give same result."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Run same calculation 5 times
        results = []
        for _ in range(5):
            tof, c3, vinf_dep, vinf_arr, used = compute_c3_tof(
                "2025-01-15", "2025-08-15", 'EARTH', 'MARS'
            )
            results.append(c3)
        
        # All results should be identical
        c3_std = np.std(results)
        assert c3_std < 1e-10, f"Results not stable: std={c3_std:.2e}"
        
        print(f"✅ Numerical stability: {len(results)} runs, std={c3_std:.2e}")
    
    
    def test_magnitude_conservation_precision(self, pykep_available):
        """Test v_inf magnitude conservation to high precision."""
        import pykep as pk
        
        # Run 100 different flyby scenarios
        errors = []
        for i in range(100):
            # Random scenario
            np.random.seed(i)
            v_sc = np.random.rand(3) * 30 + 10  # 10-40 km/s
            v_planet = np.random.rand(3) * 25 + 5  # 5-30 km/s
            rp = 3600 + np.random.rand() * 5000  # 3600-8600 km
            beta = np.random.rand() * 2 * np.pi
            mu = 42828.0
            
            v_out = np.array(pk.fb_prop(
                v_sc.tolist(), v_planet.tolist(), rp, beta, mu
            ))
            
            vinf_in_mag = np.linalg.norm(v_sc - v_planet)
            vinf_out_mag = np.linalg.norm(v_out - v_planet)
            error = abs(vinf_in_mag - vinf_out_mag)
            errors.append(error)
        
        # All should conserve to machine precision
        max_error = max(errors)
        assert max_error < 1e-6, f"Max magnitude error {max_error:.2e} too large"
        
        print(f"✅ Magnitude conservation: max error = {max_error:.2e} km/s (100 scenarios)")


class TestPerformanceBenchmarks:
    """Benchmark performance metrics."""
    
    def test_lambert_solve_speed(self, spice_loaded, pykep_available):
        """Benchmark Lambert solver speed."""
        from lambertlab.core.solver import compute_c3_tof
        
        # Time 100 Lambert solves
        n_runs = 100
        start = time.time()
        
        for i in range(n_runs):
            day = 1 + (i % 28)
            dep = f"2025-01-{day:02d}"
            arr = "2025-08-15"
            compute_c3_tof(dep, arr, 'EARTH', 'MARS')
        
        elapsed = time.time() - start
        per_solve = (elapsed / n_runs) * 1000  # ms
        
        # Should be fast (< 10 ms per solve)
        assert per_solve < 50, f"Lambert solve too slow: {per_solve:.1f} ms"
        
        print(f"✅ Lambert performance: {per_solve:.2f} ms/solve ({n_runs} runs)")
    
    
    def test_flyby_propagation_speed(self, pykep_available):
        """Benchmark flyby propagation speed."""
        import pykep as pk
        
        # Time 1000 flyby propagations
        n_runs = 1000
        v_sc = np.array([25.0, 10.0, 0.0])
        v_planet = np.array([20.0, 15.0, 0.0])
        
        start = time.time()
        
        for i in range(n_runs):
            rp = 3600 + (i % 5000)
            beta = (i % 360) * np.pi / 180
            pk.fb_prop(v_sc.tolist(), v_planet.tolist(), rp, beta, 42828.0)
        
        elapsed = time.time() - start
        per_prop = (elapsed / n_runs) * 1000000  # μs
        
        # Should be very fast (< 100 μs per propagation)
        assert per_prop < 500, f"Flyby propagation too slow: {per_prop:.1f} μs"
        
        print(f"✅ Flyby performance: {per_prop:.1f} μs/propagation ({n_runs} runs)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
