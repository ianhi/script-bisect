"""Common correction patterns for auto-fixing Python scripts.

This module contains patterns for detecting and fixing common issues
in Python scripts extracted from GitHub issues, such as missing imports
and other static analysis corrections.
"""

from __future__ import annotations

# Common import fixes for frequently used names
# Maps usage patterns (like "np.") to their required import statements
COMMON_IMPORT_FIXES: dict[str, str] = {
    # NumPy
    "np.": "import numpy as np",
    "numpy.": "import numpy",
    # Pandas
    "pd.": "import pandas as pd",
    "pandas.": "import pandas",
    # Matplotlib
    "plt.": "import matplotlib.pyplot as plt",
    "pyplot.": "import matplotlib.pyplot",
    # Standard library modules
    "sys.": "import sys",
    "os.": "import os",
    "re.": "import re",
    "json.": "import json",
    "datetime.": "import datetime",
    "pathlib.": "import pathlib",
    "random.": "import random",
    "math.": "import math",
    "time.": "import time",
    "collections.": "import collections",
    "itertools.": "import itertools",
    "functools.": "import functools",
    "operator.": "import operator",
    "copy.": "import copy",
    "pickle.": "import pickle",
    "csv.": "import csv",
    "urllib.": "import urllib",
    "subprocess.": "import subprocess",
    "threading.": "import threading",
    "multiprocessing.": "import multiprocessing",
    "logging.": "import logging",
    "warnings.": "import warnings",
    "tempfile.": "import tempfile",
    "shutil.": "import shutil",
    "glob.": "import glob",
    "fnmatch.": "import fnmatch",
    "argparse.": "import argparse",
    "configparser.": "import configparser",
    # Data science and ML
    "sklearn.": "import sklearn",
    "scipy.": "import scipy",
    "seaborn.": "import seaborn",
    "plotly.": "import plotly",
    "statsmodels.": "import statsmodels",
    "xgboost.": "import xgboost",
    "lightgbm.": "import lightgbm",
    "catboost.": "import catboost",
    "tensorflow.": "import tensorflow",
    "torch.": "import torch",
    "keras.": "import keras",
    "transformers.": "import transformers",
    # Web frameworks and HTTP
    "requests.": "import requests",
    "flask.": "import flask",
    "fastapi.": "import fastapi",
    "django.": "import django",
    "urllib3.": "import urllib3",
    "httpx.": "import httpx",
    "aiohttp.": "import aiohttp",
    # Database and data storage
    "sqlite3.": "import sqlite3",
    "sqlalchemy.": "import sqlalchemy",
    "pymongo.": "import pymongo",
    "redis.": "import redis",
    "psycopg2.": "import psycopg2",
    # File formats
    "yaml.": "import yaml",
    "toml.": "import toml",
    "xml.": "import xml",
    # CLI and utilities
    "click.": "import click",
    "typer.": "import typer",
    "rich.": "import rich",
    "tqdm.": "import tqdm",
    # Async
    "asyncio.": "import asyncio",
    "async_timeout.": "import async_timeout",
    "trio.": "import trio",
    "anyio.": "import anyio",
    # Testing
    "pytest.": "import pytest",
    "unittest.": "import unittest",
    "mock.": "import mock",
    "hypothesis.": "import hypothesis",
    # Data storage and formats
    "zarr.": "import zarr",
    "icechunk.": "import icechunk",
}

