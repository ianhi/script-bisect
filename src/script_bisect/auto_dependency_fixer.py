"""Automatic dependency detection and fixing during bisection.

This module detects common import/dependency errors during test execution
and automatically fixes them by adding the missing dependencies to the
script's PEP 723 metadata, then re-runs the test.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

from rich.console import Console

console = Console()


class DependencyFix(NamedTuple):
    """Represents a dependency fix to apply."""

    package_name: str
    reason: str
    error_pattern: str


class AutoDependencyFixer:
    """Automatically detects and fixes missing dependencies during bisection."""

    def __init__(self, quiet_mode: bool = False) -> None:
        """Initialize the dependency fixer.

        Args:
            quiet_mode: If True, suppress console output during operation
        """
        self.quiet_mode = quiet_mode
        self._pending_messages: list[str] = []

    # General patterns for detecting missing dependencies
    GENERAL_PATTERNS = [
        # Standard import errors - captures package name from error
        (r"No module named ['\"]([^'\"]+)['\"]", "Import error"),
        (
            r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
            "Module not found",
        ),
        (r"ImportError: No module named ['\"]([^'\"]+)['\"]", "Import failure"),
        # Engine/backend not available patterns
        (r"unrecognized engine ['\"]([^'\"]+)['\"]", "Engine not available"),
        (r"engine ['\"]([^'\"]+)['\"] is not available", "Engine not available"),
        # Chunk manager patterns
        (
            r"chunk manager ['\"]([^'\"]+)['\"] is not available",
            "Chunk manager missing",
        ),
        # General "X is not installed" patterns
        (r"['\"]([^'\"]+)['\"] is not installed", "Package not installed"),
        (r"Please install ['\"]([^'\"]+)['\"]", "Installation required"),
    ]

    # Special cases where the detected name needs to be mapped to a different package
    PACKAGE_MAPPING = {
        # Common mismatches between import names and package names
        "netCDF4": "netcdf4",
        "cv2": "opencv-python",
        "PIL": "pillow",
        "sklearn": "scikit-learn",
        "yaml": "pyyaml",
        "dask": "dask[array]",  # Use array extras for xarray compatibility
    }

    # Domain-specific error interpreters - these translate application errors into missing dependencies
    DOMAIN_INTERPRETERS = [
        # xarray/backend engine errors -> missing backend packages
        (
            r"unrecognized engine ['\"]([^'\"]+)['\"]",
            r"\1",
            "Backend engine not available",
        ),
        (
            r"engine ['\"]([^'\"]+)['\"] is not available",
            r"\1",
            "Backend engine missing",
        ),
        # chunk manager errors -> dask variants
        (
            r"chunk manager ['\"]dask['\"] is not available",
            "dask[array]",
            "Dask array support needed",
        ),
        # matplotlib backend errors
        (
            r"backend ['\"]([^'\"]+)['\"] is not available",
            r"\1",
            "Backend not available",
        ),
    ]

    # Special error messages that need custom handling (not covered by general patterns)
    SPECIAL_CASES = [
        DependencyFix(
            package_name="cftime",
            reason="Required for non-standard calendar decoding in xarray/netCDF",
            error_pattern=r"The cftime package is required for working with non-standard calendars",
        ),
        # Add other special cases that can't be caught by general patterns
    ]

    def detect_missing_dependencies(self, error_output: str) -> list[DependencyFix]:
        """Detect missing dependencies from error output using general patterns and special cases.

        Args:
            error_output: Combined stdout/stderr from test execution

        Returns:
            List of dependency fixes to apply
        """
        fixes_needed = []
        detected_packages = set()  # Track to avoid duplicates

        # First, check special cases that need custom handling
        for fix in self.SPECIAL_CASES:
            if (
                re.search(fix.error_pattern, error_output, re.IGNORECASE)
                and fix.package_name not in detected_packages
            ):
                fixes_needed.append(fix)
                detected_packages.add(fix.package_name)

        # Then, use general patterns to detect other missing dependencies
        for pattern, reason_template in self.GENERAL_PATTERNS:
            matches = re.findall(pattern, error_output, re.IGNORECASE)
            for match in matches:
                # Clean up the matched package name
                package_name = match.strip().lower()

                # Apply package mapping if needed
                mapped_package = self.PACKAGE_MAPPING.get(match, package_name)

                if mapped_package not in detected_packages:
                    fix = DependencyFix(
                        package_name=mapped_package,
                        reason=f"{reason_template} for '{match}'",
                        error_pattern=pattern,  # Not used, just for completeness
                    )
                    fixes_needed.append(fix)
                    detected_packages.add(mapped_package)
                    self._print_or_queue(
                        f"[yellow]🔧 Detected missing dependency: {mapped_package}[/yellow]"
                    )
                    self._print_or_queue(f"[dim]   Reason: {fix.reason}[/dim]")

        # Finally, try domain-specific interpreters for application errors
        for pattern, package_template, reason_template in self.DOMAIN_INTERPRETERS:
            matches = re.findall(pattern, error_output, re.IGNORECASE)
            for match in matches:
                # Handle both static package names and regex substitution patterns
                if package_template.startswith("\\"):
                    # This is a regex substitution pattern like r"\1"
                    package_name = re.sub(
                        pattern, package_template, match, flags=re.IGNORECASE
                    )
                else:
                    # This is a static package name
                    package_name = package_template

                # Apply package mapping if needed
                package_name = self.PACKAGE_MAPPING.get(package_name, package_name)

                # Validate the package exists on PyPI before suggesting it
                if (
                    package_name not in detected_packages
                    and self._validate_package_exists(package_name)
                ):
                    fix = DependencyFix(
                        package_name=package_name,
                        reason=f"{reason_template} ('{match}')",
                        error_pattern=pattern,
                    )
                    fixes_needed.append(fix)
                    detected_packages.add(package_name)
                    self._print_or_queue(
                        f"[yellow]🔧 Detected missing dependency: {package_name}[/yellow]"
                    )
                    self._print_or_queue(f"[dim]   Reason: {fix.reason}[/dim]")

        return fixes_needed

    def _validate_package_exists(self, package_name: str) -> bool:
        """Validate that a package exists on PyPI before suggesting it.

        Args:
            package_name: Name of the package to validate (may include extras like 'dask[array]')

        Returns:
            True if the package exists, False otherwise
        """
        try:
            # Extract base package name (remove extras)
            base_package = package_name.split("[")[0]

            # Use pip index to check if package exists (fast and reliable)
            result = subprocess.run(
                ["uv", "pip", "index", base_package],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            # If validation fails, err on the side of caution and allow it
            # This prevents blocking legitimate packages due to network issues
            return True

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
            self._print_or_queue(
                "[red]❌ No PEP 723 metadata block found in script[/red]"
            )
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

        # Dependencies already shown in fix_and_retry message

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

        # Write the modified content back to the original file
        try:
            script_path.write_text("\n".join(new_lines), encoding="utf-8")
            # Script update message removed for cleaner output
            return script_path
        except OSError as e:
            self._print_or_queue(f"[red]❌ Failed to write to script: {e}[/red]")
            return script_path

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

        # Show consolidated dependency fix message
        dep_names = [fix.package_name for fix in fixes]
        self._print_or_queue(
            f"[cyan]🔧 Auto-fixing dependencies: {', '.join(dep_names)}[/cyan]"
        )

        self.apply_dependency_fixes(script_path, fixes)
        return script_path, True

    def _print_or_queue(self, message: str) -> None:
        """Print a message or queue it for later if in quiet mode."""
        if self.quiet_mode:
            self._pending_messages.append(message)
        else:
            console.print(message)

    def flush_messages(self) -> list[str]:
        """Return and clear all pending messages."""
        messages = self._pending_messages.copy()
        self._pending_messages.clear()
        return messages
