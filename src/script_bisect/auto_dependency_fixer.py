"""Automatic dependency detection and fixing during bisection.

This module detects common import/dependency errors during test execution
and automatically fixes them by adding the missing dependencies to the
script's PEP 723 metadata, then re-runs the test.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import NamedTuple

from rich.console import Console

console = Console()


class DependencyFix(NamedTuple):
    """Represents a dependency fix to apply."""

    package_name: str
    reason: str
    error_pattern: str


class AutoDependencyFixer:
    """Automatically detects and fixes missing dependencies during bisection."""

    # Common dependency fixes based on error patterns
    DEPENDENCY_FIXES = [
        DependencyFix(
            package_name="cftime",
            reason="Required for non-standard calendar decoding in xarray/netCDF",
            error_pattern=r"The cftime package is required for working with non-standard calendars",
        ),
        DependencyFix(
            package_name="dask[array]",
            reason="Required for chunked array operations",
            error_pattern=r"chunk manager 'dask' is not available",
        ),
        DependencyFix(
            package_name="dask[array]",
            reason="Required for chunked array operations",
            error_pattern=r"make sure 'dask' is installed",
        ),
        DependencyFix(
            package_name="netcdf4",
            reason="Required for NetCDF4 backend",
            error_pattern=r"No module named 'netCDF4'",
        ),
        DependencyFix(
            package_name="scipy",
            reason="Required for scipy backend in xarray",
            error_pattern=r"No module named 'scipy'",
        ),
        DependencyFix(
            package_name="matplotlib",
            reason="Required for plotting functionality",
            error_pattern=r"No module named 'matplotlib'",
        ),
        DependencyFix(
            package_name="seaborn",
            reason="Required for statistical plotting",
            error_pattern=r"No module named 'seaborn'",
        ),
        DependencyFix(
            package_name="zarr",
            reason="Required for Zarr array storage",
            error_pattern=r"No module named 'zarr'",
        ),
        DependencyFix(
            package_name="fsspec",
            reason="Required for file system operations",
            error_pattern=r"No module named 'fsspec'",
        ),
        DependencyFix(
            package_name="h5py",
            reason="Required for HDF5 operations",
            error_pattern=r"No module named 'h5py'",
        ),
        DependencyFix(
            package_name="bottleneck",
            reason="Required for optimized array operations",
            error_pattern=r"No module named 'bottleneck'",
        ),
        DependencyFix(
            package_name="numbagg",
            reason="Required for numba-accelerated operations",
            error_pattern=r"No module named 'numbagg'",
        ),
    ]

    def detect_missing_dependencies(self, error_output: str) -> list[DependencyFix]:
        """Detect missing dependencies from error output.

        Args:
            error_output: Combined stdout/stderr from test execution

        Returns:
            List of dependency fixes to apply
        """
        fixes_needed = []

        for fix in self.DEPENDENCY_FIXES:
            if re.search(fix.error_pattern, error_output, re.IGNORECASE):
                fixes_needed.append(fix)
                console.print(
                    f"[yellow]🔧 Detected missing dependency: {fix.package_name}[/yellow]"
                )
                console.print(f"[dim]   Reason: {fix.reason}[/dim]")

        return fixes_needed

    def apply_dependency_fixes(
        self, script_path: Path, fixes: list[DependencyFix]
    ) -> Path:
        """Apply dependency fixes to a script by modifying its PEP 723 metadata.

        Args:
            script_path: Path to the script to fix
            fixes: List of dependency fixes to apply

        Returns:
            Path to the modified script (may be a temporary file)
        """
        if not fixes:
            return script_path

        # Read the original script
        content = script_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find the PEP 723 metadata block
        metadata_start = None
        metadata_end = None
        dependencies_line = None

        for i, line in enumerate(lines):
            if line.strip() == "# /// script":
                metadata_start = i
            elif line.strip() == "# ///":
                metadata_end = i
                break
            elif metadata_start is not None and line.strip().startswith(
                "# dependencies = ["
            ):
                dependencies_line = i

        if metadata_start is None or metadata_end is None:
            console.print("[red]❌ No PEP 723 metadata block found in script[/red]")
            return script_path

        # Extract existing dependencies
        existing_deps = []
        if dependencies_line is not None:
            deps_content = []
            i = dependencies_line
            while i <= metadata_end:
                line = lines[i]
                deps_content.append(line)
                if "]" in line:
                    break
                i += 1

            # Parse existing dependencies
            deps_text = " ".join(deps_content)
            match = re.search(r"\[(.*?)\]", deps_text, re.DOTALL)
            if match:
                deps_str = match.group(1)
                # Extract quoted dependency strings
                existing_deps = re.findall(r'"([^"]*)"', deps_str)

        # Add new dependencies (deduplicate)
        new_deps = list({fix.package_name for fix in fixes})
        all_deps = existing_deps + [dep for dep in new_deps if dep not in existing_deps]

        console.print(f"[green]📦 Adding dependencies: {', '.join(new_deps)}[/green]")

        # Create new dependencies block
        deps_lines = ["# dependencies = ["]
        for i, dep in enumerate(all_deps):
            comma = "," if i < len(all_deps) - 1 else ""
            deps_lines.append(f'#   "{dep}"{comma}')
        deps_lines.append("# ]")

        # Replace or add dependencies in metadata block
        new_lines = lines[
            : metadata_start + 2
        ]  # Keep script marker and requires-python

        # Skip old dependencies if they exist
        skip_until = metadata_start + 2
        if dependencies_line is not None:
            # Find end of existing dependencies block
            i = dependencies_line
            while i <= metadata_end:
                if "]" in lines[i]:
                    skip_until = i + 1
                    break
                i += 1

        # Add new dependencies
        new_lines.extend(deps_lines)

        # Add rest of metadata and script content
        new_lines.extend(lines[skip_until:])

        # Create temporary file with fixed dependencies
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("\n".join(new_lines))
            fixed_script_path = Path(f.name)

        console.print(
            f"[green]✅ Created fixed script: {fixed_script_path.name}[/green]"
        )
        return fixed_script_path

    def should_retry_with_fixes(self, error_output: str) -> bool:
        """Check if the error output indicates we should retry with dependency fixes.

        Args:
            error_output: Combined stdout/stderr from test execution

        Returns:
            True if we should retry with fixes, False otherwise
        """
        return len(self.detect_missing_dependencies(error_output)) > 0

    def fix_and_retry(
        self, script_path: Path, error_output: str
    ) -> tuple[Path | None, bool]:
        """Detect dependency issues and create a fixed script for retry.

        Args:
            script_path: Original script path
            error_output: Error output from failed test

        Returns:
            Tuple of (fixed_script_path, should_retry)
            fixed_script_path is None if no fixes were applied
        """
        fixes = self.detect_missing_dependencies(error_output)

        if not fixes:
            return None, False

        console.print(
            f"[cyan]🔄 Attempting to fix {len(fixes)} dependency issue(s)...[/cyan]"
        )

        fixed_script = self.apply_dependency_fixes(script_path, fixes)

        if fixed_script != script_path:
            console.print("[cyan]🔄 Re-running test with fixed dependencies...[/cyan]")
            return fixed_script, True

        return None, False

    def cleanup_temp_script(
        self, script_path: Path, original_script_path: Path
    ) -> None:
        """Clean up temporary script if it's not the original.

        Args:
            script_path: Path to potentially temporary script
            original_script_path: Path to original script
        """
        if script_path != original_script_path and script_path.exists():
            try:
                script_path.unlink()
                console.print(
                    f"[dim]🗑️ Cleaned up temporary script: {script_path.name}[/dim]"
                )
            except OSError:
                console.print(
                    f"[yellow]⚠️ Could not remove temporary script: {script_path}[/yellow]"
                )
