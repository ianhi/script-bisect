"""Repository URL mappings for common Python packages.

This module contains curated mappings from package names to their
GitHub repository URLs, making it easier to auto-detect repositories
for bisection without manual input.
"""

from __future__ import annotations

# Repository mappings for common Python packages
COMMON_REPOSITORIES: dict[str, str] = {
    # Scientific Python core
    "numpy": "https://github.com/numpy/numpy",
    "scipy": "https://github.com/scipy/scipy",
    "matplotlib": "https://github.com/matplotlib/matplotlib",
    "pandas": "https://github.com/pandas-dev/pandas",
    # Machine learning
    "scikit-learn": "https://github.com/scikit-learn/scikit-learn",
    "scikit-image": "https://github.com/scikit-image/scikit-image",
    "scikit-optimize": "https://github.com/scikit-optimize/scikit-optimize",
    "sklearn": "https://github.com/scikit-learn/scikit-learn",  # alias
    # Data and climate science
    "xarray": "https://github.com/pydata/xarray",
    "zarr": "https://github.com/zarr-developers/zarr-python",
    "icechunk": "https://github.com/earth-mover/icechunk",
    "dask": "https://github.com/dask/dask",
    "numba": "https://github.com/numba/numba",
    # Visualization
    "plotly": "https://github.com/plotly/plotly.py",
    "seaborn": "https://github.com/mwaskom/seaborn",
    "bokeh": "https://github.com/bokeh/bokeh",
    "altair": "https://github.com/altair-viz/altair",
    # Web frameworks
    "django": "https://github.com/django/django",
    "flask": "https://github.com/pallets/flask",
    "fastapi": "https://github.com/tiangolo/fastapi",
    "starlette": "https://github.com/encode/starlette",
    # HTTP and networking
    "requests": "https://github.com/psf/requests",
    "httpx": "https://github.com/encode/httpx",
    "aiohttp": "https://github.com/aio-libs/aiohttp",
    # Data validation and serialization
    "pydantic": "https://github.com/pydantic/pydantic",
    "marshmallow": "https://github.com/marshmallow-code/marshmallow",
    # Database
    "sqlalchemy": "https://github.com/sqlalchemy/sqlalchemy",
    "alembic": "https://github.com/sqlalchemy/alembic",
    "psycopg2": "https://github.com/psycopg/psycopg2",
    # Testing and development
    "pytest": "https://github.com/pytest-dev/pytest",
    "hypothesis": "https://github.com/HypothesisWorks/hypothesis",
    "mypy": "https://github.com/python/mypy",
    "ruff": "https://github.com/astral-sh/ruff",
    # CLI and utilities
    "click": "https://github.com/pallets/click",
    "typer": "https://github.com/tiangolo/typer",
    "rich": "https://github.com/Textualize/rich",
    "textual": "https://github.com/Textualize/textual",
    # Async and concurrency
    "asyncio": "https://github.com/python/cpython",  # stdlib but sometimes versioned
    "trio": "https://github.com/python-trio/trio",
    "anyio": "https://github.com/agronholm/anyio",
    # Image processing
    "pillow": "https://github.com/python-pillow/Pillow",
    "opencv-python": "https://github.com/opencv/opencv-python",
    # Jupyter ecosystem
    "jupyter": "https://github.com/jupyter/jupyter",
    "jupyterlab": "https://github.com/jupyterlab/jupyterlab",
    "ipython": "https://github.com/ipython/ipython",
    "notebook": "https://github.com/jupyter/notebook",
}


def get_repository_url(package_name: str) -> str | None:
    """Get repository URL for a package name.

    Args:
        package_name: Name of the package to look up

    Returns:
        Repository URL if found, None otherwise
    """
    return COMMON_REPOSITORIES.get(package_name)


def list_supported_packages() -> list[str]:
    """Get list of all packages with known repository mappings.

    Returns:
        Sorted list of supported package names
    """
    return sorted(COMMON_REPOSITORIES.keys())


def add_repository(package_name: str, repository_url: str) -> None:
    """Add or update a repository mapping.

    Args:
        package_name: Name of the package
        repository_url: GitHub repository URL
    """
    COMMON_REPOSITORIES[package_name] = repository_url


def has_repository(package_name: str) -> bool:
    """Check if a package has a known repository mapping.

    Args:
        package_name: Name of the package to check

    Returns:
        True if repository mapping exists, False otherwise
    """
    return package_name in COMMON_REPOSITORIES
