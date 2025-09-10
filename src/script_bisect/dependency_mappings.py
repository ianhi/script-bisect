"""Import name to package name mappings for dependency detection.

This module contains mappings from Python import names to their
corresponding PyPI package names, used for automatic dependency
detection in Python scripts.
"""

from __future__ import annotations

# Mapping from import names to PyPI package names
IMPORT_TO_PACKAGE: dict[str, str] = {
    # Image and computer vision
    "cv2": "opencv-python",
    "PIL": "Pillow",
    # Machine learning and data science
    "sklearn": "scikit-learn",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "scipy": "scipy",
    "sympy": "sympy",
    "plotly": "plotly",
    "bokeh": "bokeh",
    "altair": "altair",
    "streamlit": "streamlit",
    "dash": "dash",
    # Data formats and parsing
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "lxml": "lxml",
    # Authentication and security
    "requests_oauthlib": "requests-oauthlib",
    "jwt": "PyJWT",
    "cryptography": "cryptography",
    # Date and time
    "dateutil": "python-dateutil",
    # Environment and configuration
    "dotenv": "python-dotenv",
    # File type detection
    "magic": "python-magic",
    # System utilities
    "psutil": "psutil",
    # HTTP clients
    "httpx": "httpx",
    "aiohttp": "aiohttp",
    "requests": "requests",
    "urllib3": "urllib3",
    "certifi": "certifi",
    "chardet": "chardet",
    "idna": "idna",
    # Web frameworks
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "starlette": "starlette",
    "flask": "Flask",
    "django": "Django",
    "tornado": "tornado",
    "bottle": "bottle",
    "pyramid": "pyramid",
    # Data validation
    "pydantic": "pydantic",
    # Database
    "sqlalchemy": "SQLAlchemy",
    "alembic": "alembic",
    "redis": "redis",
    "pymongo": "pymongo",
    "psycopg2": "psycopg2-binary",
    "mysqlclient": "mysqlclient",
    # Task queues
    "celery": "celery",
    "dramatiq": "dramatiq",
    # Testing
    "pytest": "pytest",
    "mock": "mock",
    "hypothesis": "hypothesis",
    # Jupyter ecosystem
    "jupyter": "jupyter",
    "ipython": "ipython",
    "notebook": "notebook",
    "jupyterlab": "jupyterlab",
    # CLI and utilities
    "click": "click",
    "typer": "typer",
    "argparse": "argparse",  # standard library but sometimes confused
    "rich": "rich",
    "textual": "textual",
    "tqdm": "tqdm",
    "colorama": "colorama",
}

# Python standard library modules (Python 3.12+)
STANDARD_LIBRARY: set[str] = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "copy",
    "copyreg",
    "cProfile",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "doctest",
    "email",
    "encodings",
    "ensurepip",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "sys",
    "sysconfig",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "trace",
    "traceback",
    "tracemalloc",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    # Python 3.9+ additions
    "graphlib",
    "zoneinfo",
    # Python 3.10+ additions
    "tomllib",
    # Python 3.11+ additions (note: tomli_w is not actually stdlib)
    "tomli_w",  # Not standard library, but commonly confused
}


def get_package_name(import_name: str) -> str:
    """Get the PyPI package name for an import name.

    Args:
        import_name: The name used in import statements

    Returns:
        The corresponding PyPI package name, or the import name if no mapping exists
    """
    return IMPORT_TO_PACKAGE.get(import_name, import_name)


def is_standard_library(import_name: str) -> bool:
    """Check if an import name is part of the Python standard library.

    Args:
        import_name: The name used in import statements

    Returns:
        True if it's a standard library module, False otherwise
    """
    return import_name in STANDARD_LIBRARY


def list_known_imports() -> list[str]:
    """Get list of all known import name mappings.

    Returns:
        Sorted list of import names with known package mappings
    """
    return sorted(IMPORT_TO_PACKAGE.keys())


def add_mapping(import_name: str, package_name: str) -> None:
    """Add or update an import to package mapping.

    Args:
        import_name: The name used in import statements
        package_name: The corresponding PyPI package name
    """
    IMPORT_TO_PACKAGE[import_name] = package_name