# Common class/function patterns that need specific imports
# Maps class/function names to their required import statements
COMMON_CLASS_IMPORTS: dict[str, str] = {
    # NumPy
    "ndarray": "import numpy as np",
    "array": "import numpy as np",  # Could be numpy array
    # Pandas
    "DataFrame": "import pandas as pd",
    "Series": "import pandas as pd",
    "Index": "import pandas as pd",
    "MultiIndex": "import pandas as pd",
    "Categorical": "import pandas as pd",
    "Timestamp": "import pandas as pd",
    "Timedelta": "import pandas as pd",
    "Period": "import pandas as pd",
    # Xarray (common in climate/data science)
    "DataArray": "import xarray as xr",
    "Dataset": "import xarray as xr",
    # Matplotlib
    "Figure": "import matplotlib.pyplot as plt",
    "Axes": "import matplotlib.pyplot as plt",
    # Scikit-learn
    "LinearRegression": "from sklearn.linear_model import LinearRegression",
    "LogisticRegression": "from sklearn.linear_model import LogisticRegression",
    "RandomForestClassifier": "from sklearn.ensemble import RandomForestClassifier",
    "RandomForestRegressor": "from sklearn.ensemble import RandomForestRegressor",
    "GradientBoostingClassifier": "from sklearn.ensemble import GradientBoostingClassifier",
    "SVC": "from sklearn.svm import SVC",
    "KMeans": "from sklearn.cluster import KMeans",
    "PCA": "from sklearn.decomposition import PCA",
    "StandardScaler": "from sklearn.preprocessing import StandardScaler",
    "MinMaxScaler": "from sklearn.preprocessing import MinMaxScaler",
    "train_test_split": "from sklearn.model_selection import train_test_split",
    "cross_val_score": "from sklearn.model_selection import cross_val_score",
    "GridSearchCV": "from sklearn.model_selection import GridSearchCV",
    "accuracy_score": "from sklearn.metrics import accuracy_score",
    "classification_report": "from sklearn.metrics import classification_report",
    "confusion_matrix": "from sklearn.metrics import confusion_matrix",
    "mean_squared_error": "from sklearn.metrics import mean_squared_error",
    "r2_score": "from sklearn.metrics import r2_score",
    # Python standard library classes
    "Path": "from pathlib import Path",
    "datetime": "from datetime import datetime",
    "date": "from datetime import date",
    "time": "from datetime import time",
    "timedelta": "from datetime import timedelta",
    "defaultdict": "from collections import defaultdict",
    "Counter": "from collections import Counter",
    "deque": "from collections import deque",
    "OrderedDict": "from collections import OrderedDict",
    "namedtuple": "from collections import namedtuple",
    "Enum": "from enum import Enum",
    "IntEnum": "from enum import IntEnum",
    "dataclass": "from dataclasses import dataclass",
    "field": "from dataclasses import field",
    "partial": "from functools import partial",
    "lru_cache": "from functools import lru_cache",
    "cached_property": "from functools import cached_property",
    "reduce": "from functools import reduce",
    # Web and API
    "Response": "import requests",
    "Session": "import requests",
    "HTTPException": "from fastapi import HTTPException",
    "Depends": "from fastapi import Depends",
    "FastAPI": "from fastapi import FastAPI",
    "Flask": "from flask import Flask",
    "Blueprint": "from flask import Blueprint",
    "request": "from flask import request",
    "jsonify": "from flask import jsonify",
}

# Common function calls that need imports
COMMON_FUNCTION_IMPORTS: dict[str, str] = {
    # File operations
    "open": "",  # Built-in, no import needed
    "read_csv": "import pandas as pd",
    "read_excel": "import pandas as pd",
    "read_json": "import pandas as pd",
    "read_parquet": "import pandas as pd",
    "read_sql": "import pandas as pd",
    "to_csv": "",  # Method call, handled by class imports
    "to_excel": "",  # Method call
    "to_json": "",  # Method call
    "to_parquet": "",  # Method call
    # NumPy functions
    "arange": "import numpy as np",
    "linspace": "import numpy as np",
    "zeros": "import numpy as np",
    "ones": "import numpy as np",
    "empty": "import numpy as np",
    "eye": "import numpy as np",
    "random": "import numpy as np",  # Could be numpy.random
    "mean": "import numpy as np",
    "median": "import numpy as np",
    "std": "import numpy as np",
    "var": "import numpy as np",
    "min": "",  # Built-in
    "max": "",  # Built-in
    "sum": "",  # Built-in
    "dot": "import numpy as np",
    "cross": "import numpy as np",
    "transpose": "import numpy as np",
    "reshape": "import numpy as np",
    "concatenate": "import numpy as np",
    "stack": "import numpy as np",
    "vstack": "import numpy as np",
    "hstack": "import numpy as np",
    "where": "import numpy as np",
    "argmax": "import numpy as np",
    "argmin": "import numpy as np",
    "unique": "import numpy as np",
    "sort": "import numpy as np",
    "argsort": "import numpy as np",
    # Matplotlib functions
    "plot": "import matplotlib.pyplot as plt",
    "scatter": "import matplotlib.pyplot as plt",
    "bar": "import matplotlib.pyplot as plt",
    "hist": "import matplotlib.pyplot as plt",
    "boxplot": "import matplotlib.pyplot as plt",
    "heatmap": "import seaborn as sns",  # More likely seaborn
    "figure": "import matplotlib.pyplot as plt",
    "subplot": "import matplotlib.pyplot as plt",
    "subplots": "import matplotlib.pyplot as plt",
    "show": "import matplotlib.pyplot as plt",
    "savefig": "import matplotlib.pyplot as plt",
    "xlabel": "import matplotlib.pyplot as plt",
    "ylabel": "import matplotlib.pyplot as plt",
    "title": "import matplotlib.pyplot as plt",
    "legend": "import matplotlib.pyplot as plt",
    "grid": "import matplotlib.pyplot as plt",
    "xlim": "import matplotlib.pyplot as plt",
    "ylim": "import matplotlib.pyplot as plt",
}

