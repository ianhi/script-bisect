# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
#   "numpy",
#   "scipy"
# ]
# ///
"""
Test script for xarray issue #10683: Performance regression in interpolation
https://github.com/pydata/xarray/issues/10683

This script tests the interpolation performance that became ~76x slower
between 2024.11.0 and 2025.1.0.

Expected regressing commit: 29fe679a9fc4611af44e4889b992639dbf40cc91
"""

import sys
import time

import numpy as np
import xarray as xr


def test_interpolation_performance() -> bool:
    """Test interpolation performance and exit with error if too slow."""
    print("🧪 Testing xarray interpolation performance regression...")

    try:
        print("  📦 Creating test data...")

        # Create test data similar to issue report
        # 122 x 65 x 65 array (slightly smaller for faster testing)
        data = np.random.random((80, 50, 50))
        dims = ("x", "y", "z")
        coords = {"x": np.arange(80), "y": np.arange(50), "z": np.linspace(0, 1, 50)}
        da = xr.DataArray(data, dims=dims, coords=coords)

        print(f"  📊 Test array shape: {da.shape}")
        print(f"  📦 xarray version: {xr.__version__}")

        # Create interpolation coordinates
        interp_z = np.linspace(0.1, 0.9, 30)  # Fewer points for faster testing

        print("  🔥 Running warmup to handle numba compilation...")
        # Warmup run to trigger any JIT compilation
        warmup_z = np.linspace(0.1, 0.2, 5)  # Small warmup
        _ = da.interp(z=warmup_z)
        print("  🔥 Warmup complete")

        print("  ⏱️ Starting interpolation timing test...")
        start_time = time.time()

        # Perform the interpolation that shows regression
        result = da.interp(z=interp_z)

        elapsed_time = time.time() - start_time
        print(f"  ⏱️ Interpolation completed in {elapsed_time:.3f} seconds")

        print(f"  📊 Result shape: {result.shape}")

        # Performance threshold: if it takes more than 1 second, consider it a regression
        # (adjust this threshold based on the actual performance difference)
        if elapsed_time > 1.0:
            print("  💥 PERFORMANCE REGRESSION DETECTED!")
            print(f"  💥 Interpolation took {elapsed_time:.3f}s (threshold: 1.0s)")
            return False  # Test failed - performance regression
        else:
            print(f"  ✅ Performance acceptable: {elapsed_time:.3f}s")
            return True  # Test passed - no regression

    except Exception as e:
        print(f"  💥 Test failed with error: {e}")
        return False


def show_version_info() -> None:
    """Show version information for debugging."""
    print("📋 Version Information:")
    print(f"  Python: {sys.version}")
    print(f"  xarray: {xr.__version__}")

    try:
        import numpy as np

        print(f"  numpy: {np.__version__}")
    except ImportError:
        print("  numpy: Not available")

    try:
        import scipy

        print(f"  scipy: {scipy.__version__}")
    except ImportError:
        print("  scipy: Not available")

    print()


def main() -> bool:
    """Main test function."""
    print("🔬 xarray interpolation performance regression test (issue #10683)")
    print("=" * 70)

    show_version_info()

    success = test_interpolation_performance()

    if success:
        print("\n🎉 Test PASSED - No performance regression detected")
        return True
    else:
        print("\n💥 Test FAILED - Performance regression detected")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
