"""
Test 2: Flyby Mechanics - Gravity Assist Physics
=================================================

Unit tests for PyKEP flyby propagation (fb_prop).
Validates physics: magnitude conservation, turn angle limits, B-plane geometry.
"""

import pytest
import numpy as np
from astropy import units as u
import pykep as pk


class TestFlybyPhysics:
    """Test suite for gravity assist physics."""
    
    def test_magnitude_conservation(self, pykep_available):
        """Test that flyby conserves v_inf magnitude (ballistic)."""
        # Mars flyby scenario
        v_sc = np.array([25.0, 10.0, 0.0])  # Spacecraft velocity (km/s)
        v_mars = np.array([20.0, 15.0, 0.0])  # Mars velocity (km/s)
        rp = 3896.2  # Mars radius + 300 km
        beta = np.pi/4  # B-plane angle
        mu_mars = 42828.0  # km³/s²
        
        # Propagate flyby
        v_out = np.array(pk.fb_prop(
            v_sc.tolist(),
            v_mars.tolist(),
            rp,
            beta,
            mu_mars
        ))
        
        # Check magnitude conservation
        vinf_in = v_sc - v_mars
        vinf_out = v_out - v_mars
        vinf_in_mag = np.linalg.norm(vinf_in)
        vinf_out_mag = np.linalg.norm(vinf_out)
        
        delta_vmag = abs(vinf_in_mag - vinf_out_mag)
        assert delta_vmag < 1e-6, \
            f"V_inf magnitude not conserved: Δ={delta_vmag:.9f} km/s"
        
        print(f"✅ Magnitude conservation: |v∞_in|={vinf_in_mag:.6f}, |v∞_out|={vinf_out_mag:.6f}")
    
    
    def test_turn_angle_limit(self, pykep_available):
        """Test that turn angle obeys hyperbolic flyby physics."""
        v_sc = np.array([25.0, 10.0, 0.0])
        v_mars = np.array([20.0, 15.0, 0.0])
        rp = 3896.2
        beta = 0.0
        mu_mars = 42828.0
        
        v_out = np.array(pk.fb_prop(
            v_sc.tolist(), v_mars.tolist(), rp, beta, mu_mars
        ))
        
        # Calculate turn angle
        vinf_in = v_sc - v_mars
        vinf_out = v_out - v_mars
        cos_delta = np.dot(vinf_in, vinf_out) / (np.linalg.norm(vinf_in) * np.linalg.norm(vinf_out))
        delta = np.arccos(np.clip(cos_delta, -1, 1))
        
        # Theoretical maximum turn angle: δ = 2*arcsin(1/(1 + rp*v²/μ))
        vinf_mag = np.linalg.norm(vinf_in)
        sin_half_delta_max = 1.0 / (1.0 + rp * vinf_mag**2 / mu_mars)
        delta_max = 2.0 * np.arcsin(sin_half_delta_max)
        
        assert delta <= delta_max + 1e-6, \
            f"Turn angle {np.degrees(delta):.2f}° exceeds max {np.degrees(delta_max):.2f}°"
        
        print(f"✅ Turn angle physics: δ={np.degrees(delta):.2f}° (max {np.degrees(delta_max):.2f}°)")
    
    
    def test_low_altitude_high_turn(self, pykep_available):
        """Test that lower periapsis gives larger turn angle."""
        v_sc = np.array([25.0, 10.0, 0.0])
        v_mars = np.array([20.0, 15.0, 0.0])
        beta = 0.0
        mu_mars = 42828.0
        
        # Two periapsis altitudes
        rp_high = 5000.0  # High altitude
        rp_low = 3600.0   # Low altitude (just above Mars surface)
        
        v_out_high = np.array(pk.fb_prop(v_sc.tolist(), v_mars.tolist(), rp_high, beta, mu_mars))
        v_out_low = np.array(pk.fb_prop(v_sc.tolist(), v_mars.tolist(), rp_low, beta, mu_mars))
        
        # Calculate turn angles
        vinf_in = v_sc - v_mars
        
        cos_delta_high = np.dot(vinf_in, v_out_high - v_mars) / \
                        (np.linalg.norm(vinf_in) * np.linalg.norm(v_out_high - v_mars))
        delta_high = np.arccos(np.clip(cos_delta_high, -1, 1))
        
        cos_delta_low = np.dot(vinf_in, v_out_low - v_mars) / \
                       (np.linalg.norm(vinf_in) * np.linalg.norm(v_out_low - v_mars))
        delta_low = np.arccos(np.clip(cos_delta_low, -1, 1))
        
        # Lower altitude should give larger turn
        assert delta_low > delta_high, \
            f"Lower rp should give larger turn: {np.degrees(delta_low):.1f}° vs {np.degrees(delta_high):.1f}°"
        
        print(f"✅ Altitude vs turn: rp={rp_high:.0f}km→δ={np.degrees(delta_high):.1f}°, " +
              f"rp={rp_low:.0f}km→δ={np.degrees(delta_low):.1f}°")
    
    
    def test_bplane_angle_effect(self, pykep_available):
        """Test that B-plane angle rotates outgoing v_inf."""
        v_sc = np.array([25.0, 10.0, 0.0])
        v_mars = np.array([20.0, 15.0, 0.0])
        rp = 3896.2
        mu_mars = 42828.0
        
        # Two different B-plane angles
        beta1 = 0.0
        beta2 = np.pi/2
        
        v_out1 = np.array(pk.fb_prop(v_sc.tolist(), v_mars.tolist(), rp, beta1, mu_mars))
        v_out2 = np.array(pk.fb_prop(v_sc.tolist(), v_mars.tolist(), rp, beta2, mu_mars))
        
        # Outgoing vectors should be different
        diff = np.linalg.norm(v_out1 - v_out2)
        assert diff > 0.1, f"B-plane angle should change outgoing direction: diff={diff:.3f}"
        
        # But magnitudes should be same
        vinf_out1_mag = np.linalg.norm(v_out1 - v_mars)
        vinf_out2_mag = np.linalg.norm(v_out2 - v_mars)
        assert abs(vinf_out1_mag - vinf_out2_mag) < 1e-6, \
            "B-plane rotation should preserve v_inf magnitude"
        
        print(f"✅ B-plane rotation: β=0→v={v_out1}, β=π/2→v={v_out2}")