# Patterns for common typos and corrections
COMMON_TYPO_FIXES: dict[str, str] = {
    # Common misspellings
    "dataframe": "DataFrame",
    "dataArray": "DataArray",
    "numpy": "np",  # When used as module alias
    "pandas": "pd",  # When used as module alias
    "matplotlib": "plt",  # When used incorrectly
    "pyplot": "plt",  # When used as alias
}

# Common code patterns that need fixing
CODE_PATTERN_FIXES: dict[str, str] = {
    # Missing parentheses
    r"\.shape$": ".shape()",  # pandas/numpy shape property
    r"\.size$": ".size()",  # size property
    r"\.count$": ".count()",  # count method
    # Common syntax fixes
    r"print ([^(].*[^)])$": r"print(\1)",  # print statement to function
    r"range\s*\(\s*len\(([^)]+)\)\s*\)": r"range(len(\1))",  # range(len(x))
}


def get_import_for_pattern(pattern: str) -> str | None:
    """Get the required import for a usage pattern.

    Args:
        pattern: Usage pattern like 'np.' or 'DataFrame'

    Returns:
        Required import statement or None if not found
    """
    # Check attribute patterns first (np., pd., etc.)
    if pattern in COMMON_IMPORT_FIXES:
        return COMMON_IMPORT_FIXES[pattern]

    # Check class/function names
    if pattern in COMMON_CLASS_IMPORTS:
        return COMMON_CLASS_IMPORTS[pattern]

    # Check function patterns
    if pattern in COMMON_FUNCTION_IMPORTS:
        return COMMON_FUNCTION_IMPORTS[pattern]

    return None


def get_all_patterns() -> list[str]:
    """Get all known correction patterns.

    Returns:
        List of all patterns that can be auto-corrected
    """
    patterns: list[str] = []
    patterns.extend(COMMON_IMPORT_FIXES.keys())
    patterns.extend(COMMON_CLASS_IMPORTS.keys())
    patterns.extend(COMMON_FUNCTION_IMPORTS.keys())
    return sorted(patterns)


def get_typo_fix(text: str) -> str | None:
    """Get correction for a common typo.

    Args:
        text: Text that might be a typo

    Returns:
        Corrected text or None if no fix available
    """
    return COMMON_TYPO_FIXES.get(text.lower())


def suggest_import_for_undefined_name(name: str) -> list[str]:
    """Suggest possible imports for an undefined name.

    Args:
        name: Undefined variable/function/class name

    Returns:
        List of possible import statements
    """
    suggestions = []

    # Check if it's a known class or function
    if name in COMMON_CLASS_IMPORTS:
        suggestions.append(COMMON_CLASS_IMPORTS[name])

    if name in COMMON_FUNCTION_IMPORTS and COMMON_FUNCTION_IMPORTS[name]:
        suggestions.append(COMMON_FUNCTION_IMPORTS[name])

    # Check if it might be a shortened module name
    for pattern, import_stmt in COMMON_IMPORT_FIXES.items():
        if pattern.startswith(name + "."):
            suggestions.append(import_stmt)

    return list(set(suggestions))  # Remove duplicates
