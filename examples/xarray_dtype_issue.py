# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
#   "pandas",
#   "numpy",
# ]
# ///
"""
Real-world test case for xarray issue #10703:
to_dataframe() changes coordinate variable dtypes

This script demonstrates the regression where coordinate dtypes
are changed when converting to DataFrame. The issue was introduced
between v2025.08.0 and v2025.09.0.

Known bisection result: a13a2556a29b3c5ba342a402b2598bab42939b46

Usage:
    script-bisect xarray_dtype_issue.py xarray v2025.08.0 v2025.09.0

Expected output:
    Should find commit a13a2556a29b3c5ba342a402b2598bab42939b46
"""

import sys

import numpy as np
import pandas as pd
import xarray as xr


def test_to_dataframe_dtype_preservation() -> bool:
    """Test that to_dataframe() preserves coordinate dtypes."""
    print("🧪 Testing xarray to_dataframe() dtype preservation...")

    # Test case 1: 2D DataArray with different coordinate dtypes
    print("  📊 Testing 2D DataArray...")
    x = np.array([1], dtype=np.uint32)
    y = np.array([1.0], dtype=np.float32)
    v = np.array([[42]], dtype=np.uint32)

    da_2d = xr.DataArray(v, dims=["x", "y"], coords={"x": x, "y": y})

    print(f"    Original x dtype: {da_2d.coords['x'].dtype}")
    print(f"    Original y dtype: {da_2d.coords['y'].dtype}")

    df_2d = da_2d.to_dataframe(name="v")

    x_dtype = df_2d.index.get_level_values("x").dtype
    y_dtype = df_2d.index.get_level_values("y").dtype

    print(f"    DataFrame x dtype: {x_dtype}")
    print(f"    DataFrame y dtype: {y_dtype}")

    # Check dtype preservation
    if x_dtype != np.uint32:
        print(f"    ❌ x coordinate dtype changed from uint32 to {x_dtype}")
        return False

    if y_dtype != np.float32:
        print(f"    ❌ y coordinate dtype changed from float32 to {y_dtype}")
        return False

    # Test case 2: 1D DataArray
    print("  📊 Testing 1D DataArray...")
    x_1d = np.array([1, 2, 3], dtype=np.uint32)
    v_1d = np.array([10, 20, 30], dtype=np.int32)

    da_1d = xr.DataArray(v_1d, dims=["x"], coords={"x": x_1d})

    print(f"    Original x dtype: {da_1d.coords['x'].dtype}")

    df_1d = da_1d.to_dataframe(name="v")
    x_1d_dtype = df_1d.index.dtype

    print(f"    DataFrame x dtype: {x_1d_dtype}")

    if x_1d_dtype != np.uint32:
        print(f"    ❌ 1D x coordinate dtype changed from uint32 to {x_1d_dtype}")
        return False

    print("  ✅ All dtype preservation tests passed!")
    return True


def show_versions() -> None:
    """Show version information for debugging."""
    print("📋 Version Information:")
    print(f"  Python: {sys.version}")
    print(f"  NumPy: {np.__version__}")
    print(f"  Pandas: {pd.__version__}")
    print(f"  xarray: {xr.__version__}")
    print()


def main() -> bool:
    """Main test function."""
    print("🔬 xarray to_dataframe() dtype preservation test")
    print("=" * 50)

    show_versions()

    try:
        success = test_to_dataframe_dtype_preservation()

        if success:
            print("\n🎉 Test PASSED - dtype preservation working correctly")
            return True
        else:
            print("\n💥 Test FAILED - dtype preservation regression detected")
            return False

    except Exception as e:
        print(f"\n💥 Test FAILED with exception: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
