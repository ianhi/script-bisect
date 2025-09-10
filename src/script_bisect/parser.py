"""PEP 723 inline script metadata parser."""

from __future__ import annotations

import logging
import re
import tomllib
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import tomli_w

from .exceptions import ParseError
from .utils import extract_package_name

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path


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

    @classmethod
    def from_content(cls, content: str) -> ScriptParser:
        """Create a ScriptParser from script content rather than a file.

        Args:
            content: The script content with PEP 723 metadata

        Returns:
            ScriptParser instance

        Raises:
            ParseError: If the content contains invalid metadata
        """
        # Create a temporary instance
        instance = cls.__new__(cls)
        instance.script_path = None  # type: ignore  # No file path for content-based parser
        instance._content = content
        instance._metadata = instance._parse_metadata()
        return instance

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
        # Find the script metadata block (allow any lines between markers)
        metadata_pattern = re.compile(
            r"^# /// script\s*\n(.*?)^# ///\s*\n", re.MULTILINE | re.DOTALL
        )

        match = metadata_pattern.search(self._content)
        if not match:
            raise ParseError("No PEP 723 script metadata block found")

        # Extract the metadata content
        metadata_lines = match.group(1).strip().split("\n")
        toml_content = []

        for line in metadata_lines:
            # Remove comment prefix and leading space
            if line.startswith("#"):
                clean_line = line[1:].lstrip(" ")
                toml_content.append(clean_line)
            elif line.strip() == "":
                toml_content.append("")
            else:
                raise ParseError(f"Invalid metadata line (must start with #): {line}")

        toml_string = "\n".join(toml_content)

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
        return any(extract_package_name(dep) == package_name for dep in dependencies)

    def get_available_packages(self) -> list[str]:
        """Get a list of all packages in the dependencies.

        Returns:
            List of package names found in dependencies
        """
        dependencies = self._metadata.get("dependencies", [])
        return [extract_package_name(dep) for dep in dependencies]

    def get_repository_url(
        self, package_name: str, github_context: str | None = None
    ) -> str | None:
        """Attempt to extract repository URL for a package.

        This method tries multiple approaches:
        1. Find git URL in existing dependency specification
        2. Look up in curated list of common packages
        3. Use importlib.metadata to find project URLs
        4. Extract from GitHub issue URL context (if available)

        Args:
            package_name: Name of the package
            github_context: GitHub issue/PR URL for context hints

        Returns:
            Repository URL if found, None otherwise
        """
        dependencies = self._metadata.get("dependencies", [])

        # Method 1: Check existing git dependencies
        for dep in dependencies:
            if extract_package_name(dep) == package_name and "@git+" in dep:
                # Extract the git URL
                git_part = dep.split("@git+")[1]
                # Remove any additional git parameters like @ref
                git_url = git_part.split("@")[0] if "@" in git_part else git_part
                return f"git+{git_url}"

        # Method 2: Curated list of common scientific Python packages
        from .repository_mappings import get_repository_url as get_curated_repo

        repo_url = get_curated_repo(package_name)
        if repo_url:
            return repo_url

        # Method 3: Try extracting from GitHub context
        if github_context:
            context_repo = self._get_repo_from_github_context(
                package_name, github_context
            )
            if context_repo:
                return context_repo

        # Method 4: Try importlib.metadata
        repo_url = self._get_repo_from_metadata(package_name)
        if repo_url:
            return repo_url

        return None

    def update_git_reference(
        self, package_name: str, repo_url: str, new_ref: str
    ) -> str:
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
            r"(^# /// script\s*\n)((?:^#.*\n)*?)(^# ///\s*\n)", re.MULTILINE
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
                    extras_match = re.search(r"\[([^\]]+)\]", dep)
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
        for line in toml_string.strip().split("\n"):
            if line.strip():
                commented_lines.append(f"# {line}")
            else:
                commented_lines.append("#")

        # Reconstruct the script
        new_metadata_block = (
            match.group(1) + "\n".join(commented_lines) + "\n" + match.group(3)
        )

        modified_content = self._content.replace(match.group(0), new_metadata_block)
        return modified_content

    def get_dependency_spec(self, package_name: str) -> str | None:
        """Get the full dependency specification for a package.

        Args:
            package_name: Name of the package

        Returns:
            The full dependency specification or None if not found
        """
        dependencies = self._metadata.get("dependencies", [])
        for dep in dependencies:
            # Ensure dep is treated as a string
            dep_str = str(dep)
            if extract_package_name(dep_str) == package_name:
                return dep_str
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

    def _get_repo_from_metadata(self, package_name: str) -> str | None:
        """Try to extract repository URL from package metadata using importlib.

        Args:
            package_name: Name of the package to look up

        Returns:
            Repository URL if found, None otherwise
        """
        try:
            import importlib.metadata as metadata

            # Get package metadata
            dist = metadata.distribution(package_name)

            # Check common URL fields that might contain the repository
            project_urls = dist.metadata.get_all("Project-URL") or []
            home_page = dist.metadata.get("Home-page")

            # Look for repository URLs in project URLs
            for url_entry in project_urls:
                if isinstance(url_entry, str) and ", " in url_entry:
                    label, url = url_entry.split(", ", 1)
                    label = label.lower()
                    if any(
                        keyword in label
                        for keyword in [
                            "source",
                            "repository",
                            "repo",
                            "code",
                            "github",
                        ]
                    ) and self._is_valid_git_repo_url(url):
                        return url

            # Check home page as fallback
            if home_page and self._is_valid_git_repo_url(home_page):
                return home_page

        except (metadata.PackageNotFoundError, ImportError, ValueError):
            # Package not installed or importlib.metadata not available
            pass

        return None

    def _is_valid_git_repo_url(self, url: str) -> bool:
        """Check if a URL looks like a valid git repository URL.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a git repository
        """
        try:
            parsed = urlparse(url)

            # Check for GitHub, GitLab, Bitbucket, or other git hosting
            git_hosts = [
                "github.com",
                "gitlab.com",
                "bitbucket.org",
                "codeberg.org",
                "git.sr.ht",
            ]

            return bool(
                parsed.scheme in ("https", "http", "git")
                and any(host in parsed.netloc for host in git_hosts)
                and parsed.path.strip("/")  # has a path
            )
        except Exception:
            return False

    def _get_repo_from_github_context(
        self, package_name: str, github_url: str
    ) -> str | None:
        """Try to extract repository URL from GitHub issue context.

        If the GitHub issue is from the same repository as the package being bisected,
        we can use that repository URL directly.

        Args:
            package_name: Name of the package to look up
            github_url: GitHub issue/PR URL for context

        Returns:
            Repository URL if contextually relevant, None otherwise
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(github_url)
            if parsed.hostname not in ("github.com", "www.github.com"):
                return None

            # Extract owner/repo from path like /owner/repo/issues/123
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                return None

            owner, repo = path_parts[0], path_parts[1]
            repo_url = f"https://github.com/{owner}/{repo}"

            # Heuristic: if the repo name matches the package name or contains it,
            # it's likely the same project
            if (
                package_name.lower() == repo.lower()
                or package_name.replace("-", "").replace("_", "").lower()
                == repo.replace("-", "").replace("_", "").lower()
                or package_name.lower() in repo.lower()
                or repo.lower() in package_name.lower()
            ):
                return repo_url

            # Additional heuristic: check for common package/repo name patterns
            package_variations = {
                package_name.replace("-", "_"),
                package_name.replace("_", "-"),
                f"{package_name}-python",
                f"python-{package_name}",
                f"{package_name}.py",
            }

            if any(var.lower() == repo.lower() for var in package_variations):
                return repo_url

        except Exception as e:
            logger.warning("Failed to parse repository URL: %s", e, exc_info=True)

        return None
