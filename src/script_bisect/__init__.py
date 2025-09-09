"""script-bisect: Bisect package versions in PEP 723 Python scripts using git bisect and uv."""

__version__ = "0.1.0"
__author__ = "script-bisect contributors"

from .cli import main

__all__ = ["main"]