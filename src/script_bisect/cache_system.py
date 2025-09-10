"""Intelligent caching system for script-bisect operations.

This module provides a comprehensive caching layer to optimize expensive operations like
repository cloning, git reference fetching, PyPI metadata lookups, and uv operations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """Manages intelligent caching for script-bisect operations."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the cache manager.

        Args:
            cache_dir: Custom cache directory. If None, uses ~/.cache/script-bisect
        """
        if cache_dir is None:
            # Use XDG cache directory standard
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                cache_dir = Path(xdg_cache) / "script-bisect"
            else:
                cache_dir = Path.home() / ".cache" / "script-bisect"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different cache types
        self.repos_cache = self.cache_dir / "repositories"
        self.refs_cache = self.cache_dir / "references"
        self.metadata_cache = self.cache_dir / "metadata"
        self.scripts_cache = self.cache_dir / "scripts"

        for cache_subdir in [
            self.repos_cache,
            self.refs_cache,
            self.metadata_cache,
            self.scripts_cache,
        ]:
            cache_subdir.mkdir(exist_ok=True)

    def _get_cache_key(self, *args: Any) -> str:
        """Generate a cache key from arguments."""
        # Create a stable hash from all arguments
        content = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_cache_valid(self, cache_path: Path, ttl_hours: float = 24.0) -> bool:
        """Check if cache file is valid (exists and not expired)."""
        if not cache_path.exists():
            return False

        # Check TTL
        file_age = time.time() - cache_path.stat().st_mtime
        max_age = ttl_hours * 3600  # Convert hours to seconds

        return file_age < max_age

    def cache_repository(
        self,
        repo_url: str,
        good_ref: str,
        bad_ref: str,
        ttl_hours: float = 168.0,  # 1 week
    ) -> Path | None:
        """Get cached repository or return None if not available.

        Args:
            repo_url: Repository URL
            good_ref: Good reference
            bad_ref: Bad reference
            ttl_hours: Cache TTL in hours

        Returns:
            Path to cached repository or None if not cached
        """
        cache_key = self._get_cache_key("repo", repo_url, good_ref, bad_ref)
        cache_path = self.repos_cache / cache_key

        if self._is_cache_valid(cache_path, ttl_hours):
            logger.debug(f"Using cached repository: {cache_path}")
            return cache_path

        return None

    def store_repository(
        self, repo_url: str, good_ref: str, bad_ref: str, repo_path: Path
    ) -> None:
        """Store a repository in the cache.

        Args:
            repo_url: Repository URL
            good_ref: Good reference
            bad_ref: Bad reference
            repo_path: Path to repository to cache
        """
        cache_key = self._get_cache_key("repo", repo_url, good_ref, bad_ref)
        cache_path = self.repos_cache / cache_key

        try:
            # Remove existing cache if it exists
            if cache_path.exists():
                shutil.rmtree(cache_path)

            # Copy repository to cache
            shutil.copytree(repo_path, cache_path)

            # Store metadata
            metadata = {
                "repo_url": repo_url,
                "good_ref": good_ref,
                "bad_ref": bad_ref,
                "cached_at": time.time(),
            }
            (cache_path / ".cache_metadata.json").write_text(
                json.dumps(metadata, indent=2)
            )

            logger.debug(f"Cached repository: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to cache repository: {e}")
            if cache_path.exists():
                shutil.rmtree(cache_path, ignore_errors=True)

    def get_cached_refs(
        self,
        repo_url: str,
        ttl_hours: float = 6.0,  # 6 hours
        force_refresh: bool = False,
    ) -> list[str] | None:
        """Get cached git references for a repository.

        Args:
            repo_url: Repository URL
            ttl_hours: Cache TTL in hours
            force_refresh: If True, ignore cache and return None to force refresh

        Returns:
            List of git references or None if not cached
        """
        if force_refresh:
            return None

        cache_key = self._get_cache_key("refs", repo_url)
        cache_path = self.refs_cache / f"{cache_key}.json"

        if self._is_cache_valid(cache_path, ttl_hours):
            try:
                data = json.loads(cache_path.read_text())
                logger.debug(f"Using cached refs for {repo_url}")
                refs = data.get("refs", [])
                return refs if isinstance(refs, list) else []
            except Exception as e:
                logger.warning(f"Failed to load cached refs: {e}")

        return None

    def store_refs(self, repo_url: str, refs: list[str]) -> None:
        """Store git references in cache.

        Args:
            repo_url: Repository URL
            refs: List of git references
        """
        cache_key = self._get_cache_key("refs", repo_url)
        cache_path = self.refs_cache / f"{cache_key}.json"

        try:
            data = {
                "repo_url": repo_url,
                "refs": refs,
                "cached_at": time.time(),
            }
            cache_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Cached {len(refs)} refs for {repo_url}")

        except Exception as e:
            logger.warning(f"Failed to cache refs: {e}")

    def get_cached_metadata(
        self, package_name: str, ttl_hours: float = 24.0
    ) -> dict[str, Any] | None:
        """Get cached package metadata (PyPI info, repo URLs, etc.).

        Args:
            package_name: Package name
            ttl_hours: Cache TTL in hours

        Returns:
            Package metadata or None if not cached
        """
        cache_key = self._get_cache_key("metadata", package_name)
        cache_path = self.metadata_cache / f"{cache_key}.json"

        if self._is_cache_valid(cache_path, ttl_hours):
            try:
                data = json.loads(cache_path.read_text())
                logger.debug(f"Using cached metadata for {package_name}")
                metadata = data.get("metadata", {})
                return metadata if isinstance(metadata, dict) else {}
            except Exception as e:
                logger.warning(f"Failed to load cached metadata: {e}")

        return None

    def store_metadata(self, package_name: str, metadata: dict[str, Any]) -> None:
        """Store package metadata in cache.

        Args:
            package_name: Package name
            metadata: Package metadata
        """
        cache_key = self._get_cache_key("metadata", package_name)
        cache_path = self.metadata_cache / f"{cache_key}.json"

        try:
            data = {
                "package_name": package_name,
                "metadata": metadata,
                "cached_at": time.time(),
            }
            cache_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Cached metadata for {package_name}")

        except Exception as e:
            logger.warning(f"Failed to cache metadata: {e}")

    def get_cached_script_info(
        self, script_path: Path, ttl_hours: float = 1.0
    ) -> dict[str, Any] | None:
        """Get cached script parsing information.

        Args:
            script_path: Path to script file
            ttl_hours: Cache TTL in hours

        Returns:
            Cached script info or None if not cached/invalid
        """
        # Include file modification time in cache key for invalidation
        try:
            mtime = script_path.stat().st_mtime
        except OSError:
            return None

        cache_key = self._get_cache_key("script", str(script_path), mtime)
        cache_path = self.scripts_cache / f"{cache_key}.json"

        if self._is_cache_valid(cache_path, ttl_hours):
            try:
                data = json.loads(cache_path.read_text())
                logger.debug(f"Using cached script info for {script_path}")
                info = data.get("info", {})
                return info if isinstance(info, dict) else {}
            except Exception as e:
                logger.warning(f"Failed to load cached script info: {e}")

        return None

    def store_script_info(self, script_path: Path, info: dict[str, Any]) -> None:
        """Store script parsing information in cache.

        Args:
            script_path: Path to script file
            info: Script parsing information
        """
        try:
            mtime = script_path.stat().st_mtime
        except OSError:
            logger.warning(f"Cannot get mtime for {script_path}")
            return

        cache_key = self._get_cache_key("script", str(script_path), mtime)
        cache_path = self.scripts_cache / f"{cache_key}.json"

        try:
            data = {
                "script_path": str(script_path),
                "mtime": mtime,
                "info": info,
                "cached_at": time.time(),
            }
            cache_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Cached script info for {script_path}")

        except Exception as e:
            logger.warning(f"Failed to cache script info: {e}")

    def cached_call(
        self,
        func: Callable[..., T],
        cache_key_parts: list[Any],
        ttl_hours: float = 1.0,
        cache_subdir: str = "general",
    ) -> Callable[..., T]:
        """Create a cached version of a function call.

        Args:
            func: Function to cache
            cache_key_parts: Parts to use for cache key generation
            ttl_hours: Cache TTL in hours
            cache_subdir: Cache subdirectory name

        Returns:
            Cached function wrapper
        """
        cache_dir = self.cache_dir / cache_subdir
        cache_dir.mkdir(exist_ok=True)

        cache_key = self._get_cache_key(*cache_key_parts)
        cache_path = cache_dir / f"{cache_key}.json"

        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Try to load from cache first
            if self._is_cache_valid(cache_path, ttl_hours):
                try:
                    data = json.loads(cache_path.read_text())
                    logger.debug(f"Using cached result for {func.__name__}")
                    result = data["result"]
                    return result  # type: ignore[no-any-return]
                except Exception as e:
                    logger.warning(f"Failed to load cached result: {e}")

            # Call function and cache result
            result = func(*args, **kwargs)

            try:
                data = {
                    "function": func.__name__,
                    "cache_key_parts": cache_key_parts,
                    "result": result,
                    "cached_at": time.time(),
                }
                cache_path.write_text(json.dumps(data, indent=2, default=str))
                logger.debug(f"Cached result for {func.__name__}")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

            return result  # type: ignore[no-any-return]

        return wrapper

    def cleanup_expired(self, max_age_days: float = 30.0) -> None:
        """Clean up expired cache entries.

        Args:
            max_age_days: Maximum age for cache entries in days
        """
        max_age_seconds = max_age_days * 24 * 3600
        current_time = time.time()
        cleaned_count = 0

        for cache_subdir in [
            self.repos_cache,
            self.refs_cache,
            self.metadata_cache,
            self.scripts_cache,
        ]:
            if not cache_subdir.exists():
                continue

            for item in cache_subdir.iterdir():
                try:
                    age = current_time - item.stat().st_mtime
                    if age > max_age_seconds:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean cache item {item}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")

    def clear_cache(self, cache_type: str | None = None) -> None:
        """Clear cache entries.

        Args:
            cache_type: Type of cache to clear ('repos', 'refs', 'metadata', 'scripts', or None for all)
        """
        if cache_type is None:
            # Clear all caches
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cleared all caches")
        else:
            cache_map = {
                "repos": self.repos_cache,
                "repositories": self.repos_cache,
                "refs": self.refs_cache,
                "references": self.refs_cache,
                "metadata": self.metadata_cache,
                "scripts": self.scripts_cache,
            }

            cache_dir = cache_map.get(cache_type.lower())
            if cache_dir and cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(exist_ok=True)
                logger.info(f"Cleared {cache_type} cache")
            else:
                logger.warning(f"Unknown cache type: {cache_type}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about cache usage.

        Returns:
            Dictionary with cache statistics
        """
        stats = {"cache_dir": str(self.cache_dir), "total_size_mb": 0.0, "subdirs": {}}

        if not self.cache_dir.exists():
            return stats

        def get_dir_size(path: Path) -> tuple[int, int]:
            """Get directory size and file count."""
            total_size = 0
            file_count = 0

            try:
                for item in path.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        file_count += 1
            except Exception as e:
                logger.warning(f"Error calculating size for {path}: {e}")

            return total_size, file_count

        total_size = 0
        for subdir_name, subdir_path in [
            ("repositories", self.repos_cache),
            ("references", self.refs_cache),
            ("metadata", self.metadata_cache),
            ("scripts", self.scripts_cache),
        ]:
            if subdir_path.exists():
                size, count = get_dir_size(subdir_path)
                total_size += size
                subdirs = stats["subdirs"]
                assert isinstance(subdirs, dict)
                subdirs[subdir_name] = {
                    "size_mb": size / (1024 * 1024),
                    "file_count": count,
                }
            else:
                subdirs = stats["subdirs"]
                assert isinstance(subdirs, dict)
                subdirs[subdir_name] = {
                    "size_mb": 0.0,
                    "file_count": 0,
                }

        stats["total_size_mb"] = total_size / (1024 * 1024)
        return stats


# Global cache instance
_global_cache: CacheManager | None = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
        # Auto-cleanup expired entries on startup (async to not slow down startup)
        try:
            _global_cache.cleanup_expired(max_age_days=30.0)
        except Exception as e:
            # Don't fail if cleanup fails, just log it
            logger.debug(f"Auto-cleanup failed: {e}")
    return _global_cache


def clear_global_cache(cache_type: str | None = None) -> None:
    """Clear the global cache."""
    cache = get_cache()
    cache.clear_cache(cache_type)
