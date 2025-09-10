# script-bisect Project Documentation

## Project Overview

**script-bisect** is a command-line tool that automates git bisection for Python package dependencies using PEP 723 inline script metadata. It helps developers find the exact commit where a regression was introduced in a Python package by automatically testing different package versions.

### Core Purpose
- **Problem**: When a Python package breaks, finding the exact commit that caused the regression is manual and time-consuming
- **Solution**: Automate git bisect with intelligent package version testing using PEP 723 scripts as test cases
- **Value**: Developers can quickly identify problematic commits to create better bug reports and understand regressions

## Architecture Overview

### Technology Stack
- **Language**: Python 3.12+
- **Package Manager**: uv (modern Python package management)
- **CLI Framework**: Click (command-line interface)
- **UI Library**: Rich (terminal formatting and tables)
- **Interactive Input**: prompt-toolkit (tab completion and prompts)
- **Git Operations**: GitPython (repository management)
- **Testing**: pytest with coverage
- **Code Quality**: ruff (linting/formatting), mypy (type checking), pre-commit hooks

### Project Structure
```
src/script_bisect/
├── __init__.py                  # Package initialization
├── cli.py                      # Command-line interface and main entry point
├── interactive.py              # Interactive prompts and UI
├── parser.py                   # PEP 723 script metadata parsing
├── bisector.py                 # Core git bisection logic
├── runner.py                   # Test execution and process management
├── repository_manager.py       # Git repository operations with optimizations (NEW)
├── end_state_menu.py           # Post-bisection options and re-runs (NEW)
├── bisection_orchestrator.py   # High-level bisection coordination (NEW)
├── validation.py               # Reference validation and fixing (NEW)
├── cli_display.py              # Display utilities and formatting (NEW)
├── utils.py                    # Shared utilities and helpers
└── exceptions.py               # Custom exception definitions

tests/
├── test_*.py                   # Comprehensive test coverage
├── test_repository_manager.py  # Repository management tests (NEW)
├── fixtures/                   # Test data and mock scripts
└── integration/                # End-to-end integration tests

examples/                       # Example PEP 723 scripts for testing
.github/workflows/              # CI/CD automation
```

## Core Components

### 1. CLI Interface (cli.py)
- **Entry Point**: Main command-line interface using Click
- **Argument Parsing**: Handles script path, package name, git references
- **Interactive Mode**: NEW - Prompts for missing parameters
- **Validation**: Smart reference validation and swapping detection
- **Configuration**: Supports dry-run, verbose modes, custom test commands

### 2. Interactive UI (interactive.py) - NEW FEATURE
- **Smart Prompts**: Only asks for missing parameters (package, good ref, bad ref)
- **Tab Completion**: Fuzzy autocompletion for git references using prompt-toolkit
- **Git Integration**: Fetches remote refs automatically for completion
- **Validation**: Real-time validation of git references and repository URLs
- **UX Enhancement**: Shows previously entered refs, colored output, confirmation dialogs

### 3. Script Parser (parser.py)
- **PEP 723 Support**: Parses inline script metadata from Python files
- **Dependency Detection**: Extracts package dependencies and requirements
- **Repository Discovery**: Auto-detects git repository URLs from PyPI metadata
- **Metadata Management**: Handles requirements-python, dependencies arrays

### 4. Git Bisector (bisector.py)
- **Repository Management**: Clones and manages temporary git repositories
- **Bisection Logic**: Implements automated git bisect with custom test scripts
- **Package Updates**: Dynamically updates PEP 723 metadata for each commit
- **Performance**: Uses sparse checkout and blob filtering for efficiency
- **Cleanup**: Automatic temporary directory management

### 5. Test Runner (runner.py)
- **Process Management**: Executes test scripts with proper isolation
- **uv Integration**: Uses uv for fast, reliable package management
- **Exit Codes**: Proper git bisect exit codes (0=good, 1=bad, 125=skip)
- **Output Capture**: Captures and processes test execution output
- **Error Summarization**: Intelligent error extraction and user-friendly display

