"""Integration tests that run the full bisection process."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.slow
@pytest.mark.integration
def test_xarray_bisection_finds_correct_commit():
    """Integration test: Run full bisection on xarray example and verify correct commit is found.

    This test runs the actual script-bisect command on the xarray example and verifies
    that it finds the known regression commit: a13a2556a29b3c5ba342a402b2598bab42939b46
    """
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    # The known commits from the xarray example documentation
    good_ref = "v2025.08.0"
    bad_ref = "v2025.09.0"
    expected_commit = "a13a2556a29b3c5ba342a402b2598bab42939b46"

    try:
        # Run the full bisection process
        cmd = [
            "uv",
            "run",
            "script-bisect",
            str(example_path),
            "xarray",
            good_ref,
            bad_ref,
            "--verbose",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout for full bisection
            cwd=Path(__file__).parent.parent,
        )

        # Bisection should succeed
        assert result.returncode == 0, (
            f"Bisection failed with return code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Should find the expected commit in the output
        assert expected_commit in result.stdout, (
            f"Expected commit {expected_commit} not found in output:\n"
            f"STDOUT: {result.stdout}"
        )

        # Should show success message
        assert (
            "✨ Bisection completed successfully!" in result.stdout
        ), f"Success message not found in output:\n{result.stdout}"

        # Should mention it found the first bad commit
        assert (
            "Found first bad commit" in result.stdout
        ), f"First bad commit message not found in output:\n{result.stdout}"

    except FileNotFoundError:
        pytest.skip("uv not found - skipping integration test")
    except subprocess.TimeoutExpired:
        pytest.fail("Bisection process timed out after 10 minutes")


@pytest.mark.slow
@pytest.mark.integration
def test_bisection_dry_run_mode():
    """Test that dry run mode shows what would be done without actually doing it."""
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    try:
        cmd = [
            "uv",
            "run",
            "script-bisect",
            str(example_path),
            "xarray",
            "v2025.08.0",
            "v2025.09.0",
            "--dry-run",
            "--verbose",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent,
        )

        # Dry run should succeed quickly
        assert result.returncode == 0, f"Dry run failed: {result.stderr}"

        # Should show dry run message
        assert "Dry run mode - no actual bisection will be performed" in result.stdout

        # Should show bisection summary
        assert "Bisection Summary" in result.stdout
        assert "xarray" in result.stdout
        assert "v2025.08.0" in result.stdout
        assert "v2025.09.0" in result.stdout

    except FileNotFoundError:
        pytest.skip("uv not found - skipping integration test")


@pytest.mark.integration
def test_bisection_with_invalid_package():
    """Test that bisection fails gracefully with helpful error for invalid package."""
    example_path = Path(__file__).parent.parent / "examples" / "xarray_dtype_issue.py"

    try:
        cmd = [
            "uv",
            "run",
            "script-bisect",
            str(example_path),
            "nonexistent_package",  # Package not in the script
            "v1.0.0",
            "v2.0.0",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        # Should fail with exit code 1
        assert result.returncode == 1

        # Should show helpful error message
        assert "not found in script dependencies" in result.stdout

        # Should list available packages
        assert "Available packages:" in result.stdout
        assert "xarray" in result.stdout
        assert "numpy" in result.stdout
        assert "pandas" in result.stdout

    except FileNotFoundError:
        pytest.skip("uv not found - skipping integration test")


@pytest.mark.integration
def test_bisection_help_command():
    """Test that help command works correctly."""
    try:
        result = subprocess.run(
            ["uv", "run", "script-bisect", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Bisect package versions in PEP 723 Python scripts" in result.stdout
        assert "SCRIPT" in result.stdout
        assert "PACKAGE" in result.stdout
        assert "GOOD_REF" in result.stdout
        assert "BAD_REF" in result.stdout

    except FileNotFoundError:
        pytest.skip("uv not found - skipping integration test")
