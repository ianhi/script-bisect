# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray[complete]@git+https://github.com/pydata/xarray.git@main",
# ]
# ///
"""
Example bug report script for bisecting xarray issues.

This script demonstrates how to create a minimal reproducer for bisecting
package version issues. Replace the test logic with your actual bug reproduction.
"""

import sys
import xarray as xr
import numpy as np

def main():
    """Main test function that would demonstrate the bug."""
    print("🔍 Testing xarray functionality...")
    
    # Show version info for debugging
    print(f"Python version: {sys.version}")
    print("Xarray version info:")
    xr.show_versions()
    
    print("\n📊 Running reproducer test...")
    
    try:
        # Create sample data
        data = xr.Dataset({
            'temperature': (['time', 'location'], np.random.randn(365, 10)),
            'precipitation': (['time', 'location'], np.random.randn(365, 10))
        })
        
        # Test operation that might have regressed
        result = data.mean(dim='time')
        
        # Add your specific test here
        # For example, test a specific method or behavior
        assert result is not None, "Result should not be None"
        assert 'temperature' in result, "Temperature variable missing"
        
        print("✅ Test passed - no regression detected")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)