### 6. Repository Manager (repository_manager.py) - NEW FEATURE
- **Optimized Cloning**: Efficient repository setup with sparse checkout
- **Blob Filtering**: Uses git filters to minimize bandwidth usage
- **Reference Resolution**: Smart resolution with similarity suggestions
- **Performance Focus**: Minimal disk usage and network requests
- **Cleanup Management**: Automatic temporary directory management

### 7. End State Menu (end_state_menu.py) - NEW FEATURE
- **Post-Bisection Options**: Interactive menu after completion
- **Parameter Re-runs**: Re-run with different refs, scripts, or settings
- **Editor Integration**: Automatic editor launching for script modification
- **Session Continuity**: Seamless transition between multiple bisections
- **User Experience**: Eliminates need to restart entire process

### 8. Bisection Orchestrator (bisection_orchestrator.py) - NEW FEATURE
- **High-Level Coordination**: Manages the full bisection workflow
- **Component Integration**: Coordinates parser, bisector, UI components
- **Parameter Management**: Handles complex parameter passing and validation
- **Workflow Abstraction**: Separates workflow logic from UI concerns

### 9. Validation (validation.py) - NEW FEATURE
- **Reference Validation**: Comprehensive git reference checking
- **Smart Swapping**: Detects and offers to fix swapped good/bad refs
- **Version Intelligence**: Understands semantic versioning patterns
- **User Guidance**: Provides helpful suggestions for common mistakes

### 10. CLI Display (cli_display.py) - NEW FEATURE
- **Modular UI**: Separated display logic from business logic
- **Rich Formatting**: Professional tables, panels, and progress displays
- **Confirmation Dialogs**: Standardized user confirmation patterns
- **Reusable Components**: Shared display utilities across modules

## Key Features

### Current Functionality
1. **Automated Bisection**: Full git bisect automation with minimal user input
2. **Interactive UI**: Smart prompts with tab completion and validation
3. **PEP 723 Integration**: Native support for inline script metadata
4. **Repository Auto-detection**: Automatic discovery of package git repositories
5. **Reference Validation**: Smart detection and fixing of swapped good/bad refs with suggestions
6. **Fuzzy Completion**: Advanced autocompletion for git references
7. **End State Options**: Post-bisection menu for re-running with different parameters (NEW)
8. **Optimized Performance**: Efficient repository operations with blob filtering (NEW)
9. **Error Intelligence**: Smart error summarization and full traceback options (NEW)
10. **Modular Architecture**: Clean separation of concerns for maintainability (NEW)
11. **CI/CD Integration**: GitHub Actions workflow for testing
12. **Cross-platform**: Works on macOS, Linux, and Windows

### Usage Patterns
```bash
# Full interactive mode
script-bisect script.py

# Semi-interactive (prompts for missing refs)
script-bisect script.py pandas

# Minimal interaction (prompts for bad ref only)
script-bisect script.py pandas v1.0.0

# Full specification (no prompts)
script-bisect script.py pandas v1.0.0 v2.0.0

# Advanced options
script-bisect script.py pandas v1.0.0 main --inverse --verbose
```

## Testing Strategy

### Test Coverage
- **Unit Tests**: Comprehensive coverage of all modules
- **Integration Tests**: End-to-end workflow testing
- **Interactive Tests**: Custom completion and validation testing
- **Fixture-based**: Realistic test scripts and scenarios
- **Mock Integration**: Git operations and external API calls

### Quality Assurance
- **Pre-commit Hooks**: Automated formatting, linting, and validation
- **Type Checking**: Full mypy coverage with strict mode
- **Security Scanning**: Bandit for security vulnerability detection
- **Spell Checking**: Documentation and code comment validation

### CI/CD Pipeline
- **GitHub Actions**: Automated testing on Ubuntu with Python 3.12/3.13
- **Matrix Testing**: Multiple Python versions and platforms
- **Coverage Reporting**: Code coverage tracking and reporting
- **Dependency Caching**: Fast builds with uv caching

