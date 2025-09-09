"""Test runner for script-bisect bisection."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

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
        timeout: int = 300,
    ) -> None:
        """Initialize the test runner.
        
        Args:
            script_path: Path to the original PEP 723 script
            package: Name of the package being bisected
            repo_url: Git repository URL
            test_command: Custom test command (default: uv run script)
            timeout: Test timeout in seconds
        """
        self.script_path = script_path
        self.package = package
        self.repo_url = repo_url
        self.test_command = test_command
        self.timeout = timeout
        
        self.parser = ScriptParser(script_path)
    
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
                self.package, 
                self.repo_url, 
                commit_hash
            )
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(modified_content)
                temp_script_path = Path(temp_file.name)
            
            try:
                # Run the test
                success = self._run_test(temp_script_path)
                logger.debug(f"Commit {commit_hash[:12]} test result: {'PASS' if success else 'FAIL'}")
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
        """Run the test for a script.
        
        Args:
            script_path: Path to the script to test
            
        Returns:
            True if test passes, False otherwise
        """
        if self.test_command:
            # Use custom test command
            command = self.test_command.format(script=script_path)
            cmd = command.split()
        else:
            # Default: uv run script
            cmd = ["uv", "run", str(script_path)]
        
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
            
            # Test passes if exit code is 0
            return result.returncode == 0
            
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
    
    def validate_test_setup(self) -> bool:
        """Validate that the test setup is correct.
        
        Returns:
            True if setup is valid, False otherwise
        """
        try:
            # Check if uv is available
            subprocess.run(
                ["uv", "--version"], 
                capture_output=True, 
                check=True,
                timeout=10
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False