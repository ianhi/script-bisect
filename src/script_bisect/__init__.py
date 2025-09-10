"""script-bisect: Bisect package versions in PEP 723 Python scripts using git bisect and uv."""

import importlib.metadata

__version__: str = importlib.metadata.version("script-bisect")
__author__ = "script-bisect contributors"

from .cli import main

__all__ = ["main"]
