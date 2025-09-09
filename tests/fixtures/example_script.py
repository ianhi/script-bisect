# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy@git+https://github.com/numpy/numpy.git@main",
# ]
# ///
"""
Example script demonstrating a potential regression in numpy.

This script would be used to test different numpy commits to find
when a specific behavior changed or broke.
"""

import numpy as np

def test_numpy_feature():
    """Test a numpy feature that might regress."""
    # Create a simple array
    arr = np.array([1, 2, 3, 4, 5])
    
    # Test some operations that might change behavior
    result = np.mean(arr)
    assert result == 3.0, f"Expected mean of 3.0, got {result}"
    
    # Test array creation with specific dtype
    typed_arr = np.array([1.1, 2.2, 3.3], dtype=np.float32)
    assert typed_arr.dtype == np.float32, f"Expected float32, got {typed_arr.dtype}"
    
    print("✅ All numpy tests passed!")
    return True

if __name__ == "__main__":
    test_numpy_feature()