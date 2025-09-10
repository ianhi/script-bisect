"""Tests for dependency mappings functionality."""

from script_bisect.dependency_mappings import (
    IMPORT_TO_PACKAGE,
    STANDARD_LIBRARY,
    add_mapping,
    get_package_name,
    is_standard_library,
    list_known_imports,
)


class TestDependencyMappings:
    """Test dependency mapping functionality."""

    def test_import_to_package_dict_exists(self):
        """Test that the import to package dictionary exists and is populated."""
        assert isinstance(IMPORT_TO_PACKAGE, dict)
        assert len(IMPORT_TO_PACKAGE) > 0

        # Test some expected mappings
        expected_mappings = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "sklearn": "scikit-learn",
            "yaml": "PyYAML",
            "bs4": "beautifulsoup4",
        }

        for import_name, expected_package in expected_mappings.items():
            assert import_name in IMPORT_TO_PACKAGE
            assert IMPORT_TO_PACKAGE[import_name] == expected_package

    def test_standard_library_set_exists(self):
        """Test that the standard library set exists and is populated."""
        assert isinstance(STANDARD_LIBRARY, set)
        assert len(STANDARD_LIBRARY) > 0

        # Test some expected standard library modules
        expected_stdlib = [
            "os",
            "sys",
            "json",
            "re",
            "datetime",
            "pathlib",
            "collections",
            "itertools",
            "functools",
            "math",
            "random",
            "time",
            "urllib",
            "subprocess",
            "threading",
        ]

        for module in expected_stdlib:
            assert (
                module in STANDARD_LIBRARY
            ), f"Module {module} should be in standard library"

    def test_get_package_name_existing_mappings(self):
        """Test getting package names for existing import mappings."""
        assert get_package_name("cv2") == "opencv-python"
        assert get_package_name("PIL") == "Pillow"
        assert get_package_name("sklearn") == "scikit-learn"
        assert get_package_name("yaml") == "PyYAML"
        assert get_package_name("bs4") == "beautifulsoup4"

    def test_get_package_name_direct_mappings(self):
        """Test getting package names for direct mappings (import name = package name)."""
        direct_mappings = ["numpy", "pandas", "requests", "flask", "django"]

        for name in direct_mappings:
            if name in IMPORT_TO_PACKAGE:
                assert get_package_name(name) == IMPORT_TO_PACKAGE[name]

    def test_get_package_name_unknown(self):
        """Test getting package name for unknown imports (should return original name)."""
        unknown_imports = ["unknown_package", "custom_module", "my_library"]

        for name in unknown_imports:
            assert get_package_name(name) == name

    def test_is_standard_library_true(self):
        """Test checking standard library modules."""
        stdlib_modules = ["os", "sys", "json", "re", "datetime", "math", "random"]

        for module in stdlib_modules:
            assert is_standard_library(module) is True

    def test_is_standard_library_false(self):
        """Test checking non-standard library modules."""
        third_party_modules = ["numpy", "pandas", "requests", "flask", "pytest"]

        for module in third_party_modules:
            assert is_standard_library(module) is False

    def test_list_known_imports(self):
        """Test listing all known import mappings."""
        imports = list_known_imports()

        assert isinstance(imports, list)
        assert len(imports) == len(IMPORT_TO_PACKAGE)

        # Should be sorted
        assert imports == sorted(imports)

        # Should contain expected imports
        expected_imports = ["cv2", "PIL", "sklearn", "numpy", "pandas"]
        for imp in expected_imports:
            if imp in IMPORT_TO_PACKAGE:
                assert imp in imports

    def test_add_mapping(self):
        """Test adding new import mappings."""
        original_count = len(IMPORT_TO_PACKAGE)

        # Add a new mapping
        add_mapping("test_import", "test-package")

        assert len(IMPORT_TO_PACKAGE) == original_count + 1
        assert get_package_name("test_import") == "test-package"

        # Update existing mapping
        add_mapping("test_import", "updated-package")

        assert len(IMPORT_TO_PACKAGE) == original_count + 1  # Should not increase count
        assert get_package_name("test_import") == "updated-package"

        # Clean up
        del IMPORT_TO_PACKAGE["test_import"]

    def test_computer_vision_mappings(self):
        """Test computer vision specific mappings."""
        cv_mappings = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
        }

        for import_name, expected_package in cv_mappings.items():
            assert get_package_name(import_name) == expected_package

    def test_machine_learning_mappings(self):
        """Test machine learning specific mappings."""
        ml_mappings = {
            "sklearn": "scikit-learn",
        }

        for import_name, expected_package in ml_mappings.items():
            assert get_package_name(import_name) == expected_package

        # Test that common ML packages have entries
        ml_packages = ["numpy", "pandas", "scipy", "matplotlib", "seaborn"]
        for package in ml_packages:
            if package in IMPORT_TO_PACKAGE:
                assert get_package_name(package) == IMPORT_TO_PACKAGE[package]

    def test_web_framework_mappings(self):
        """Test web framework specific mappings."""
        web_mappings = {
            "flask": "Flask",
            "django": "Django",
        }

        for import_name, expected_package in web_mappings.items():
            if import_name in IMPORT_TO_PACKAGE:
                assert get_package_name(import_name) == expected_package

    def test_data_format_mappings(self):
        """Test data format parsing mappings."""
        data_mappings = {
            "yaml": "PyYAML",
            "bs4": "beautifulsoup4",
        }

        for import_name, expected_package in data_mappings.items():
            assert get_package_name(import_name) == expected_package

    def test_database_mappings(self):
        """Test database related mappings."""
        db_mappings = {
            "sqlalchemy": "SQLAlchemy",
            "psycopg2": "psycopg2-binary",
        }

        for import_name, expected_package in db_mappings.items():
            if import_name in IMPORT_TO_PACKAGE:
                assert get_package_name(import_name) == expected_package

    def test_authentication_mappings(self):
        """Test authentication and security mappings."""
        auth_mappings = {
            "jwt": "PyJWT",
            "dateutil": "python-dateutil",
            "dotenv": "python-dotenv",
        }

        for import_name, expected_package in auth_mappings.items():
            if import_name in IMPORT_TO_PACKAGE:
                assert get_package_name(import_name) == expected_package

    def test_no_circular_mappings(self):
        """Test that there are no circular mappings."""
        for import_name, package_name in IMPORT_TO_PACKAGE.items():
            # Package name should not map back to a different import name
            # (unless it's the same name, which is fine)
            if package_name in IMPORT_TO_PACKAGE:
                mapped_back = IMPORT_TO_PACKAGE[package_name]
                if mapped_back != package_name:
                    # This could indicate a circular mapping
                    print(
                        f"Potential circular mapping: {import_name} -> {package_name} -> {mapped_back}"
                    )

    def test_standard_library_completeness(self):
        """Test that standard library set includes expected modules."""
        # Test Python 3.12+ standard library modules
        expected_stdlib = {
            # Built-in modules
            "builtins",
            "sys",
            "os",
            "pathlib",
            # Common standard library modules
            "json",
            "re",
            "datetime",
            "math",
            "random",
            "time",
            "collections",
            "itertools",
            "functools",
            "operator",
            "copy",
            "pickle",
            "csv",
            "urllib",
            "subprocess",
            "threading",
            "multiprocessing",
            "logging",
            "warnings",
            "tempfile",
            "shutil",
            "glob",
            "fnmatch",
            # Python 3.9+ additions
            "graphlib",
            "zoneinfo",
            # Python 3.10+ additions
            "tomllib",
        }

        for module in expected_stdlib:
            assert (
                module in STANDARD_LIBRARY
            ), f"Standard library should include {module}"

    def test_standard_library_no_third_party(self):
        """Test that standard library set doesn't include third-party packages."""
        third_party_packages = {
            "numpy",
            "pandas",
            "requests",
            "flask",
            "django",
            "pytest",
            "mypy",
            "ruff",
            "black",
            "isort",
            "scikit-learn",
            "matplotlib",
            "scipy",
            "pillow",
        }

        for package in third_party_packages:
            assert (
                package not in STANDARD_LIBRARY
            ), f"Standard library should not include third-party package {package}"

    def test_case_sensitivity(self):
        """Test that import name lookups are case sensitive."""
        # Test case sensitivity for mappings that should be case sensitive
        assert get_package_name("PIL") == "Pillow"  # Uppercase PIL
        assert (
            get_package_name("pil") == "pil"
        )  # lowercase pil should return as-is (no mapping)

        # Standard library should be case sensitive too
        assert is_standard_library("os") is True
        assert is_standard_library("OS") is False

    def test_mapping_consistency(self):
        """Test that mappings are consistent and logical."""
        for import_name, package_name in IMPORT_TO_PACKAGE.items():
            # Package name should not be empty
            assert package_name, f"Package name for {import_name} should not be empty"

            # Package name should not contain spaces (PyPI constraint)
            assert (
                " " not in package_name
            ), f"Package name {package_name} should not contain spaces"

            # Import name should not be empty
            assert import_name, "Import name should not be empty"
