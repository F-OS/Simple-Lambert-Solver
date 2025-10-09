"""Check if poliastro has compute_flyby function."""

try:
    from poliastro.core.flybys import compute_flyby
    print("✅ poliastro.core.flybys.compute_flyby is AVAILABLE!")
    
    import inspect
    sig = inspect.signature(compute_flyby)
    print(f"\nSignature: {sig}")
    
    # Get the docstring
    if compute_flyby.__doc__:
        print(f"\nDocstring:\n{compute_flyby.__doc__}")
    
    # Try to get parameter details
    print("\nParameters:")
    for param_name, param in sig.parameters.items():
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'no type hint'}")
        
except ImportError as e:
    print(f"❌ poliastro.core.flybys NOT available in version 0.7.0")
    print(f"   Error: {e}")
    print("\n   This module was added in a later version of poliastro.")
    print("   The stable docs show features from the latest version, not 0.7.0")
except Exception as e:
    print(f"⚠️  Unexpected error: {e}")
