"""Tests for the RepositoryManager class."""

from unittest.mock import MagicMock, Mock, patch

import git
import pytest

from script_bisect.repository_manager import RepositoryManager


class TestRepositoryManager:
    """Test the RepositoryManager class."""

    def test_init_strips_git_prefix(self):
        """Test that git+ prefix is stripped from repo URLs."""
        manager = RepositoryManager("git+https://github.com/user/repo.git")
        assert manager.repo_url == "git+https://github.com/user/repo.git"
        assert manager.clone_url == "https://github.com/user/repo.git"

    def test_init_without_git_prefix(self):
        """Test initialization without git+ prefix."""
        manager = RepositoryManager("https://github.com/user/repo.git")
        assert manager.repo_url == "https://github.com/user/repo.git"
        assert manager.clone_url == "https://github.com/user/repo.git"

    @patch("script_bisect.repository_manager.git.Repo")
    def test_resolve_reference_success(self, _mock_repo_class):
        """Test successful reference resolution."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.commit.return_value = mock_commit

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        # Test
        result = manager.resolve_reference("v1.0.0")

        assert result == "abc123def456"
        mock_repo.commit.assert_called_once_with("v1.0.0")

    @patch("script_bisect.repository_manager.git.Repo")
    def test_resolve_reference_with_suggestions(self, _mock_repo_class):
        """Test reference resolution with suggestions when ref is invalid."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.commit.side_effect = git.BadName("bad ref")

        # Mock tags and remote refs for suggestions
        mock_tag1 = MagicMock()
        mock_tag1.name = "v1.0.0"
        mock_tag2 = MagicMock()
        mock_tag2.name = "v1.1.0"
        mock_tag3 = MagicMock()
        mock_tag3.name = "v2.0.0"
        mock_repo.tags = [mock_tag1, mock_tag2, mock_tag3]

        mock_remote = MagicMock()
        mock_ref1 = MagicMock()
        mock_ref1.name = "origin/main"
        mock_ref2 = MagicMock()
        mock_ref2.name = "origin/develop"
        mock_remote.refs = [mock_ref1, mock_ref2]
        mock_repo.remote.return_value = mock_remote

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        # Test with invalid ref that should match suggestions
        with pytest.raises(
            ValueError,
            match=r"Cannot resolve reference 'v1\.0\.1'\. Did you mean: 'v1\.0\.0', 'v1\.1\.0'",
        ):
            manager.resolve_reference("v1.0.1")

    @patch("script_bisect.repository_manager.git.Repo")
    def test_resolve_reference_no_suggestions(self, _mock_repo_class):
        """Test reference resolution when no similar refs are found."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo.commit.side_effect = git.BadName("bad ref")
        mock_repo.tags = []

        mock_remote = MagicMock()
        mock_remote.refs = []
        mock_repo.remote.return_value = mock_remote

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        # Test with invalid ref and no suggestions
        with pytest.raises(
            ValueError,
            match="Cannot resolve reference 'nonexistent': Ref 'bad ref' did not resolve to an object",
        ):
            manager.resolve_reference("nonexistent")

    def test_get_similar_refs_prefix_matching(self):
        """Test that _get_similar_refs finds prefix matches."""
        # Setup mock repo
        mock_repo = MagicMock()
        mock_tag1 = MagicMock()
        mock_tag1.name = "v1.0.0"
        mock_tag2 = MagicMock()
        mock_tag2.name = "v1.1.0"
        mock_tag3 = MagicMock()
        mock_tag3.name = "v2.0.0"
        mock_repo.tags = [mock_tag1, mock_tag2, mock_tag3]

        mock_remote = MagicMock()
        mock_remote.refs = []
        mock_repo.remote.return_value = mock_remote

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        # Test prefix matching
        suggestions = manager._get_similar_refs("v1")
        assert "v1.0.0" in suggestions
        assert "v1.1.0" in suggestions
        assert "v2.0.0" not in suggestions

    def test_get_similar_refs_substring_matching(self):
        """Test that _get_similar_refs finds substring matches."""
        # Setup mock repo
        mock_repo = MagicMock()
        mock_tag1 = MagicMock()
        mock_tag1.name = "release-1.0"
        mock_tag2 = MagicMock()
        mock_tag2.name = "hotfix-1.0.1"
        mock_tag3 = MagicMock()
        mock_tag3.name = "feature-2.0"
        mock_repo.tags = [mock_tag1, mock_tag2, mock_tag3]

        mock_remote = MagicMock()
        mock_remote.refs = []
        mock_repo.remote.return_value = mock_remote

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        # Test substring matching
        suggestions = manager._get_similar_refs("1.0")
        assert "release-1.0" in suggestions
        assert "hotfix-1.0.1" in suggestions
        assert "feature-2.0" not in suggestions

    def test_version_similarity_score(self):
        """Test version similarity scoring."""
        manager = RepositoryManager("https://github.com/user/repo.git")

        # Test same structure
        score = manager._version_similarity_score("v1.0.0", "v2.0.0")
        assert score == 0.7

        # Test similar structure (off by one part)
        score = manager._version_similarity_score("v1.0", "v1.0.0")
        assert score == 0.6

        # Test different structure
        score = manager._version_similarity_score("v1", "v1.0.0.1")
        assert score == 0.3

    def test_get_similar_refs_no_repo(self):
        """Test _get_similar_refs returns empty list when no repo is set up."""
        manager = RepositoryManager("https://github.com/user/repo.git")
        suggestions = manager._get_similar_refs("v1.0.0")
        assert suggestions == []

    def test_get_similar_refs_exception_handling(self):
        """Test _get_similar_refs handles exceptions gracefully."""
        mock_repo = MagicMock()
        mock_repo.tags = Mock(side_effect=Exception("Git error"))

        manager = RepositoryManager("https://github.com/user/repo.git")
        manager.repo = mock_repo

        suggestions = manager._get_similar_refs("v1.0.0")
        assert suggestions == []

    def test_resolve_reference_no_repo(self):
        """Test resolve_reference raises error when repo not set up."""
        manager = RepositoryManager("https://github.com/user/repo.git")

        with pytest.raises(ValueError, match="Repository not set up"):
            manager.resolve_reference("v1.0.0")
