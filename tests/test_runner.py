"""Tests for the test runner."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from script_bisect.exceptions import ExecutionError
from script_bisect.runner import TestRunner

if TYPE_CHECKING:
    from pathlib import Path


class TestTestRunner:
    """Tests for the TestRunner class."""

    def test_runner_initialization(self, tmp_path: Path) -> None:
        """Test test runner initialization."""
        script_path = tmp_path / "test_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
            timeout=60,
        )

        assert runner.script_path == script_path
        assert runner.package == "requests"
        assert runner.repo_url == "git+https://github.com/psf/requests.git"
        assert runner.timeout == 60

    @patch("subprocess.run")
    def test_successful_test(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test a successful test execution."""
        # Mock successful subprocess run
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        script_path = tmp_path / "success_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests@git+https://github.com/psf/requests.git@main"]
# ///

import requests
print("Success")
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
        )

        result = runner.test_commit("abc123")

        assert result is True
        mock_run.assert_called_once()

        # Verify the command was called with uv run
        args, kwargs = mock_run.call_args
        assert args[0][:2] == ["uv", "run"]

    @patch("subprocess.run")
    def test_failed_test(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test a failed test execution."""
        # Mock failed subprocess run
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error occurred")

        script_path = tmp_path / "fail_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests@git+https://github.com/psf/requests.git@main"]
# ///

raise RuntimeError("This should fail")
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
        )

        result = runner.test_commit("def456")

        assert result is False

    @patch("subprocess.run")
    def test_custom_test_command(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test using a custom test command."""
        mock_run.return_value = Mock(returncode=0, stdout="Test passed", stderr="")

        script_path = tmp_path / "custom_script.py"
        script_path.write_text("""# /// script
# dependencies = ["pytest", "requests@git+https://github.com/psf/requests.git@main"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
            test_command="pytest {script}",
        )

        result = runner.test_commit("ghi789")

        assert result is True

        # Verify custom command was used
        args, kwargs = mock_run.call_args
        assert "pytest" in args[0][0]

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test handling of test timeouts."""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(["uv", "run"], 5)

        script_path = tmp_path / "timeout_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests@git+https://github.com/psf/requests.git@main"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
            timeout=5,
        )

        result = runner.test_commit("timeout123")

        assert result is False

    @patch("subprocess.run")
    def test_uv_not_found(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test handling when uv is not found."""
        mock_run.side_effect = FileNotFoundError("uv not found")

        script_path = tmp_path / "no_uv_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests@git+https://github.com/psf/requests.git@main"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
        )

        with pytest.raises(ExecutionError, match="uv not found"):
            runner.test_commit("nouv123")

    @patch("subprocess.run")
    def test_validate_test_setup_success(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test successful test setup validation."""
        mock_run.return_value = Mock(returncode=0, stdout="uv 0.1.0")

        script_path = tmp_path / "validate_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
        )

        assert runner.validate_test_setup() is True
        mock_run.assert_called_once_with(
            ["uv", "--version"], capture_output=True, check=True, timeout=10
        )

    @patch("subprocess.run")
    def test_validate_test_setup_failure(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test failed test setup validation."""
        mock_run.side_effect = FileNotFoundError()

        script_path = tmp_path / "validate_fail_script.py"
        script_path.write_text("""# /// script
# dependencies = ["requests"]
# ///
""")

        runner = TestRunner(
            script_path=script_path,
            package="requests",
            repo_url="git+https://github.com/psf/requests.git",
        )

        assert runner.validate_test_setup() is False