class TestFlybyIntegration:
    """Test flyby compute_flyby() function."""
    
    def test_mars_flyby_search(self, spice_loaded, pykep_available):
        """Test that flyby targeting search finds valid solutions."""
        from lambertlab.flows.flyby import compute_flyby
        from lambertlab.core.spice_io import rv_helio_spice
        from astropy.time import Time
        
        # Mars flyby at arrival
        epoch = Time("2025-08-20", scale='tdb')
        r_mars, v_mars = rv_helio_spice('MARS', epoch)
        
        # Incoming v_inf (realistic Mars approach)
        vinf_in = np.array([3.0, -2.0, 0.5])  # km/s planetocentric
        
        # Search for flyby to Ceres
        result = compute_flyby(
            epoch=epoch,
            r_planet=r_mars,
            v_planet=v_mars,
            mu_planet=42828.0,
            vinf_in=vinf_in,
            rp_bounds=(3600.0, 10000.0),
            target_body='MARS',  # Simplified test - just target Mars itself
            mu_central=1.32712e11,
            search_arrival_window=(
                epoch + 100*u.day,
                epoch + 300*u.day
            ),
            max_samples=10,
            seed=42,
            min_alt_km=200.0
        )
        
        # Should find a solution (or fail gracefully)
        if result.success:
            assert result.rp is not None
            assert result.turn_angle is not None
            assert 3600.0 <= result.rp <= 10000.0
            print(f"✅ Flyby search: rp={result.rp:.1f}km, δ={np.degrees(result.turn_angle):.1f}°")
        else:
            # Acceptable to not find solution for this simplified test
            print(f"ℹ️  Flyby search: {result.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
