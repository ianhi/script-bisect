"""Tests for example scripts included with script-bisect."""

import subprocess
from pathlib import Path


def test_xarray_example_has_valid_pep723_metadata():
    """Test that the xarray example has valid PEP 723 metadata."""
    from script_bisect.parser import ScriptParser

    # Path to the xarray example
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    # Should be able to parse without errors
    parser = ScriptParser(example_path)

    # Should find the xarray package
    assert parser.has_package("xarray")

    # Should have proper metadata
    available_packages = parser.get_available_packages()
    expected_packages = {"xarray", "pandas", "numpy"}
    assert set(available_packages) == expected_packages

    # Should be able to extract repository URL
    repo_url = parser.get_repository_url("xarray")
    assert repo_url is not None
    assert "github.com/pydata/xarray" in repo_url


def test_xarray_example_syntax_is_valid():
    """Test that the xarray example script has valid Python syntax."""
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    # Should compile without syntax errors
    with Path.open(example_path, encoding="utf-8") as f:
        content = f.read()

    # This will raise SyntaxError if the file has syntax errors
    compile(content, str(example_path), "exec")


def test_xarray_example_can_run_with_uv():
    """Test that the xarray example can be executed with uv run (integration test)."""
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    # Try to run with uv - this is an integration test that requires uv to be installed
    # We don't assert on the exit code since the test might fail due to the actual bug
    # being tested, but we want to ensure it can be executed
    try:
        result = subprocess.run(
            ["uv", "run", str(example_path)],
            capture_output=True,
            text=True,
            timeout=60,  # Reasonable timeout for dependency installation
        )

        # Should either succeed or fail cleanly (no syntax errors, import errors, etc.)
        # The actual test result depends on which version of xarray gets resolved
        assert (
            result.returncode in (0, 1)
        ), f"Unexpected return code: {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Should produce some output (version information and test results)
        assert len(result.stdout) > 100, "Expected substantial output from the test"

        # Should mention xarray version
        assert (
            "xarray:" in result.stdout
        ), "Expected xarray version information in output"

    except FileNotFoundError:
        # Skip the test if uv is not available
        import pytest

        pytest.skip("uv not found - skipping integration test")
    except subprocess.TimeoutExpired:
        # If it times out, that's also a problem
        raise AssertionError(
            "Test execution timed out - may indicate hanging dependencies"
        )
