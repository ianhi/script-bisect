"""PEP 723 inline script metadata parser."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib  # type: ignore
except ImportError:
    import tomli as tomllib  # type: ignore

import tomli_w

from .exceptions import ParseError
from .utils import extract_package_name


class ScriptParser:
    """Parser for PEP 723 inline script metadata in Python scripts.
    
    This class handles parsing, validating, and modifying PEP 723 inline metadata
    in Python scripts, specifically for updating git dependency references.
    """
    
    def __init__(self, script_path: Path) -> None:
        """Initialize the parser with a script file.
        
        Args:
            script_path: Path to the Python script with PEP 723 metadata
            
        Raises:
            ParseError: If the script cannot be read or contains invalid metadata
        """
        self.script_path = script_path
        self._content = self._read_script()
        self._metadata = self._parse_metadata()
    
    def _read_script(self) -> str:
        """Read the script file content.
        
        Returns:
            The script file content as a string
            
        Raises:
            ParseError: If the script cannot be read
        """
        try:
            return self.script_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise ParseError(f"Cannot read script file: {e}") from e
    
    def _parse_metadata(self) -> dict[str, Any]:
        """Parse PEP 723 metadata from the script content.
        
        Returns:
            Dictionary containing the parsed metadata
            
        Raises:
            ParseError: If metadata is malformed or missing
        """
        # Find the script metadata block
        metadata_pattern = re.compile(
            r"^# /// script\s*\n((?:^#.*\n)*?)^# ///\s*\n",
            re.MULTILINE
        )
        
        match = metadata_pattern.search(self._content)
        if not match:
            raise ParseError("No PEP 723 script metadata block found")
        
        # Extract the metadata content
        metadata_lines = match.group(1).strip().split('\n')
        toml_content = []
        
        for line in metadata_lines:
            # Remove comment prefix and leading space
            if line.startswith('#'):
                clean_line = line[1:].lstrip(' ')
                toml_content.append(clean_line)
            elif line.strip() == '':
                toml_content.append('')
            else:
                raise ParseError(f"Invalid metadata line (must start with #): {line}")
        
        toml_string = '\n'.join(toml_content)
        
        try:
            return tomllib.loads(toml_string)
        except Exception as e:
            raise ParseError(f"Invalid TOML in metadata: {e}") from e
    
    def has_package(self, package_name: str) -> bool:
        """Check if a package is listed in the dependencies.
        
        Args:
            package_name: Name of the package to check for
            
        Returns:
            True if the package is found in dependencies
        """
        dependencies = self._metadata.get("dependencies", [])
        for dep in dependencies:
            if extract_package_name(dep) == package_name:
                return True
        return False
    
    def get_available_packages(self) -> list[str]:
        """Get a list of all packages in the dependencies.
        
        Returns:
            List of package names found in dependencies
        """
        dependencies = self._metadata.get("dependencies", [])
        return [extract_package_name(dep) for dep in dependencies]
    
    def get_repository_url(self, package_name: str) -> str | None:
        """Attempt to extract repository URL for a package.
        
        This method tries to find a git URL in the existing dependency
        specification. For PyPI packages, it would need external lookup.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Repository URL if found, None otherwise
        """
        dependencies = self._metadata.get("dependencies", [])
        
        for dep in dependencies:
            if extract_package_name(dep) == package_name:
                # Check if it's already a git dependency
                if "@git+" in dep:
                    # Extract the git URL
                    git_part = dep.split("@git+")[1]
                    # Remove any additional git parameters like @ref
                    if "@" in git_part:
                        git_url = git_part.split("@")[0]
                    else:
                        git_url = git_part
                    return f"git+{git_url}"
        
        # TODO: Implement PyPI metadata lookup for repository URL
        # For now, return None to require manual specification
        return None
    
    def update_git_reference(self, package_name: str, repo_url: str, new_ref: str) -> str:
        """Update the git reference for a package and return modified script content.
        
        Args:
            package_name: Name of the package to update
            repo_url: The git repository URL (should start with git+)
            new_ref: The new git reference (commit hash, tag, or branch)
            
        Returns:
            Modified script content with updated git reference
            
        Raises:
            ParseError: If the package is not found or cannot be updated
        """
        if not self.has_package(package_name):
            raise ParseError(f"Package '{package_name}' not found in dependencies")
        
        # Normalize the repo URL
        if not repo_url.startswith("git+"):
            repo_url = f"git+{repo_url}"
        
        # Find the metadata block and update it
        metadata_pattern = re.compile(
            r"(^# /// script\s*\n)((?:^#.*\n)*?)(^# ///\s*\n)",
            re.MULTILINE
        )
        
        match = metadata_pattern.search(self._content)
        if not match:
            raise ParseError("No PEP 723 script metadata block found")
        
        # Parse the current metadata
        metadata_copy = self._metadata.copy()
        dependencies = metadata_copy.get("dependencies", [])
        
        # Update the dependency
        updated_dependencies = []
        found = False
        
        for dep in dependencies:
            if extract_package_name(dep) == package_name:
                # Create new git dependency specification
                # Handle extras if present
                extras = ""
                if "[" in dep:
                    extras_match = re.search(r'\[([^\]]+)\]', dep)
                    if extras_match:
                        extras = f"[{extras_match.group(1)}]"
                
                new_dep = f"{package_name}{extras}@{repo_url}@{new_ref}"
                updated_dependencies.append(new_dep)
                found = True
            else:
                updated_dependencies.append(dep)
        
        if not found:
            raise ParseError(f"Could not find package '{package_name}' to update")
        
        # Update the metadata
        metadata_copy["dependencies"] = updated_dependencies
        
        # Convert back to TOML string
        toml_string = tomli_w.dumps(metadata_copy)
        
        # Add comment prefixes back
        commented_lines = []
        for line in toml_string.strip().split('\n'):
            if line.strip():
                commented_lines.append(f"# {line}")
            else:
                commented_lines.append("#")
        
        # Reconstruct the script
        new_metadata_block = (
            match.group(1) + 
            '\n'.join(commented_lines) + '\n' +
            match.group(3)
        )
        
        return self._content.replace(match.group(0), new_metadata_block)
    
    def get_dependency_spec(self, package_name: str) -> str | None:
        """Get the full dependency specification for a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            The full dependency specification or None if not found
        """
        dependencies = self._metadata.get("dependencies", [])
        for dep in dependencies:
            if extract_package_name(dep) == package_name:
                return dep
        return None
    
    def validate_metadata(self) -> list[str]:
        """Validate the PEP 723 metadata structure.
        
        Returns:
            List of validation warnings/errors (empty if valid)
        """
        warnings = []
        
        # Check for required dependencies field
        if "dependencies" not in self._metadata:
            warnings.append("No 'dependencies' field found in metadata")
        elif not isinstance(self._metadata["dependencies"], list):
            warnings.append("'dependencies' field must be a list")
        
        # Check Python version requirement
        requires_python = self._metadata.get("requires-python")
        if requires_python and not isinstance(requires_python, str):
            warnings.append("'requires-python' field must be a string")
        
        return warnings