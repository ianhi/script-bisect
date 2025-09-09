# script-bisect

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bisect package versions in PEP 723 Python scripts using git bisect and uv.

## Overview

`script-bisect` combines the power of git bisect with PEP 723 inline script metadata to automatically find the commit that introduced a regression in a Python package dependency. It works by:

1. 📄 **Parsing** your PEP 723 script to extract dependency information
2. 📥 **Cloning** the package repository automatically  
3. 🔄 **Running** git bisect with intelligent test automation
4. ✏️ **Updating** package references for each commit tested
5. 🎯 **Finding** the exact commit that caused the issue

Perfect for debugging package regressions, testing new features, and creating reliable bug reports.

## Installation

### Using uvx (Recommended)

```bash
uvx script-bisect script.py package_name good_ref bad_ref
```

### Using uv

```bash
uv tool install script-bisect
script-bisect script.py package_name good_ref bad_ref
```

### Development Installation

```bash
git clone https://github.com/user/script-bisect.git
cd script-bisect
uv sync --extra dev
uv run script-bisect --help
```

## Quick Start

### 1. Create a PEP 723 Script

Create a script that demonstrates your issue:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "xarray@git+https://github.com/pydata/xarray.git@main",
# ]
# ///

import xarray as xr
import numpy as np

# Your reproducer code here
data = xr.Dataset({'temp': (['time'], np.random.randn(10))})
result = data.some_method()  # This might fail in certain versions
print("✅ Test passed!")
```

### 2. Run the Bisection

```bash
# Find when something broke
script-bisect bug_report.py xarray v2024.01.0 v2024.03.0

# Find when something was fixed (inverse mode)
script-bisect bug_report.py pandas v1.5.0 v2.0.0 --inverse
```

### 3. Get Results

```
🔍 script-bisect v0.1.0
Bisect package versions in PEP 723 Python scripts

📦 Package: xarray
🔗 Repository: https://github.com/pydata/xarray.git
✅ Good ref: v2024.01.0 (commit: abc123...)
❌ Bad ref: v2024.03.0 (commit: def456...)

🔄 Starting bisection (approximately 7 steps)...

✨ Found first bad commit:

Commit: 234pqr890...
Author: John Doe <john@example.com>
Date: 2024-02-15 10:30:00
Message: Refactor array indexing logic

View on GitHub: https://github.com/pydata/xarray/commit/234pqr890
```

## Usage

### Basic Usage

```bash
script-bisect SCRIPT PACKAGE GOOD_REF BAD_REF
```

- **SCRIPT**: Path to your PEP 723 Python script
- **PACKAGE**: Name of the package to bisect  
- **GOOD_REF**: Git reference (tag/commit/branch) where it works
- **BAD_REF**: Git reference where it's broken

### Options

- `--repo-url URL`: Override repository URL (auto-detected from git dependencies)
- `--test-command CMD`: Custom test command (default: `uv run SCRIPT`)
- `--inverse`: Find when something was fixed (not broken)
- `--keep-clone`: Keep cloned repository for inspection
- `--dry-run`: Show what would be done without executing
- `--verbose`: Enable detailed logging

### Examples

#### Basic Package Regression

```bash
# Your script has: numpy>=1.24.0
script-bisect reproducer.py numpy 1.24.0 1.26.0
```

#### Git Dependency Already Present

```bash
# Your script has: xarray@git+https://github.com/pydata/xarray.git@main
script-bisect bug_report.py xarray v2024.01.0 main
```

#### Custom Repository

```bash
script-bisect test.py numpy v1.24.0 main \\
    --repo-url https://github.com/numpy/numpy.git
```

#### Custom Test Command

```bash
script-bisect test.py pandas v2.0.0 main \\
    --test-command "python -m pytest {script}"
```

#### Finding Fixes (Inverse Mode)

```bash
# Find when a bug was fixed
script-bisect regression_test.py scipy v1.10.0 v1.11.0 --inverse
```

## Requirements

### System Requirements

- **Python 3.11+**
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **git** version control

### Script Requirements

Your Python script must contain PEP 723 inline metadata with dependencies:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "package_name>=1.0",
#   # OR for git dependencies:
#   "package_name@git+https://github.com/org/repo.git@ref",
# ]
# ///
```

The tool will automatically convert PyPI package specs to git dependencies during bisection.

## How It Works

### 1. Script Analysis
- Parses PEP 723 metadata from your script
- Validates package dependencies and requirements
- Auto-detects repository URLs for PyPI packages

### 2. Repository Management  
- Clones the package repository to a temporary directory
- Validates that good/bad references exist
- Manages cleanup automatically (unless `--keep-clone` is used)

### 3. Bisection Process
- Uses `git bisect run` with an automated test script
- For each commit, updates your script's dependency reference  
- Runs `uv run script.py` to test the specific commit
- Returns appropriate exit codes for git bisect (0=good, 1=bad, 125=skip)

### 4. Result Reporting
- Identifies the exact problematic commit
- Shows commit details (author, date, message)
- Provides GitHub/GitLab links when possible

## Troubleshooting

### Common Issues

**"Package not found in dependencies"**
- Ensure the package name matches exactly what's in your dependencies list
- Use `--verbose` to see available packages

**"Could not auto-detect repository URL"**  
- Use `--repo-url` to specify the repository manually
- Ensure the package has repository metadata on PyPI

**"uv not found"**
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Ensure uv is in your PATH

**Test always fails/passes**
- Check your script logic with `--dry-run`
- Use `--verbose` to see test output
- Verify your script correctly demonstrates the issue

### Getting Help

- Check the [troubleshooting guide](./docs/troubleshooting.md)
- Review example scripts in [`examples/`](./examples/)
- Open an issue on [GitHub](https://github.com/user/script-bisect/issues)

## Future Features

### Roadmap 🗺️

- **GitHub Issue Integration**: Point at a GitHub issue to automatically extract and test script blocks
  ```bash
  script-bisect --issue https://github.com/pydata/xarray/issues/1234
  ```
- **Multiple Package Bisection**: Bisect multiple related packages simultaneously
- **PyPI Metadata Lookup**: Automatic repository detection for more packages
- **Regression Test Suite**: Generate test suites from bisection results
- **CI Integration**: GitHub Actions and other CI platform support

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/user/script-bisect.git
cd script-bisect
uv sync --extra dev
uv run pre-commit install

# Run tests
uv run pytest
uv run pytest --cov=script_bisect

# Format and lint
uv run ruff format
uv run ruff check --fix
```

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Acknowledgments

- Built with [uv](https://github.com/astral-sh/uv) for fast Python package management
- Inspired by [PEP 723](https://peps.python.org/pep-0723/) inline script metadata
- Uses [rich](https://github.com/Textualize/rich) for beautiful terminal output