"""Test runner for script-bisect bisection."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from .auto_dependency_fixer import AutoDependencyFixer
from .exceptions import ExecutionError
from .parser import ScriptParser

logger = logging.getLogger(__name__)


class TestRunner:
    """Runs tests for individual commits during bisection."""

    def __init__(
        self,
        script_path: Path,
        package: str,
        repo_url: str,
        test_command: str | None = None,
        timeout: int = 120,
    ) -> None:
        """Initialize the test runner.

        Args:
            script_path: Path to the original PEP 723 script
            package: Name of the package being bisected
            repo_url: Git repository URL
            test_command: Custom test command (default: uv run script)
            timeout: Test timeout in seconds (default: 120)
        """
        self.script_path = script_path
        self.package = package
        self.repo_url = repo_url
        self.test_command = test_command
        self.timeout = timeout

        self.parser = ScriptParser(script_path)
        self.dependency_fixer = AutoDependencyFixer()

    def test_commit(self, commit_hash: str) -> bool:
        """Test a specific commit.

        Args:
            commit_hash: The git commit hash to test

        Returns:
            True if the test passes, False if it fails

        Raises:
            ExecutionError: If there's an error running the test
        """
        logger.debug(f"Testing commit {commit_hash[:12]}")

        try:
            # Create modified script with the specific commit
            modified_content = self.parser.update_git_reference(
                self.package, self.repo_url, commit_hash
            )

            # Write to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(modified_content)
                temp_script_path = Path(temp_file.name)

            try:
                # Run the test
                success = self._run_test(temp_script_path)
                logger.debug(
                    f"Commit {commit_hash[:12]} test result: {'PASS' if success else 'FAIL'}"
                )
                return success

            finally:
                # Clean up temporary file
                try:
                    temp_script_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")

        except Exception as e:
            raise ExecutionError(f"Failed to test commit {commit_hash}: {e}") from e

    def _run_test(self, script_path: Path) -> bool:
        """Run the test for a script with automatic dependency fixing.

        Args:
            script_path: Path to the script to test

        Returns:
            True if test passes, False otherwise
        """
        current_script = script_path
        max_retries = 3  # Prevent infinite loops
        retries = 0
        previous_temp_script = None  # Track previous temp script for cleanup

        try:
            while retries <= max_retries:
                if self.test_command:
                    # Use custom test command
                    command = self.test_command.format(script=current_script)
                    cmd = command.split()
                else:
                    # Default: uv run script
                    cmd = ["uv", "run", str(current_script)]

                try:
                    logger.debug(f"Running command: {' '.join(cmd)}")

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        check=False,  # Don't raise on non-zero exit
                    )

                    # Log output for debugging
                    if result.stdout:
                        logger.debug(f"STDOUT: {result.stdout[:500]}")
                    if result.stderr:
                        logger.debug(f"STDERR: {result.stderr[:500]}")

                    # If test passes, we're done
                    if result.returncode == 0:
                        return True

                    # If test fails, check for dependency issues (allow multiple rounds)
                    if retries < max_retries:
                        error_output = result.stdout + "\n" + result.stderr

                        fixed_script, should_retry = (
                            self.dependency_fixer.fix_and_retry(
                                current_script, error_output
                            )
                        )

                        if should_retry and fixed_script:
                            # Clean up previous temp script if it exists
                            if (
                                previous_temp_script
                                and previous_temp_script != script_path
                            ):
                                self.dependency_fixer.cleanup_temp_script(
                                    previous_temp_script, script_path
                                )

                            # Track current script for potential cleanup next iteration
                            if current_script != script_path:
                                previous_temp_script = current_script

                            current_script = fixed_script
                            retries += 1
                            continue  # Retry with fixed script

                    # Test failed and no more retries - show failure output for debugging
                    if result.stdout or result.stderr:
                        from rich.console import Console

                        console = Console()
                        console.print(
                            f"[red]💥 Test failed (exit code {result.returncode})[/red]"
                        )
                        if result.stdout:
                            console.print("[yellow]📤 STDOUT:[/yellow]")
                            console.print(
                                result.stdout[:1000]
                                + ("..." if len(result.stdout) > 1000 else "")
                            )
                        if result.stderr:
                            console.print("[yellow]📤 STDERR:[/yellow]")
                            console.print(
                                result.stderr[:1000]
                                + ("..." if len(result.stderr) > 1000 else "")
                            )

                    return False

                except subprocess.TimeoutExpired:
                    logger.warning(f"Test timed out after {self.timeout} seconds")
                    return False
                except FileNotFoundError as e:
                    if "uv" in str(e):
                        raise ExecutionError(
                            "uv not found. Please install uv (https://docs.astral.sh/uv/)"
                        ) from e
                    raise ExecutionError(f"Command not found: {e}") from e
                except Exception as e:
                    logger.warning(f"Test execution failed: {e}")
                    return False

        finally:
            # Clean up any remaining temp scripts
            if previous_temp_script and previous_temp_script != script_path:  # type: ignore
                self.dependency_fixer.cleanup_temp_script(
                    previous_temp_script, script_path
                )
            if current_script != script_path and current_script != previous_temp_script:  # type: ignore
                self.dependency_fixer.cleanup_temp_script(current_script, script_path)

        return False

    def validate_test_setup(self) -> bool:
        """Validate that the test setup is correct.

        Returns:
            True if setup is valid, False otherwise
        """
        try:
            # Check if uv is available
            subprocess.run(
                ["uv", "--version"], capture_output=True, check=True, timeout=10
            )
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return False
