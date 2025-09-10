"""Utility functions for script-bisect."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging with appropriate level and formatting.

    Args:
        verbose: Enable verbose (DEBUG) logging if True, otherwise INFO
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure logging with Rich handler for pretty output
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def create_temp_dir(prefix: str = "script_bisect_") -> Path:
    """Create a temporary directory for bisection work.

    Args:
        prefix: Prefix for the temporary directory name

    Returns:
        Path to the created temporary directory
    """
    return Path(tempfile.mkdtemp(prefix=prefix))


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename.

    Args:
        name: The original name

    Returns:
        A filename-safe version of the name
    """
    # Replace problematic characters
    safe_chars = []
    for char in name:
        # Only allow ASCII alphanumeric characters and specific symbols
        if (char.isascii() and char.isalnum()) or char in "-_.":
            safe_chars.append(char)
        else:
            safe_chars.append("_")

    return "".join(safe_chars)


def extract_package_name(dependency: str) -> str:
    """Extract the package name from a dependency specification.

    Args:
        dependency: A dependency string like "requests>=2.0" or "numpy@git+..."

    Returns:
        The package name portion

    Examples:
        >>> extract_package_name("requests>=2.0")
        'requests'
        >>> extract_package_name("numpy[extra]@git+https://github.com/numpy/numpy")
        'numpy'
    """
    # Handle git dependencies first
    name = dependency.split("@")[0] if "@" in dependency else dependency

    # Remove version specifiers and extras
    for sep in [">=", "<=", "==", "!=", ">", "<", "~=", "[", ";"]:
        if sep in name:
            name = name.split(sep)[0]

    return name.strip()


def get_commit_url(repo_url: str, commit_hash: str) -> str | None:
    """Generate a URL to view the commit on the git hosting service.

    Args:
        repo_url: The git repository URL
        commit_hash: The commit SHA

    Returns:
        URL to view the commit, or None if not supported
    """
    # Clean up the repo URL
    url = repo_url
    if url.startswith("git+"):
        url = url[4:]
    if url.endswith(".git"):
        url = url[:-4]

    # Convert SSH URLs to HTTPS
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")
    elif url.startswith("git@gitlab.com:"):
        url = url.replace("git@gitlab.com:", "https://gitlab.com/")

    # Generate commit URLs for known hosting services
    if "github.com" in url:
        return f"{url}/commit/{commit_hash}"
    elif "gitlab.com" in url:
        return f"{url}/-/commit/{commit_hash}"
    elif "bitbucket.org" in url:
        return f"{url}/commits/{commit_hash}"

    return None


def format_commit_info(
    commit_hash: str, author: str, date: str, message: str, repo_url: str | None = None
) -> str:
    """Format commit information for display.

    Args:
        commit_hash: The commit SHA
        author: The commit author
        date: The commit date
        message: The commit message (first line)
        repo_url: The repository URL (optional, for generating commit links)

    Returns:
        Formatted commit info string
    """
    lines = [
        f"Commit: {commit_hash[:12]}...",
        f"Author: {author}",
        f"Date: {date}",
        f"Message: {message}",
    ]

    # Add commit URL if we can generate one
    if repo_url:
        commit_url = get_commit_url(repo_url, commit_hash)
        if commit_url:
            lines.append(f"View: {commit_url}")

    return "\n".join(lines)