## Recent Major Improvements

### Phase 1: Interactive UI System (Previously Implemented)
The first major update added a complete interactive UI system that transforms the user experience:

### Phase 2: End State Options & Modular Refactoring (NEWLY IMPLEMENTED)
The latest major enhancement adds comprehensive post-bisection workflow options with significant architectural improvements:

#### Before (Rigid CLI)
```bash
# Required all parameters upfront
script-bisect script.py package good_ref bad_ref
```

#### After (Smart Interactive)
```bash
# Adapts to what user provides
script-bisect script.py                    # Prompts for everything
script-bisect script.py pandas             # Prompts for refs only
script-bisect script.py pandas v1.0.0      # Prompts for bad ref only
```

### Technical Achievements
1. **Advanced Tab Completion**: Custom fuzzy matching handles edge cases like `v2025.09.` → `v2025.09.0`
2. **Smart Validation**: Detects and offers to fix swapped good/bad references
3. **Git Integration**: Automatically fetches and prioritizes recent version tags
4. **Context Preservation**: Shows previously entered values when prompting for missing ones
5. **Professional UX**: Rich formatting, colored output, and confirmation dialogs

## Planned Future Features

### GitHub Issue Integration (Ambitious Roadmap)
We've planned a sophisticated feature to extract and test scripts directly from GitHub issues:

#### Core Components Needed
1. **Issue Parser**: Extract code blocks from GitHub issue URLs/comments
2. **Script Detection**: AI-powered identification of likely test scripts
3. **Metadata Generation**: Auto-populate PEP 723 metadata when missing
4. **User Selection**: Interactive selection of correct code blocks
5. **Script Editor**: Launch external editor (vim) for script refinement
6. **Dependency Detection**: Automatic dependency discovery and addition
7. **Smart Testing**: Iterative testing with dependency resolution

#### Technical Challenges
- **Content Extraction**: Reliable parsing of GitHub's API and HTML
- **Code Classification**: Distinguishing test scripts from example code
- **Dependency Resolution**: Smart detection of missing packages
- **Editor Integration**: Cross-platform external editor support
- **Error Recovery**: Handling malformed or incomplete scripts

#### Workflow Vision
```bash
# Point at GitHub issue
script-bisect --issue https://github.com/pandas/pandas/issues/12345

# Tool automatically:
# 1. Fetches issue content
# 2. Identifies code blocks
# 3. Prompts user to select correct script
# 4. Launches editor for refinement
# 5. Auto-adds missing dependencies
# 6. Runs bisection
```

## Development Workflow

### Code Standards
- **Python 3.12+**: Modern Python features and syntax
- **Type Hints**: Full type annotation coverage
- **Docstrings**: Comprehensive documentation for all functions
- **Error Handling**: Proper exception management and user feedback

### Git Practices
- **Conventional Commits**: Structured commit messages with co-authorship
- **Pre-commit Validation**: All code must pass quality checks
- **Branch Protection**: Main branch protected with required checks
- **Detailed Descriptions**: Comprehensive commit messages explaining changes

### Dependencies Management
- **uv**: Modern, fast Python package management
- **Minimal Dependencies**: Carefully curated dependency list
- **Version Pinning**: Specific version requirements for stability
- **Optional Dependencies**: Development tools as optional extras

## Maintenance Notes

### Code Health
- **Metrics**: 44/46 tests passing (2 pre-existing issues unrelated to new features)
- **Coverage**: Comprehensive test coverage with new interactive UI tests
- **Quality**: All linting, formatting, and type checking passes
- **Documentation**: Inline code documentation and comprehensive README

### Future Maintenance
- **Dependency Updates**: Regular updates to prompt-toolkit, rich, etc.
- **Python Version Support**: Maintain compatibility with latest Python versions
- **Platform Testing**: Ensure cross-platform compatibility
- **Security Updates**: Regular security scanning and updates

This project represents a sophisticated CLI tool that balances powerful automation with exceptional user experience, setting the foundation for even more ambitious features like GitHub issue integration.
