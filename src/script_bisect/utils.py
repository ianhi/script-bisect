"""Utility functions for script-bisect."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

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
        if char.isalnum() or char in "-_.":
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
    if "@" in dependency:
        name = dependency.split("@")[0]
    else:
        name = dependency
    
    # Remove version specifiers and extras
    for sep in [">=", "<=", "==", "!=", ">", "<", "~=", "[", ";"]:
        if sep in name:
            name = name.split(sep)[0]
    
    return name.strip()


def format_commit_info(commit_hash: str, author: str, date: str, message: str) -> str:
    """Format commit information for display.
    
    Args:
        commit_hash: The commit SHA
        author: The commit author
        date: The commit date
        message: The commit message (first line)
        
    Returns:
        Formatted commit info string
    """
    return (
        f"Commit: {commit_hash[:12]}...\n"
        f"Author: {author}\n" 
        f"Date: {date}\n"
        f"Message: {message}"
    )