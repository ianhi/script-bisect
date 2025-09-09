"""Tests for utility functions."""

from __future__ import annotations

import tempfile
from pathlib import Path

from script_bisect.utils import (
    create_temp_dir,
    extract_package_name,
    format_commit_info,
    safe_filename,
)


class TestUtils:
    """Tests for utility functions."""
    
    def test_extract_package_name_simple(self) -> None:
        """Test extracting package names from simple dependencies."""
        assert extract_package_name("requests") == "requests"
        assert extract_package_name("numpy") == "numpy"
    
    def test_extract_package_name_with_version(self) -> None:
        """Test extracting package names with version specifiers."""
        assert extract_package_name("requests>=2.0") == "requests"
        assert extract_package_name("numpy<=1.21.0") == "numpy"
        assert extract_package_name("pandas==1.5.0") == "pandas"
        assert extract_package_name("scipy>1.0") == "scipy"
        assert extract_package_name("matplotlib<3.0") == "matplotlib"
        assert extract_package_name("seaborn~=0.11") == "seaborn"
        assert extract_package_name("scikit-learn!=1.0.0") == "scikit-learn"
    
    def test_extract_package_name_with_extras(self) -> None:
        """Test extracting package names with extras."""
        assert extract_package_name("requests[security]") == "requests"
        assert extract_package_name("pandas[performance,test]") == "pandas"
        assert extract_package_name("xarray[complete]>=2024.1") == "xarray"
    
    def test_extract_package_name_git_dependencies(self) -> None:
        """Test extracting package names from git dependencies."""
        assert extract_package_name("requests@git+https://github.com/psf/requests") == "requests"
        assert extract_package_name("xarray[complete]@git+https://github.com/pydata/xarray.git@main") == "xarray"
        assert extract_package_name("numpy@git+https://github.com/numpy/numpy@v1.24.0") == "numpy"
    
    def test_extract_package_name_complex(self) -> None:
        """Test extracting package names from complex dependency specifications."""
        assert extract_package_name("requests>=2.0,<3.0") == "requests"
        assert extract_package_name("pandas[performance]>=1.5.0;python_version>='3.8'") == "pandas"
    
    def test_safe_filename(self) -> None:
        """Test creating safe filenames."""
        assert safe_filename("hello-world") == "hello-world"
        assert safe_filename("test_file.py") == "test_file.py"
        assert safe_filename("my file name") == "my_file_name"
        assert safe_filename("file/with/slashes") == "file_with_slashes"
        assert safe_filename("special!@#$chars") == "special____chars"
        assert safe_filename("unicode-café") == "unicode-caf_"
    
    def test_create_temp_dir(self) -> None:
        """Test creating temporary directories."""
        temp_dir = create_temp_dir()
        
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "script_bisect_" in temp_dir.name
        
        # Clean up
        temp_dir.rmdir()
    
    def test_create_temp_dir_with_prefix(self) -> None:
        """Test creating temporary directories with custom prefix."""
        temp_dir = create_temp_dir("custom_prefix_")
        
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "custom_prefix_" in temp_dir.name
        
        # Clean up
        temp_dir.rmdir()
    
    def test_format_commit_info(self) -> None:
        """Test formatting commit information."""
        commit_info = format_commit_info(
            commit_hash="abc123def456789",
            author="John Doe <john@example.com>",
            date="2024-01-15 10:30:00",
            message="Fix critical bug in parser"
        )
        
        expected = (
            "Commit: abc123def456...\n"
            "Author: John Doe <john@example.com>\n"
            "Date: 2024-01-15 10:30:00\n"
            "Message: Fix critical bug in parser"
        )
        
        assert commit_info == expected