# Development Agents Guide

This document outlines the development approach and AI agent collaboration patterns used to build `uv-bisect`.

## Project Overview

`uv-bisect` is a tool that combines PEP 723 inline script metadata with git bisect to automatically find problematic commits in Python package dependencies. It dynamically modifies script metadata and uses `uv run` to test different package versions.

## Development Philosophy

### Clean Code Principles
- **Type safety**: All functions have proper type hints
- **Error handling**: Custom exceptions with clear messages
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: Unit tests, integration tests, and property-based testing
- **Code quality**: Pre-commit hooks with ruff, mypy, and other linters

### User Experience Focus
- **Clear terminal output**: Rich formatting with progress bars and status updates
- **Interactive prompts**: Helpful defaults and validation
- **Graceful error handling**: Informative error messages with recovery suggestions
- **Safety first**: No destructive operations without confirmation

## Agent Collaboration Patterns

### 1. Planning Agent
**Role**: High-level architecture and feature planning
- Researches PEP 723 specifications and git bisect workflows  
- Designs API interfaces and CLI interactions
- Creates implementation roadmap with clear milestones
- Documents design decisions and trade-offs

### 2. Implementation Agent  
**Role**: Core feature development
- Implements parser for PEP 723 metadata manipulation
- Creates git bisect orchestration logic
- Builds CLI interface with rich terminal output
- Writes comprehensive error handling and logging

### 3. Testing Agent
**Role**: Quality assurance and validation
- Creates unit tests for all components
- Builds integration tests with mock repositories
- Develops property-based tests for edge cases
- Sets up CI/CD pipeline and coverage reporting

### 4. Documentation Agent
**Role**: User-facing documentation and examples
- Writes clear README with usage examples
- Creates troubleshooting guides
- Documents API interfaces and internal architecture
- Maintains changelog and release notes

## Technical Architecture

### Core Components

#### 1. CLI Interface (`cli.py`)
- Click-based command interface
- Rich terminal output with progress indicators
- Interactive prompts for missing parameters
- Proper argument validation and help text

#### 2. PEP 723 Parser (`parser.py`)
- Extracts and validates inline script metadata
- Updates git references while preserving formatting
- Handles various dependency specification formats
- Provides clear error messages for malformed metadata

#### 3. Git Bisect Orchestrator (`bisector.py`)
- Manages repository cloning and cleanup
- Coordinates git bisect workflow
- Creates test wrapper scripts
- Handles bisection state and results

#### 4. Test Runner (`runner.py`)
- Executes modified scripts with uv
- Captures and interprets exit codes
- Handles timeouts and resource cleanup
- Provides detailed execution logs

### Error Handling Strategy

#### Custom Exception Hierarchy
```python
class UvBisectError(Exception): ...
class ParseError(UvBisectError): ...
class GitError(UvBisectError): ...
class ExecutionError(UvBisectError): ...
```

#### Recovery Patterns
- **Auto-detection**: Fallback to PyPI metadata for repository URLs
- **Validation**: Pre-flight checks before destructive operations  
- **Cleanup**: Context managers for temporary files and processes
- **User guidance**: Clear error messages with suggested fixes

## Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/new-functionality

# Install development dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install

# Develop with type checking
uv run mypy src/
```

### 2. Testing Strategy
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=uv_bisect --cov-report=html

# Run specific test types
uv run pytest -m "not slow"           # Fast tests only
uv run pytest -m integration          # Integration tests
```

### 3. Quality Assurance
```bash
# Format and lint
uv run ruff check --fix
uv run ruff format

# Type checking
uv run mypy src/

# Security scanning
uv run bandit -r src/

# Pre-commit validation
uv run pre-commit run --all-files
```

## Collaboration Guidelines

### Code Review Checklist
- [ ] Type hints on all functions and methods
- [ ] Docstrings with examples for public APIs
- [ ] Error handling with specific exception types
- [ ] Tests covering happy path and edge cases
- [ ] Rich terminal output with clear status messages
- [ ] Proper resource cleanup (files, processes, git repos)

### Documentation Standards
- **API Documentation**: Docstrings with parameter types and examples
- **User Documentation**: Clear usage examples with expected output
- **Developer Documentation**: Architecture decisions and extension points
- **Error Documentation**: Troubleshooting guide for common issues

### Testing Standards
- **Unit Tests**: Test individual functions in isolation
- **Integration Tests**: Test component interactions with mock repositories
- **End-to-End Tests**: Test complete workflows with real examples
- **Property Tests**: Use Hypothesis for edge case discovery

## AI Agent Prompts

### For Implementation Tasks
```
Context: Working on uv-bisect, a tool for bisecting package versions in PEP 723 scripts
Requirements: 
- Use type hints throughout
- Handle errors gracefully with custom exceptions
- Use rich for terminal output
- Write comprehensive docstrings
- Follow the existing code patterns

Task: [specific implementation request]
```

### For Testing Tasks  
```
Context: Testing uv-bisect functionality
Requirements:
- Test both happy path and error cases
- Use pytest fixtures for common setup
- Mock external dependencies (git, subprocess)
- Ensure good test coverage
- Use descriptive test names

Task: [specific testing request]
```

This collaborative approach ensures consistent code quality, comprehensive testing, and maintainable architecture throughout the project lifecycle.