"""Tests for the PEP 723 metadata parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from script_bisect.exceptions import ParseError
from script_bisect.parser import ScriptParser

if TYPE_CHECKING:
    from pathlib import Path


class TestScriptParser:
    """Tests for the ScriptParser class."""

    def test_valid_script_parsing(self, tmp_path: Path) -> None:
        """Test parsing a valid PEP 723 script."""
        script_content = """# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.0",
#   "rich",
# ]
# ///

import requests
print("Hello world")
"""
        script_path = tmp_path / "test_script.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        assert parser.has_package("requests")
        assert parser.has_package("rich")
        assert not parser.has_package("nonexistent")

        available = parser.get_available_packages()
        assert "requests" in available
        assert "rich" in available
        assert len(available) == 2

    def test_git_dependency_parsing(self, tmp_path: Path) -> None:
        """Test parsing scripts with git dependencies."""
        script_content = """# /// script
# dependencies = [
#   "xarray[complete]@git+https://github.com/pydata/xarray.git@main",
# ]
# ///

import xarray as xr
xr.show_versions()
"""
        script_path = tmp_path / "git_script.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        assert parser.has_package("xarray")

        # Test repository URL extraction
        repo_url = parser.get_repository_url("xarray")
        assert repo_url == "git+https://github.com/pydata/xarray.git"

    def test_update_git_reference(self, tmp_path: Path) -> None:
        """Test updating git references in dependencies."""
        script_content = """# /// script
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
# ]
# ///

import xarray as xr
print("Testing xarray")
"""
        script_path = tmp_path / "update_script.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        # Update to a specific commit
        new_commit = "abc123def456"
        updated_content = parser.update_git_reference(
            "xarray", "git+https://github.com/pydata/xarray.git", new_commit
        )

        assert f"@{new_commit}" in updated_content
        assert "@main" not in updated_content

        # Verify the rest of the script is unchanged
        assert "import xarray as xr" in updated_content
        assert 'print("Testing xarray")' in updated_content

    def test_update_git_reference_with_extras(self, tmp_path: Path) -> None:
        """Test updating git references with package extras."""
        script_content = """# /// script
# dependencies = [
#   "xarray[complete,dev]@git+https://github.com/pydata/xarray.git@main",
# ]
# ///
"""
        script_path = tmp_path / "extras_script.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        new_commit = "xyz789"
        updated_content = parser.update_git_reference(
            "xarray", "git+https://github.com/pydata/xarray.git", new_commit
        )

        # Should preserve extras
        assert "xarray[complete,dev]@" in updated_content
        assert f"@{new_commit}" in updated_content

    def test_missing_metadata_block(self, tmp_path: Path) -> None:
        """Test handling scripts without PEP 723 metadata."""
        script_content = """
import requests
print("No metadata here")
"""
        script_path = tmp_path / "no_metadata.py"
        script_path.write_text(script_content)

        with pytest.raises(ParseError, match="No PEP 723 script metadata block found"):
            ScriptParser(script_path)

    def test_invalid_toml_metadata(self, tmp_path: Path) -> None:
        """Test handling invalid TOML in metadata."""
        script_content = """# /// script
# dependencies = [
#   "requests>=2.0
# invalid toml here
# ///
"""
        script_path = tmp_path / "invalid_toml.py"
        script_path.write_text(script_content)

        with pytest.raises(ParseError, match="Invalid TOML in metadata"):
            ScriptParser(script_path)

    def test_malformed_metadata_lines(self, tmp_path: Path) -> None:
        """Test handling malformed metadata lines."""
        script_content = """# /// script
# dependencies = ["requests"]
not a comment line
# ///
"""
        script_path = tmp_path / "malformed.py"
        script_path.write_text(script_content)

        with pytest.raises(ParseError, match="Invalid metadata line"):
            ScriptParser(script_path)

    def test_package_not_found_update(self, tmp_path: Path) -> None:
        """Test updating a package that doesn't exist in dependencies."""
        script_content = """# /// script
# dependencies = ["requests"]
# ///
"""
        script_path = tmp_path / "missing_pkg.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        with pytest.raises(ParseError, match="Package 'nonexistent' not found"):
            parser.update_git_reference(
                "nonexistent", "git+https://github.com/example/repo.git", "main"
            )

    def test_validation_warnings(self, tmp_path: Path) -> None:
        """Test metadata validation warnings."""
        # Script without dependencies
        script_content = """# /// script
# requires-python = ">=3.11"
# ///
"""
        script_path = tmp_path / "no_deps.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)
        warnings = parser.validate_metadata()

        assert any("No 'dependencies' field found" in w for w in warnings)

    def test_dependency_spec_extraction(self, tmp_path: Path) -> None:
        """Test extracting full dependency specifications."""
        script_content = """# /// script
# dependencies = [
#   "requests>=2.0,<3.0",
#   "rich~=13.0",
# ]
# ///
"""
        script_path = tmp_path / "deps_spec.py"
        script_path.write_text(script_content)

        parser = ScriptParser(script_path)

        requests_spec = parser.get_dependency_spec("requests")
        assert requests_spec == "requests>=2.0,<3.0"

        rich_spec = parser.get_dependency_spec("rich")
        assert rich_spec == "rich~=13.0"

        nonexistent_spec = parser.get_dependency_spec("nonexistent")
        assert nonexistent_spec is None
