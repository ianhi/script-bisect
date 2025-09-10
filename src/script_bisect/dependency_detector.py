"""Automatic dependency detection from Python scripts."""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from typing import Any

from rich.console import Console

from .exceptions import ScriptBisectError

console = Console()


@dataclass
class DetectedDependency:
    """Represents a detected dependency."""

    package_name: str
    import_name: str
    is_standard_library: bool = False
    confidence: float = 1.0
    source_line: str = ""


class DependencyDetector:
    """Detects dependencies from Python source code."""

    def __init__(self) -> None:
        """Initialize the dependency detector."""
        # Import the dependency mappings from the separate module
        from .dependency_mappings import IMPORT_TO_PACKAGE, STANDARD_LIBRARY

        self.import_to_package = IMPORT_TO_PACKAGE
        self.standard_library = STANDARD_LIBRARY

    def detect_dependencies(self, source_code: str) -> list[DetectedDependency]:
        """Detect dependencies from Python source code.

        Args:
            source_code: Python source code to analyze

        Returns:
            List of detected dependencies

        Raises:
            ScriptBisectError: If source code cannot be parsed
        """
        console.print("[dim]🔍 Analyzing dependencies...[/dim]")

        dependencies = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ScriptBisectError(f"Invalid Python syntax: {e}") from e

        # Collect import statements
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dep = self._process_import(alias.name, f"import {alias.name}")
                    if dep:
                        dependencies.append(dep)

            elif isinstance(node, ast.ImportFrom) and node.module:
                dep = self._process_import(
                    node.module, f"from {node.module} import ..."
                )
                if dep:
                    dependencies.append(dep)

        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        for dep in dependencies:
            key = (dep.package_name, dep.import_name)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        console.print(f"[green]✅ Detected {len(unique_deps)} dependencies[/green]")
        return unique_deps

    def _process_import(
        self, import_name: str, source_line: str
    ) -> DetectedDependency | None:
        """Process a single import statement.

        Args:
            import_name: The imported module name
            source_line: The original source line

        Returns:
            DetectedDependency if it's a third-party package, None if standard library
        """
        # Get the top-level package name
        top_level = import_name.split(".")[0]

        # Check if it's a standard library module
        if top_level in self.standard_library:
            return DetectedDependency(
                package_name=top_level,
                import_name=import_name,
                is_standard_library=True,
                source_line=source_line,
            )

        # Map import name to package name if known
        package_name = self.import_to_package.get(top_level, top_level)

        # Calculate confidence based on our knowledge
        confidence = 1.0 if top_level in self.import_to_package else 0.7

        return DetectedDependency(
            package_name=package_name,
            import_name=import_name,
            is_standard_library=False,
            confidence=confidence,
            source_line=source_line,
        )

    def verify_packages_exist(
        self, dependencies: list[DetectedDependency]
    ) -> list[DetectedDependency]:
        """Verify that packages exist on PyPI.

        Args:
            dependencies: List of dependencies to verify

        Returns:
            List of verified dependencies (may be modified with corrected names)
        """
        console.print("[dim]🔍 Verifying packages on PyPI...[/dim]")

        verified = []

        for dep in dependencies:
            if dep.is_standard_library:
                verified.append(dep)
                continue

            # Try to verify the package exists
            if self._package_exists_on_pypi(dep.package_name):
                verified.append(dep)
            else:
                # Try some common variations
                variations = [
                    dep.package_name.lower(),
                    dep.package_name.upper(),
                    dep.package_name.replace("-", "_"),
                    dep.package_name.replace("_", "-"),
                ]

                found = False
                for variation in variations:
                    if variation != dep.package_name and self._package_exists_on_pypi(
                        variation
                    ):
                        console.print(
                            f"[yellow]📦 Corrected package name: {dep.package_name} → {variation}[/yellow]"
                        )
                        dep.package_name = variation
                        dep.confidence = 0.9
                        verified.append(dep)
                        found = True
                        break

                if not found:
                    console.print(
                        f"[red]⚠️ Could not verify package: {dep.package_name}[/red]"
                    )
                    dep.confidence = 0.3
                    verified.append(dep)  # Keep it but with low confidence

        return verified

    def _package_exists_on_pypi(self, package_name: str) -> bool:
        """Check if a package exists on PyPI.

        Args:
            package_name: Name of the package to check

        Returns:
            True if the package exists on PyPI
        """
        try:
            # Use pip to check if package exists (faster than PyPI API)
            result = subprocess.run(
                ["pip", "index", "versions", package_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return (
                result.returncode == 0
                and "No matching distribution found" not in result.stdout
            )
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            # Fallback: assume it exists if we can't verify
            return True

    def generate_pep723_metadata(
        self, dependencies: list[DetectedDependency], requires_python: str = ">=3.12"
    ) -> dict[str, Any]:
        """Generate PEP 723 metadata from detected dependencies.

        Args:
            dependencies: List of detected dependencies
            requires_python: Python version requirement

        Returns:
            Dictionary containing PEP 723 metadata
        """
        # Filter out standard library dependencies
        external_deps = [dep for dep in dependencies if not dep.is_standard_library]

        # Sort by confidence and package name
        external_deps.sort(key=lambda x: (-x.confidence, x.package_name))

        metadata = {
            "requires-python": requires_python,
            "dependencies": [dep.package_name for dep in external_deps],
        }

        return metadata

    def format_pep723_block(self, metadata: dict[str, Any]) -> str:
        """Format PEP 723 metadata as a comment block.

        Args:
            metadata: Metadata dictionary

        Returns:
            Formatted PEP 723 comment block
        """
        lines = ["# /// script"]

        # Add requires-python
        if "requires-python" in metadata:
            lines.append(f"# requires-python = \"{metadata['requires-python']}\"")

        # Add dependencies
        if "dependencies" in metadata and metadata["dependencies"]:
            deps_str = ", ".join(f'"{dep}"' for dep in metadata["dependencies"])
            lines.append(f"# dependencies = [{deps_str}]")

        lines.append("# ///")

        return "\n".join(lines)
