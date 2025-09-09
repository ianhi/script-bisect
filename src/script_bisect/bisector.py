"""Git bisect orchestration for script-bisect."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .exceptions import GitError, RepositoryError
from .parser import ScriptParser
from .runner import TestRunner
from .utils import create_temp_dir, format_commit_info, safe_filename


logger = logging.getLogger(__name__)
console = Console()


class BisectResult:
    """Result of a git bisect operation."""
    
    def __init__(
        self,
        found_commit: str | None = None,
        commit_info: dict[str, Any] | None = None,
        is_regression: bool = True,
        steps_taken: int = 0,
    ) -> None:
        self.found_commit = found_commit
        self.commit_info = commit_info or {}
        self.is_regression = is_regression
        self.steps_taken = steps_taken
    
    @property
    def success(self) -> bool:
        """Whether bisection found a clear result."""
        return self.found_commit is not None


class GitBisector:
    """Orchestrates git bisect operations for PEP 723 scripts."""
    
    def __init__(
        self,
        script_path: Path,
        package: str,
        repo_url: str,
        good_ref: str,
        bad_ref: str,
        test_command: str | None = None,
        clone_dir: Path | None = None,
        keep_clone: bool = False,
        inverse: bool = False,
    ) -> None:
        """Initialize the git bisector.
        
        Args:
            script_path: Path to the PEP 723 script
            package: Name of the package to bisect
            repo_url: Git repository URL
            good_ref: Git reference for the good commit
            bad_ref: Git reference for the bad commit
            test_command: Custom test command (default: uv run script)
            clone_dir: Directory for repository clone (default: temp)
            keep_clone: Whether to keep the cloned repository
            inverse: Whether to find when something was fixed (not broken)
        """
        self.script_path = script_path
        self.package = package
        self.repo_url = repo_url
        self.good_ref = good_ref
        self.bad_ref = bad_ref
        self.test_command = test_command
        self.clone_dir = clone_dir or create_temp_dir("script_bisect_repo_")
        self.keep_clone = keep_clone
        self.inverse = inverse
        
        # Initialize components
        self.parser = ScriptParser(script_path)
        self.repo: git.Repo | None = None
        self.test_runner: TestRunner | None = None
    
    def run(self) -> BisectResult:
        """Run the complete bisection process.
        
        Returns:
            BisectResult containing the outcome
            
        Raises:
            GitError: If there's an error with git operations
            RepositoryError: If there's an error with the repository
        """
        try:
            # Step 1: Clone the repository
            self._clone_repository()
            
            # Step 2: Validate refs
            self._validate_refs()
            
            # Step 3: Set up test runner
            self._setup_test_runner()
            
            # Step 4: Run bisection
            result = self._run_bisection()
            
            return result
            
        finally:
            self._cleanup()
    
    def _clone_repository(self) -> None:
        """Clone the repository for bisection."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cloning repository...", total=None)
            
            try:
                # Clean the URL for git clone
                clone_url = self.repo_url
                if clone_url.startswith("git+"):
                    clone_url = clone_url[4:]  # Remove git+ prefix
                
                logger.info(f"Cloning {clone_url} to {self.clone_dir}")
                self.repo = git.Repo.clone_from(clone_url, self.clone_dir)
                
                progress.update(task, description="✅ Repository cloned")
                
            except Exception as e:
                raise RepositoryError(f"Failed to clone repository: {e}") from e
    
    def _validate_refs(self) -> None:
        """Validate that the good and bad refs exist in the repository."""
        if not self.repo:
            raise RepositoryError("Repository not initialized")
        
        try:
            # Check if refs exist
            good_commit = self.repo.commit(self.good_ref)
            bad_commit = self.repo.commit(self.bad_ref)
            
            console.print(f"✅ Good ref '{self.good_ref}' → {good_commit.hexsha[:12]}")
            console.print(f"❌ Bad ref '{self.bad_ref}' → {bad_commit.hexsha[:12]}")
            
        except git.BadName as e:
            raise GitError(f"Invalid git reference: {e}") from e
    
    def _setup_test_runner(self) -> None:
        """Set up the test runner for bisection."""
        self.test_runner = TestRunner(
            script_path=self.script_path,
            package=self.package,
            repo_url=self.repo_url,
            test_command=self.test_command,
        )
    
    def _run_bisection(self) -> BisectResult:
        """Run the git bisect process."""
        if not self.repo or not self.test_runner:
            raise RepositoryError("Bisector not properly initialized")
        
        console.print("\\n[bold blue]🔄 Starting bisection...[/bold blue]")
        
        try:
            # Start git bisect
            self.repo.git.bisect("start")
            
            # Mark good and bad commits
            self.repo.git.bisect("good", self.good_ref)
            self.repo.git.bisect("bad", self.bad_ref)
            
            # Create test script for bisect run
            test_script_path = self._create_bisect_test_script()
            
            # Run git bisect with our test script
            console.print("Running automated bisection...")
            
            try:
                # Run git bisect run with our test script
                result = self.repo.git.bisect("run", str(test_script_path))
                
                # Parse the result
                if "is the first bad commit" in result:
                    # Extract commit hash from result
                    lines = result.split('\\n')
                    commit_line = next((line for line in lines if "is the first bad commit" in line), "")
                    if commit_line:
                        commit_hash = commit_line.split()[0]
                        commit_info = self._get_commit_info(commit_hash)
                        
                        console.print(f"\\n[green]✨ Found problematic commit: {commit_hash[:12]}[/green]")
                        console.print(format_commit_info(**commit_info))
                        
                        return BisectResult(
                            found_commit=commit_hash,
                            commit_info=commit_info,
                            is_regression=not self.inverse,
                        )
                
                console.print("[yellow]⚠️ Bisection completed but no clear result[/yellow]")
                return BisectResult()
                
            except git.GitCommandError as e:
                # Check if bisect is in progress and handle appropriately
                if "bisect run failed" in str(e):
                    console.print("[red]❌ Bisection failed - test script issues[/red]")
                else:
                    console.print(f"[red]❌ Git bisect error: {e}[/red]")
                return BisectResult()
        
        except Exception as e:
            raise GitError(f"Bisection failed: {e}") from e
        
        finally:
            # Always reset bisect state
            try:
                self.repo.git.bisect("reset")
            except Exception:
                pass  # Ignore errors during cleanup
    
    def _create_bisect_test_script(self) -> Path:
        """Create a test script for git bisect run.
        
        Returns:
            Path to the created test script
        """
        if not self.repo or not self.test_runner:
            raise RepositoryError("Bisector not properly initialized")
        
        # Create test script content
        test_script_content = f'''#!/usr/bin/env python3
"""Test script for git bisect run."""

import sys
import subprocess
from pathlib import Path

def main():
    # Get current commit
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd="{self.repo.working_dir}",
            text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        print(f"Failed to get current commit: {{e}}")
        sys.exit(125)  # Skip this commit
    
    # Test this commit
    from script_bisect.runner import TestRunner
    
    runner = TestRunner(
        script_path=Path("{self.script_path}"),
        package="{self.package}",
        repo_url="{self.repo_url}",
        test_command={repr(self.test_command)},
    )
    
    try:
        success = runner.test_commit(commit)
        
        # Return appropriate exit code
        if {self.inverse}:
            # Inverse mode: good if test fails, bad if test passes
            sys.exit(0 if not success else 1)
        else:
            # Normal mode: good if test passes, bad if test fails
            sys.exit(0 if success else 1)
            
    except Exception as e:
        print(f"Test failed with error: {{e}}")
        sys.exit(125)  # Skip this commit

if __name__ == "__main__":
    main()
'''
        
        # Write test script
        test_script_path = self.clone_dir / "bisect_test.py"
        test_script_path.write_text(test_script_content)
        test_script_path.chmod(0o755)  # Make executable
        
        return test_script_path
    
    def _get_commit_info(self, commit_hash: str) -> dict[str, Any]:
        """Get detailed information about a commit.
        
        Args:
            commit_hash: The commit hash
            
        Returns:
            Dictionary with commit information
        """
        if not self.repo:
            return {}
        
        try:
            commit = self.repo.commit(commit_hash)
            return {
                "commit_hash": commit.hexsha,
                "author": f"{commit.author.name} <{commit.author.email}>",
                "date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "message": commit.message.split('\\n')[0],  # First line only
            }
        except Exception:
            return {"commit_hash": commit_hash}
    
    def _cleanup(self) -> None:
        """Clean up resources after bisection."""
        if not self.keep_clone and self.clone_dir.exists():
            try:
                shutil.rmtree(self.clone_dir)
                logger.debug(f"Cleaned up clone directory: {self.clone_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up clone directory: {e}")
        elif self.keep_clone:
            console.print(f"[dim]📁 Repository kept at: {self.clone_dir}[/dim]")