"""Script generation with automatic PEP 723 metadata."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from .dependency_detector import DependencyDetector

if TYPE_CHECKING:
    from .issue_importer import CodeBlock

console = Console()


class ScriptGenerator:
    """Generates complete Python scripts with PEP 723 metadata."""

    def __init__(self) -> None:
        """Initialize the script generator."""
        self.dependency_detector = DependencyDetector()

    def generate_script_from_code_block(
        self,
        code_block: CodeBlock,
        requires_python: str = ">=3.12",
        additional_dependencies: list[str] | None = None,
    ) -> str:
        """Generate a complete Python script with PEP 723 metadata.

        Args:
            code_block: CodeBlock containing the source code
            requires_python: Python version requirement
            additional_dependencies: Additional dependencies to include

        Returns:
            Complete Python script with PEP 723 metadata block
        """
        console.print("[dim]🔧 Generating script with PEP 723 metadata...[/dim]")

        # Detect dependencies from the code
        detected_deps = self.dependency_detector.detect_dependencies(code_block.content)

        # Verify packages exist on PyPI
        verified_deps = self.dependency_detector.verify_packages_exist(detected_deps)

        # Build dependency list
        dependency_names = [
            dep.package_name for dep in verified_deps if not dep.is_standard_library
        ]

        # Add any additional dependencies
        if additional_dependencies:
            for dep in additional_dependencies:
                if dep not in dependency_names:
                    dependency_names.append(dep)

        # Generate metadata
        metadata = self.dependency_detector.generate_pep723_metadata(
            verified_deps, requires_python
        )

        # Add any additional dependencies to metadata
        if additional_dependencies:
            existing_deps = set(metadata.get("dependencies", []))
            for dep in additional_dependencies:
                existing_deps.add(dep)
            metadata["dependencies"] = sorted(existing_deps)

        # Format the PEP 723 block
        pep723_block = self.dependency_detector.format_pep723_block(metadata)

        # Combine metadata and code
        script_parts = [
            pep723_block,
            "",  # Empty line after metadata
            code_block.content,
        ]

        complete_script = "\n".join(script_parts)

        # Report what was detected
        if dependency_names:
            console.print(
                f"[green]✅ Detected dependencies: {', '.join(dependency_names)}[/green]"
            )
        else:
            console.print("[yellow]⚠️ No external dependencies detected[/yellow]")

        return complete_script

    def create_temporary_script(
        self,
        code_block: CodeBlock,
        requires_python: str = ">=3.12",
        additional_dependencies: list[str] | None = None,
        suffix: str = ".py",
    ) -> Path:
        """Create a temporary script file with PEP 723 metadata.

        Args:
            code_block: CodeBlock containing the source code
            requires_python: Python version requirement
            additional_dependencies: Additional dependencies to include
            suffix: File suffix (default: .py)

        Returns:
            Path to the created temporary script file
        """
        script_content = self.generate_script_from_code_block(
            code_block, requires_python, additional_dependencies
        )

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
            mode="w",
            suffix=suffix,
            prefix="script_bisect_",
            delete=False,
            encoding="utf-8",
        )

        try:
            temp_file.write(script_content)
            temp_file.flush()
        finally:
            temp_file.close()

        temp_path = Path(temp_file.name)
        console.print(f"[green]📄 Created temporary script: {temp_path}[/green]")

        return temp_path

    def enhance_existing_script(
        self,
        script_path: Path,
        missing_dependencies: list[str] | None = None,
    ) -> None:
        """Enhance an existing script by adding missing dependencies.

        Args:
            script_path: Path to the existing script
            missing_dependencies: List of dependencies to add

        Raises:
            FileNotFoundError: If script file doesn't exist
            ValueError: If script doesn't have PEP 723 metadata
        """
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        if not missing_dependencies:
            console.print("[dim]No missing dependencies to add[/dim]")
            return

        console.print(f"[dim]🔧 Adding dependencies to {script_path.name}...[/dim]")

        try:
            content = script_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(f"Cannot read script file: {e}") from e

        # Check if it has PEP 723 metadata
        if "# /// script" not in content:
            console.print(
                "[yellow]⚠️ Script doesn't have PEP 723 metadata, cannot enhance[/yellow]"
            )
            return

        # Parse existing metadata and add missing dependencies
        updated_content = self._add_dependencies_to_script(
            content, missing_dependencies
        )

        # Write back to file
        try:
            script_path.write_text(updated_content, encoding="utf-8")
            console.print(
                f"[green]✅ Added dependencies: {', '.join(missing_dependencies)}[/green]"
            )
        except OSError as e:
            raise ValueError(f"Cannot write to script file: {e}") from e

    def _add_dependencies_to_script(
        self, content: str, new_dependencies: list[str]
    ) -> str:
        """Add dependencies to an existing script with PEP 723 metadata.

        Args:
            content: Original script content
            new_dependencies: Dependencies to add

        Returns:
            Updated script content
        """
        lines = content.split("\n")
        updated_lines = []
        in_metadata = False
        found_dependencies = False

        for line in lines:
            if line.strip() == "# /// script":
                in_metadata = True
                updated_lines.append(line)
            elif line.strip() == "# ///" and in_metadata:
                # End of metadata block
                if not found_dependencies:
                    # Add dependencies line before closing
                    all_deps = sorted(new_dependencies)
                    deps_str = ", ".join(f'"{dep}"' for dep in all_deps)
                    updated_lines.append(f"# dependencies = [{deps_str}]")
                in_metadata = False
                updated_lines.append(line)
            elif in_metadata and line.strip().startswith("# dependencies"):
                # Parse existing dependencies and merge
                found_dependencies = True
                import re

                match = re.search(r"dependencies\s*=\s*\[(.*?)\]", line)
                if match:
                    existing_deps_str = match.group(1)
                    # Extract existing dependency names
                    existing_deps = []
                    if existing_deps_str.strip():
                        for dep in existing_deps_str.split(","):
                            dep = dep.strip().strip("\"'")
                            if dep:
                                existing_deps.append(dep)

                    # Merge with new dependencies
                    all_deps = sorted(set(existing_deps + new_dependencies))
                    deps_str = ", ".join(f'"{dep}"' for dep in all_deps)
                    updated_lines.append(f"# dependencies = [{deps_str}]")
                else:
                    # Malformed dependencies line, replace it
                    all_deps = sorted(new_dependencies)
                    deps_str = ", ".join(f'"{dep}"' for dep in all_deps)
                    updated_lines.append(f"# dependencies = [{deps_str}]")
            else:
                updated_lines.append(line)

        return "\n".join(updated_lines)

    def detect_missing_dependencies_from_error(self, error_output: str) -> list[str]:
        """Detect missing dependencies from error messages.

        Args:
            error_output: Error output from running a script

        Returns:
            List of potentially missing dependency package names
        """
        missing_deps = []

        # Common error patterns that indicate missing packages
        import_error_patterns = [
            r"ModuleNotFoundError: No module named '([^']+)'",
            r"ImportError: No module named ([^\s]+)",
            r"ImportError: cannot import name '[^']+' from '([^']+)'",
            r"from ([^\s]+) import.*ImportError",
        ]

        import re

        for pattern in import_error_patterns:
            matches = re.findall(pattern, error_output, re.MULTILINE)
            for match in matches:
                module_name = match.split(".")[0]  # Get top-level module
                # Map import name to package name if we know it
                package_name = self.dependency_detector.import_to_package.get(
                    module_name, module_name
                )
                if package_name not in missing_deps:
                    missing_deps.append(package_name)

        if missing_deps:
            console.print(
                f"[yellow]🔍 Detected potentially missing dependencies: {', '.join(missing_deps)}[/yellow]"
            )

        return missing_deps

    def suggest_common_dependencies(self, code_content: str) -> list[str]:
        """Suggest common dependencies based on code patterns.

        Args:
            code_content: Python code to analyze

        Returns:
            List of suggested dependency package names
        """
        suggestions = []
        content_lower = code_content.lower()

        # Pattern-based suggestions
        if "pandas" in content_lower or "pd." in code_content:
            suggestions.append("pandas")

        if "numpy" in content_lower or "np." in code_content:
            suggestions.append("numpy")

        if "matplotlib" in content_lower or "plt." in code_content:
            suggestions.append("matplotlib")

        if (
            "requests" in content_lower
            or ".get(" in code_content
            or ".post(" in code_content
        ):
            suggestions.append("requests")

        if "sklearn" in content_lower or "scikit" in content_lower:
            suggestions.append("scikit-learn")

        if "cv2" in code_content or "opencv" in content_lower:
            suggestions.append("opencv-python")

        if "PIL" in code_content or "pillow" in content_lower:
            suggestions.append("Pillow")

        return list(set(suggestions))  # Remove duplicates
