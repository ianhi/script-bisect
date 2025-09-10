"""Tests for the AutoDependencyFixer module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from script_bisect.auto_dependency_fixer import AutoDependencyFixer, DependencyFix


class TestAutoDependencyFixer:
    """Test cases for AutoDependencyFixer."""

    def test_special_case_detection_cftime(self):
        """Test detection of special case cftime dependency."""
        fixer = AutoDependencyFixer()

        error_output = """
        Traceback (most recent call last):
          File "test.py", line 42, in test_function
            ds = xr.open_dataset(filename, engine="h5netcdf")
          File "/path/to/xarray/coding/times.py", line 545, in decode_cf_datetime
            dates = _decode_datetime_with_pandas(
                flat_num_dates, units, calendar, time_units
        ValueError: The cftime package is required for working with non-standard calendars
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        assert len(fixes) == 1
        assert fixes[0].package_name == "cftime"
        assert "non-standard calendar" in fixes[0].reason

    def test_general_pattern_import_errors(self):
        """Test detection of standard import errors using general patterns."""
        fixer = AutoDependencyFixer()

        error_output = """
        ModuleNotFoundError: No module named 'scipy'
        ImportError: No module named 'matplotlib'
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        package_names = [fix.package_name for fix in fixes]
        assert "scipy" in package_names
        assert "matplotlib" in package_names
        assert len(fixes) == 2

    def test_package_mapping_netcdf4(self):
        """Test that package mapping works correctly."""
        fixer = AutoDependencyFixer()

        error_output = """
        ImportError: No module named 'netCDF4'
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        assert len(fixes) == 1
        assert fixes[0].package_name == "netcdf4"  # Mapped from netCDF4

    def test_domain_interpreter_engine_errors(self):
        """Test domain-specific interpreter for xarray engine errors."""
        fixer = AutoDependencyFixer()

        error_output = """
        ValueError: unrecognized engine 'h5netcdf' must be one of your available engines
        """

        with patch.object(fixer, '_validate_package_exists', return_value=True):
            fixes = fixer.detect_missing_dependencies(error_output)

        assert len(fixes) == 1
        assert fixes[0].package_name == "h5netcdf"
        assert "Engine not available" in fixes[0].reason

    def test_domain_interpreter_dask_chunk_manager(self):
        """Test domain-specific interpreter for dask chunk manager errors."""
        fixer = AutoDependencyFixer()

        error_output = """
        ImportError: chunk manager 'dask' is not available. Please make sure 'dask' is installed and importable.
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        # Should detect both from general pattern and domain interpreter
        dask_fixes = [f for f in fixes if "dask" in f.package_name.lower()]
        assert len(dask_fixes) >= 1
        assert any(fix.package_name == "dask[array]" for fix in dask_fixes)

    @patch('subprocess.run')
    def test_package_validation_success(self, mock_run):
        """Test that package validation works when package exists."""
        mock_run.return_value = Mock(returncode=0)

        fixer = AutoDependencyFixer()
        assert fixer._validate_package_exists("numpy") is True

        mock_run.assert_called_once_with(
            ["uv", "pip", "index", "numpy"],
            capture_output=True,
            text=True,
            timeout=10
        )

    @patch('subprocess.run')
    def test_package_validation_failure(self, mock_run):
        """Test that package validation fails when package doesn't exist."""
        mock_run.return_value = Mock(returncode=1)

        fixer = AutoDependencyFixer()
        assert fixer._validate_package_exists("nonexistent-package") is False

    @patch('subprocess.run')
    def test_package_validation_timeout_fallback(self, mock_run):
        """Test that validation falls back to True on timeout/error."""
        mock_run.side_effect = subprocess.TimeoutExpired(["uv"], 10)

        fixer = AutoDependencyFixer()
        assert fixer._validate_package_exists("some-package") is True

    def test_package_validation_with_extras(self):
        """Test package validation correctly handles extras."""
        fixer = AutoDependencyFixer()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Should extract base package name
            result = fixer._validate_package_exists("dask[array]")

            assert result is True
            # Should have been called with just the base name
            mock_run.assert_called_once_with(
                ["uv", "pip", "index", "dask"],  # extras stripped
                capture_output=True,
                text=True,
                timeout=10
            )

    def test_no_dependencies_detected(self):
        """Test that no dependencies are detected from unrelated errors."""
        fixer = AutoDependencyFixer()

        error_output = """
        Traceback (most recent call last):
          File "test.py", line 10, in test_function
            result = some_function()
        ValueError: Invalid input data
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        assert len(fixes) == 0

    def test_deduplication_of_dependencies(self):
        """Test that duplicate dependencies are properly deduplicated."""
        fixer = AutoDependencyFixer()

        # Error output that could match multiple patterns for the same package
        error_output = """
        ImportError: No module named 'scipy'
        ModuleNotFoundError: No module named 'scipy'
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        # Should only detect scipy once despite multiple matches
        scipy_fixes = [f for f in fixes if f.package_name == "scipy"]
        assert len(scipy_fixes) == 1

    def test_complex_mixed_errors(self):
        """Test detection of mixed error types in complex output."""
        fixer = AutoDependencyFixer()

        error_output = """
        Traceback (most recent call last):
          File "script.py", line 10, in <module>
            import scipy
        ModuleNotFoundError: No module named 'scipy'

        Later in execution:
        ValueError: unrecognized engine 'h5netcdf' must be one of ['netcdf4', 'h5py']

        Also:
        ImportError: chunk manager 'dask' is not available. Please install dask.

        And finally:
        ValueError: The cftime package is required for working with non-standard calendars
        """

        with patch.object(fixer, '_validate_package_exists', return_value=True):
            fixes = fixer.detect_missing_dependencies(error_output)

        package_names = [fix.package_name for fix in fixes]

        # Should detect all different types of errors
        assert "scipy" in package_names  # Standard import error
        assert "h5netcdf" in package_names  # Domain interpreter
        assert "cftime" in package_names  # Special case
        # Dask might appear as either "dask" or "dask[array]" depending on pattern match order
        assert any("dask" in pkg for pkg in package_names)

    def test_apply_dependency_fixes_adds_to_existing(self):
        """Test that dependency fixes are added to existing dependencies."""
        fixer = AutoDependencyFixer()

        # Create a temporary script with existing dependencies
        script_content = '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=1.21",
#   "pandas>=1.3",
# ]
# ///
"""Test script"""

import numpy as np
import pandas as pd

def main():
    print("Hello world")

if __name__ == "__main__":
    main()
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            # Create some dependency fixes
            fixes = [
                DependencyFix("cftime", "Required for calendar decoding", "cftime pattern"),
                DependencyFix("dask[array]", "Required for chunks", "dask pattern")
            ]

            # Apply the fixes
            result_path = fixer.apply_dependency_fixes(script_path, fixes)

            # Check that the original script was modified
            assert result_path == script_path

            # Read the modified content
            modified_content = script_path.read_text(encoding='utf-8')

            # Verify dependencies were added
            assert "cftime" in modified_content
            assert "dask[array]" in modified_content
            assert "numpy>=1.21" in modified_content  # Original dependencies preserved
            assert "pandas>=1.3" in modified_content

        finally:
            # Clean up
            script_path.unlink()

    def test_apply_dependency_fixes_creates_new_block(self):
        """Test that dependency fixes create a new dependencies block if none exists."""
        fixer = AutoDependencyFixer()

        # Create a temporary script without dependencies
        script_content = '''# /// script
# requires-python = ">=3.11"
# ///
"""Test script"""

def main():
    print("Hello world")

if __name__ == "__main__":
    main()
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            # Create some dependency fixes
            fixes = [
                DependencyFix("cftime", "Required for calendar decoding", "cftime pattern")
            ]

            # Apply the fixes
            result_path = fixer.apply_dependency_fixes(script_path, fixes)

            # Check that the original script was modified
            assert result_path == script_path

            # Read the modified content
            modified_content = script_path.read_text(encoding='utf-8')

            # Verify dependencies were added
            assert "cftime" in modified_content
            assert "dependencies = [" in modified_content

        finally:
            # Clean up
            script_path.unlink()

    def test_fix_and_retry_integration(self):
        """Test the complete fix_and_retry workflow."""
        fixer = AutoDependencyFixer()

        # Create a temporary script
        script_content = '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray",
# ]
# ///
"""Test script"""

import xarray as xr

def main():
    print("Hello world")

if __name__ == "__main__":
    main()
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            # Simulate error output that should trigger cftime fix
            error_output = "ValueError: The cftime package is required for working with non-standard calendars"

            # Test fix_and_retry
            fixed_path, should_retry = fixer.fix_and_retry(script_path, error_output)

            assert should_retry is True
            assert fixed_path == script_path

            # Verify the dependency was added
            modified_content = script_path.read_text(encoding='utf-8')
            assert "cftime" in modified_content

        finally:
            # Clean up
            script_path.unlink()

    def test_should_retry_with_fixes_detection(self):
        """Test should_retry_with_fixes correctly identifies fixable errors."""
        fixer = AutoDependencyFixer()

        # Error that should trigger retry
        cftime_error = "ValueError: The cftime package is required for working with non-standard calendars"
        assert fixer.should_retry_with_fixes(cftime_error) is True

        # Error that should not trigger retry
        unrelated_error = "ValueError: Invalid input data format"
        assert fixer.should_retry_with_fixes(unrelated_error) is False

    def test_apply_fixes_deduplication(self):
        """Test that duplicate dependencies are deduplicated when applying fixes."""
        fixer = AutoDependencyFixer()

        # Create error output that would match multiple dask patterns
        error_output = """
        ImportError: chunk manager 'dask' is not available. Please make sure 'dask' is installed and importable.
        """

        fixes = fixer.detect_missing_dependencies(error_output)

        # Should detect multiple fixes but they should be deduplicated when applied
        script_content = '''# /// script
# requires-python = ">=3.11"
# ///
"""Test script"""
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            fixer.apply_dependency_fixes(script_path, fixes)
            modified_content = script_path.read_text(encoding='utf-8')

            # Should only have one occurrence of dask[array]
            assert modified_content.count('"dask[array]"') == 1

        finally:
            script_path.unlink()
