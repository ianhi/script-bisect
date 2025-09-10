"""Centralized repository management for efficient Git operations.

This module provides a centralized way to handle all Git repository interactions
with optimal performance by minimizing network requests and using efficient
Git operations.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import git
from rich.progress import Progress, SpinnerColumn, TextColumn

from .cache_system import get_cache

if TYPE_CHECKING:
    from git import Repo

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manages Git repository operations with optimized performance.

    This class centralizes all Git operations to minimize remote fetches
    and uses efficient blob-filtering to reduce bandwidth usage.
    """

    def __init__(self, repo_url: str) -> None:
        """Initialize the repository manager.

        Args:
            repo_url: The Git repository URL (with or without git+ prefix)
        """
        # Clean the URL for git operations
        self.repo_url = repo_url
        if repo_url.startswith("git+"):
            self.clone_url = repo_url[4:]  # Remove git+ prefix
        else:
            self.clone_url = repo_url

        self.repo: Repo | None = None
        self.clone_dir: Path | None = None

    def setup_repository(self, good_ref: str, bad_ref: str) -> Path:
        """Set up a local repository optimized for bisection.

        This method performs all necessary Git operations in the most efficient way:
        1. Checks cache for existing repository
        2. Creates a bare clone (no working directory initially) if not cached
        3. Fetches only the required refs with blob filtering
        4. Sets up sparse checkout to minimize disk usage
        5. Stores in cache for future use
        6. Returns the repository path for bisection operations

        Args:
            good_ref: The known good reference (commit, tag, or branch)
            bad_ref: The known bad reference (commit, tag, or branch)

        Returns:
            Path to the optimized local repository

        Raises:
            git.GitCommandError: If any Git operation fails
        """
        cache = get_cache()
        
        # Check if we have a cached repository
        cached_repo = cache.cache_repository(self.repo_url, good_ref, bad_ref)
        if cached_repo:
            logger.info("Using cached repository, updating with latest refs...")
            # Copy cached repository to a temporary location for use
            self.clone_dir = Path(tempfile.mkdtemp(prefix="script_bisect_repo_"))
            shutil.copytree(cached_repo, self.clone_dir)
            self.repo = git.Repo(self.clone_dir)
            
            # Update the cached repo with latest refs to catch new commits
            try:
                logger.debug("Fetching latest refs to update cache...")
                # Fetch specific refs and any new commits between them
                self.repo.git.fetch("origin", good_ref, bad_ref, "--filter=blob:none")
                try:
                    # Also try to fetch the range to get any new commits
                    self.repo.git.fetch("origin", f"{good_ref}..{bad_ref}", "--filter=blob:none")
                except git.GitCommandError:
                    logger.debug("Range fetch failed, using individual refs")
            except git.GitCommandError as e:
                logger.warning(f"Failed to update cached repository: {e}")
                # Continue with cached version if update fails
            
            return self.clone_dir

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=None,  # Use default console
            transient=True,
        ) as progress:
            # Create temporary directory for the repository
            self.clone_dir = Path(tempfile.mkdtemp(prefix="script_bisect_repo_"))

            task = progress.add_task("Setting up repository...", total=None)

            try:
                # Step 1: Initialize empty repository (no initial clone)
                progress.update(task, description="Initializing repository...")
                self.repo = git.Repo.init(self.clone_dir)

                # Add the remote origin
                self.repo.create_remote("origin", self.clone_url)

                # Step 2: Configure for optimal performance
                progress.update(
                    task, description="Configuring for optimal performance..."
                )

                # Enable sparse-checkout for minimal working directory
                self.repo.git.config("core.sparseCheckout", "true")
                sparse_checkout_path = (
                    self.clone_dir / ".git" / "info" / "sparse-checkout"
                )
                sparse_checkout_path.parent.mkdir(parents=True, exist_ok=True)
                sparse_checkout_path.write_text("", encoding="utf-8")  # No files

                # Step 3: Fetch only what we need with blob filtering
                progress.update(task, description="Fetching required references...")

                # Fetch both refs in a single operation with blob filtering
                # This avoids downloading file contents, only getting commit metadata
                try:
                    self.repo.git.fetch(
                        "origin",
                        good_ref,
                        bad_ref,
                        "--filter=blob:none",
                        "--no-tags",  # Skip tags unless they're the refs we want
                    )
                except git.GitCommandError:
                    # If the combined fetch fails, try individual fetches
                    logger.debug("Combined fetch failed, trying individual fetches")
                    self.repo.git.fetch("origin", good_ref, "--filter=blob:none")
                    self.repo.git.fetch("origin", bad_ref, "--filter=blob:none")

                # Step 4: Fetch the commit range with blob filtering
                progress.update(task, description="Fetching commit history...")
                try:
                    # Fetch the full history between the refs efficiently
                    self.repo.git.fetch(
                        "origin", f"{good_ref}..{bad_ref}", "--filter=blob:none"
                    )
                except git.GitCommandError:
                    logger.debug(
                        "Range fetch failed, trying to fetch all refs with blob filtering"
                    )
                    # Fallback: fetch all refs (still with blob filtering)
                    try:
                        self.repo.git.fetch("origin", "--filter=blob:none")
                    except git.GitCommandError:
                        logger.debug("Blob filter not supported, fetching normally")
                        self.repo.git.fetch("origin")

                progress.update(task, description="Caching repository...")
                
                # Cache the repository for future use
                try:
                    cache.store_repository(self.repo_url, good_ref, bad_ref, self.clone_dir)
                except Exception as e:
                    logger.warning(f"Failed to cache repository: {e}")

                progress.update(task, description="✅ Repository ready for bisection")

            except Exception as e:
                # Clean up on failure
                if self.clone_dir and self.clone_dir.exists():
                    shutil.rmtree(self.clone_dir, ignore_errors=True)
                raise git.GitCommandError(
                    f"Failed to set up repository: {e}", status=1
                ) from e

        return self.clone_dir

    def resolve_reference(self, ref: str) -> str:
        """Resolve a Git reference to its full commit hash.

        Args:
            ref: The reference to resolve (commit hash, tag, or branch)

        Returns:
            The full commit hash

        Raises:
            ValueError: If the reference cannot be resolved
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            commit = self.repo.commit(ref)
            return str(commit.hexsha)
        except git.BadName as e:
            # Get suggestions for similar refs
            suggestions = self._get_similar_refs(ref)
            if suggestions:
                suggestion_text = ", ".join(f"'{s}'" for s in suggestions[:3])
                raise ValueError(
                    f"Cannot resolve reference '{ref}'. Did you mean: {suggestion_text}?"
                ) from e
            else:
                raise ValueError(f"Cannot resolve reference '{ref}': {e}") from e

    def _get_similar_refs(self, target_ref: str, max_suggestions: int = 3) -> list[str]:
        """Find similar references using fuzzy matching.

        Args:
            target_ref: The reference that couldn't be resolved
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of similar reference names
        """
        if not self.repo:
            return []

        try:
            # Get all available refs (tags and branches)
            all_refs = []

            # Get tags
            for tag in self.repo.tags:
                all_refs.append(str(tag.name))

            # Get remote branches
            for remote_ref in self.repo.remote().refs:
                branch_name = str(remote_ref.name).split("/")[
                    -1
                ]  # Get just the branch name
                if branch_name not in all_refs and branch_name != "HEAD":
                    all_refs.append(branch_name)

            # Simple fuzzy matching based on common patterns
            suggestions = []
            target_lower = target_ref.lower()

            # Exact prefix matches first
            for ref in all_refs:
                if ref.lower().startswith(target_lower):
                    suggestions.append(ref)

            # Then substring matches
            if len(suggestions) < max_suggestions:
                for ref in all_refs:
                    if target_lower in ref.lower() and ref not in suggestions:
                        suggestions.append(ref)

            # Finally, similar length/structure matches for version patterns
            if len(suggestions) < max_suggestions:
                import re

                # Check if target looks like a version (v1.2.3, 1.2.3, etc.)
                version_pattern = re.compile(r"^v?\d+\.\d+(\.\d+)?")
                if version_pattern.match(target_ref):
                    for ref in all_refs:
                        if (
                            version_pattern.match(ref)
                            and ref not in suggestions
                            and self._version_similarity_score(target_ref, ref) > 0.5
                        ):
                            suggestions.append(ref)

            return suggestions[:max_suggestions]

        except Exception:
            # If anything fails, return empty list
            return []

    def _version_similarity_score(self, ref1: str, ref2: str) -> float:
        """Calculate a simple similarity score for version-like references."""
        # Simple heuristic: same prefix (v or not), similar number count
        ref1_clean = ref1.lower().lstrip("v")
        ref2_clean = ref2.lower().lstrip("v")

        ref1_parts = ref1_clean.split(".")
        ref2_parts = ref2_clean.split(".")

        # Prefer same number of parts
        if len(ref1_parts) == len(ref2_parts):
            return 0.7
        elif abs(len(ref1_parts) - len(ref2_parts)) == 1:
            return 0.6
        else:
            return 0.3

    def get_commit_range(self, good_ref: str, bad_ref: str) -> list[str]:
        """Get the list of commits between two references.

        Args:
            good_ref: The known good reference
            bad_ref: The known bad reference

        Returns:
            List of commit hashes in chronological order (oldest first)

        Raises:
            ValueError: If the repository is not set up or refs are invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            # Get commits in reverse chronological order (newest first), then reverse
            commits = list(self.repo.iter_commits(f"{good_ref}..{bad_ref}"))
            # Return in chronological order (oldest first) for bisection
            return [str(commit.hexsha) for commit in reversed(commits)]
        except git.GitCommandError as e:
            raise ValueError(
                f"Cannot get commit range {good_ref}..{bad_ref}: {e}"
            ) from e

    def checkout_commit(self, commit_hash: str) -> None:
        """Check out a specific commit without affecting working directory.

        Args:
            commit_hash: The commit hash to check out

        Raises:
            ValueError: If the repository is not set up or commit is invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            self.repo.git.checkout(commit_hash)
        except git.GitCommandError as e:
            raise ValueError(f"Cannot checkout commit {commit_hash}: {e}") from e

    def get_commit_info(self, commit_hash: str) -> dict[str, str]:
        """Get information about a specific commit.

        Args:
            commit_hash: The commit hash to get info for

        Returns:
            Dictionary with commit information (hash, author, date, message, etc.)

        Raises:
            ValueError: If the repository is not set up or commit is invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            commit = self.repo.commit(commit_hash)
            return {
                "hash": str(commit.hexsha),
                "short_hash": str(commit.hexsha)[:12],
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "message": str(commit.message).strip(),
                "summary": str(commit.summary),
            }
        except git.BadName as e:
            raise ValueError(f"Cannot get info for commit {commit_hash}: {e}") from e

    def cleanup(self) -> None:
        """Clean up the local repository and temporary files."""
        if self.clone_dir and self.clone_dir.exists():
            import shutil

            try:
                shutil.rmtree(self.clone_dir)
                logger.debug(f"Cleaned up repository: {self.clone_dir}")
            except OSError as e:
                logger.warning(f"Failed to clean up repository: {e}")
            finally:
                self.clone_dir = None
                self.repo = None

    def __enter__(self) -> RepositoryManager:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit with automatic cleanup."""
        self.cleanup()
