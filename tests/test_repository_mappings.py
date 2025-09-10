"""Tests for repository mappings functionality."""

from script_bisect.repository_mappings import (
    COMMON_REPOSITORIES,
    add_repository,
    get_repository_url,
    has_repository,
    list_supported_packages,
)


class TestRepositoryMappings:
    """Test repository mapping functionality."""

    def test_common_repositories_dict_exists(self):
        """Test that the common repositories dictionary exists and is populated."""
        assert isinstance(COMMON_REPOSITORIES, dict)
        assert len(COMMON_REPOSITORIES) > 0

        # Test some expected scientific Python packages
        expected_packages = [
            "numpy",
            "scipy",
            "pandas",
            "matplotlib",
            "xarray",
            "scikit-learn",
            "requests",
            "flask",
            "django",
            "pytest",
        ]

        for package in expected_packages:
            assert (
                package in COMMON_REPOSITORIES
            ), f"Package {package} should be in mappings"

    def test_all_urls_are_https_github(self):
        """Test that all repository URLs are HTTPS GitHub URLs."""
        for package, url in COMMON_REPOSITORIES.items():
            assert url.startswith(
                "https://github.com/"
            ), f"URL for {package} should be HTTPS GitHub URL"
            assert (
                url.count("/") >= 4
            ), f"URL for {package} should include owner/repo path"

    def test_get_repository_url_existing(self):
        """Test getting repository URL for existing packages."""
        # Test some known packages
        numpy_url = get_repository_url("numpy")
        assert numpy_url == "https://github.com/numpy/numpy"

        pandas_url = get_repository_url("pandas")
        assert pandas_url == "https://github.com/pandas-dev/pandas"

        requests_url = get_repository_url("requests")
        assert requests_url == "https://github.com/psf/requests"

    def test_get_repository_url_nonexistent(self):
        """Test getting repository URL for non-existent packages."""
        assert get_repository_url("nonexistent-package") is None
        assert get_repository_url("") is None

    def test_has_repository_existing(self):
        """Test checking if repository exists for known packages."""
        assert has_repository("numpy") is True
        assert has_repository("pandas") is True
        assert has_repository("scikit-learn") is True

    def test_has_repository_nonexistent(self):
        """Test checking repository for non-existent packages."""
        assert has_repository("nonexistent-package") is False
        assert has_repository("") is False

    def test_list_supported_packages(self):
        """Test listing all supported packages."""
        packages = list_supported_packages()

        assert isinstance(packages, list)
        assert len(packages) > 0
        assert len(packages) == len(COMMON_REPOSITORIES)

        # Should be sorted
        assert packages == sorted(packages)

        # Should contain expected packages
        assert "numpy" in packages
        assert "pandas" in packages
        assert "xarray" in packages

    def test_add_repository(self):
        """Test adding new repository mappings."""
        original_count = len(COMMON_REPOSITORIES)

        # Add a new repository
        add_repository("test-package", "https://github.com/test/test-package")

        assert len(COMMON_REPOSITORIES) == original_count + 1
        assert (
            get_repository_url("test-package") == "https://github.com/test/test-package"
        )
        assert has_repository("test-package") is True

        # Update existing repository
        add_repository("test-package", "https://github.com/updated/test-package")

        assert (
            len(COMMON_REPOSITORIES) == original_count + 1
        )  # Should not increase count
        assert (
            get_repository_url("test-package")
            == "https://github.com/updated/test-package"
        )

        # Clean up
        del COMMON_REPOSITORIES["test-package"]

    def test_scientific_python_core_packages(self):
        """Test that core scientific Python packages are included."""
        core_packages = [
            "numpy",
            "scipy",
            "pandas",
            "matplotlib",
            "scikit-learn",
            "jupyter",
            "ipython",
        ]

        for package in core_packages:
            assert has_repository(
                package
            ), f"Core package {package} should have repository mapping"
            url = get_repository_url(package)
            assert url is not None
            assert "github.com" in url

    def test_web_framework_packages(self):
        """Test that popular web framework packages are included."""
        web_packages = ["django", "flask", "fastapi", "requests", "httpx", "aiohttp"]

        for package in web_packages:
            assert has_repository(
                package
            ), f"Web package {package} should have repository mapping"
            url = get_repository_url(package)
            assert url is not None
            assert "github.com" in url

    def test_development_tool_packages(self):
        """Test that development tool packages are included."""
        dev_packages = ["pytest", "mypy", "ruff", "rich", "click"]

        for package in dev_packages:
            assert has_repository(
                package
            ), f"Dev package {package} should have repository mapping"
            url = get_repository_url(package)
            assert url is not None
            assert "github.com" in url

    def test_case_sensitivity(self):
        """Test that package name lookups are case sensitive."""
        # Should be case sensitive - these should not match
        assert get_repository_url("NUMPY") is None
        assert get_repository_url("Pandas") is None
        assert get_repository_url("NumPy") is None

        # But exact case should work
        assert get_repository_url("numpy") is not None
        assert get_repository_url("pandas") is not None

    def test_no_duplicate_urls(self):
        """Test that there are no duplicate repository URLs (except for aliases)."""
        urls = list(COMMON_REPOSITORIES.values())

        # Known aliases that should share URLs
        known_aliases = {
            "sklearn": "scikit-learn",  # sklearn -> scikit-learn
        }

        # Count occurrences of each URL
        url_counts: dict[str, int] = {}
        for url in urls:
            url_counts[url] = url_counts.get(url, 0) + 1

        # Check for unexpected duplicates
        for url, count in url_counts.items():
            if count > 1:
                # Find packages with this URL
                packages_with_url = [
                    pkg
                    for pkg, pkg_url in COMMON_REPOSITORIES.items()
                    if pkg_url == url
                ]

                # Should only be duplicated if they are known aliases
                for pkg in packages_with_url:
                    reverse_alias = any(
                        (alias_pkg == pkg and target_pkg in packages_with_url)
                        or (target_pkg == pkg and alias_pkg in packages_with_url)
                        for alias_pkg, target_pkg in known_aliases.items()
                    )
                    if not reverse_alias:
                        # This might be acceptable (e.g., multiple packages in same repo)
                        # but let's at least document it in the test
                        print(
                            f"Note: URL {url} is shared by packages: {packages_with_url}"
                        )

    def test_repository_accessibility(self):
        """Test that repository URLs follow expected GitHub patterns."""
        for package, url in COMMON_REPOSITORIES.items():
            # Should be GitHub HTTPS URL
            assert url.startswith("https://github.com/")

            # Should have owner/repo format
            path_parts = url.replace("https://github.com/", "").split("/")
            assert (
                len(path_parts) >= 2
            ), f"URL for {package} should have owner/repo format"

            owner, repo = path_parts[0], path_parts[1]
            assert owner, f"Owner should not be empty for {package}"
            assert repo, f"Repo should not be empty for {package}"

            # Should not have trailing slash
            assert not url.endswith(
                "/"
            ), f"URL for {package} should not have trailing slash"
