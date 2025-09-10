# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
#   "cloudpickle",
#   "s3fs",
#   "h5netcdf",
# ]
# ///
"""
Test script for xarray issue #10712: h5py objects cannot be pickled
https://github.com/pydata/xarray/issues/10712

This script demonstrates the regression where h5netcdf-backed datasets
opened via s3fs cannot be pickled. The issue was introduced between
v2025.07.1 and v2025.08.0.

Expected failing commit: ea9f02bbe6d3b02fbb56600710b2792795e0e4a5

Usage:
    script-bisect test_xarray_10712.py xarray v2025.07.1 v2025.08.0
"""

import sys


def test_h5netcdf_pickle_issue():
    """Test that h5netcdf datasets can be pickled after opening via s3fs."""
    print("🧪 Testing xarray h5netcdf pickling issue...")

    try:
        import cloudpickle
        import s3fs
        import xarray as xr

        print("  📦 Importing packages successful")

        # Open dataset via s3fs (the problematic case)
        s3 = s3fs.S3FileSystem(anon=True)
        fname = "s3://earthmover-sample-data/netcdf/tas_Amon_GFDL-ESM4_hist-piNTCF_r1i1p1f1_gr1.nc"

        print(f"  🌐 Opening S3 dataset: {fname}")
        ds = xr.open_dataset(s3.open(fname), engine="h5netcdf", chunks={})

        print(f"  📊 Dataset opened successfully: {ds.dims}")

        # Try to pickle and unpickle (this should fail in broken version)
        print("  🥒 Testing pickle/unpickle...")
        pickled_data = cloudpickle.dumps(ds)
        unpickled_ds = cloudpickle.loads(pickled_data)

        print("  ✅ Pickle/unpickle successful!")
        print(f"  📊 Unpickled dataset dims: {unpickled_ds.dims}")

        # Verify the data is the same
        if ds.dims == unpickled_ds.dims:
            print("  ✅ Dataset dimensions match after unpickling")
            return True
        else:
            print("  ❌ Dataset dimensions don't match after unpickling")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"  💥 Test failed with error: {error_msg}")
        print(f"  🔍 Error type: {type(e).__name__}")

        # Check if it's the expected h5py pickle error
        if "h5py objects cannot be pickled" in error_msg:
            print("  🎯 This is the expected h5py pickling error!")
        elif "cannot be pickled" in error_msg:
            print("  🎯 This is a pickling error!")
        elif "Failed to open" in error_msg:
            print("  🌐 This is a network/file access error!")

        # Show more error details for debugging
        import traceback

        print("  📍 Full traceback:")
        traceback.print_exc()

        return False


def show_version_info():
    """Show relevant version information."""
    import sys

    print("📋 Version Information:")
    print(f"  Python: {sys.version}")

    try:
        import xarray as xr

        print(f"  xarray: {xr.__version__}")
    except ImportError:
        print("  xarray: Not available")

    try:
        import cloudpickle

        print(f"  cloudpickle: {cloudpickle.__version__}")
    except (ImportError, AttributeError):
        print("  cloudpickle: Version unknown")

    try:
        import s3fs

        print(f"  s3fs: {s3fs.__version__}")
    except (ImportError, AttributeError):
        print("  s3fs: Version unknown")

    try:
        import h5netcdf

        print(f"  h5netcdf: {h5netcdf.__version__}")
    except (ImportError, AttributeError):
        print("  h5netcdf: Version unknown")

    print()


def main():
    """Main test function."""
    print("🔬 xarray h5netcdf pickling test (issue #10712)")
    print("=" * 60)

    show_version_info()

    try:
        success = test_h5netcdf_pickle_issue()

        if success:
            print("\n🎉 Test PASSED - h5netcdf datasets can be pickled")
            return True
        else:
            print(
                "\n💥 Test FAILED - h5netcdf datasets cannot be pickled (regression detected)"
            )
            return False

    except Exception as e:
        print(f"\n💥 Test FAILED with unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
