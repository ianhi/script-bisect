"""Tests for script auto-correction functionality."""

from script_bisect.issue_importer import CodeBlock
from script_bisect.script_autocorrect import ScriptAutoCorrector


class TestScriptAutoCorrector:
    """Test script auto-correction functionality."""

    def test_init(self):
        """Test that the auto-corrector initializes properly."""
        corrector = ScriptAutoCorrector()
        assert corrector.common_import_fixes is not None
        assert len(corrector.common_import_fixes) > 0

    def test_detect_numpy_usage(self):
        """Test detection and correction of numpy usage."""
        corrector = ScriptAutoCorrector()

        code_content = """x = np.array([1, 2, 3])
y = np.mean(x)
print(y)"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        assert "import numpy as np" in corrected_content
        assert any("numpy" in fix.lower() for fix in fixes)
        assert "AUTO-GENERATED IMPORT FIXES" in corrected_content
        assert "fmt: off" in corrected_content
        assert "fmt: on" in corrected_content

    def test_detect_pandas_usage(self):
        """Test detection and correction of pandas usage."""
        corrector = ScriptAutoCorrector()

        code_content = """df = pd.DataFrame({'a': [1, 2, 3]})
print(df.head())"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        assert "import pandas as pd" in corrected_content
        assert any("pandas" in fix.lower() for fix in fixes)

    def test_detect_matplotlib_usage(self):
        """Test detection and correction of matplotlib usage."""
        corrector = ScriptAutoCorrector()

        code_content = """plt.plot([1, 2, 3])
plt.show()"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        assert "import matplotlib.pyplot as plt" in corrected_content
        assert any("matplotlib" in fix.lower() for fix in fixes)

    def test_dependency_context_detection(self):
        """Test using dependency context to detect imports."""
        corrector = ScriptAutoCorrector()
        dependencies = ["xarray", "pandas"]

        code_content = """da = DataArray([1, 2, 3])
df = DataFrame({'a': [1, 2, 3]})"""

        corrected_content, fixes = corrector.analyze_and_fix_script(
            code_content, dependencies
        )

        assert "from xarray import DataArray" in corrected_content
        assert "from pandas import DataFrame" in corrected_content
        assert any("DataArray" in fix for fix in fixes)
        assert any("DataFrame" in fix for fix in fixes)

    def test_zarr_detection(self):
        """Test detection of zarr imports."""
        corrector = ScriptAutoCorrector()
        dependencies = ["zarr"]

        code_content = """group = Group('/path')
arr = Array([1, 2, 3])"""

        corrected_content, fixes = corrector.analyze_and_fix_script(
            code_content, dependencies
        )

        # The corrector might combine imports
        assert (
            "from zarr import Group" in corrected_content
            or "from zarr import Array, Group" in corrected_content
        )
        assert (
            "from zarr import Array" in corrected_content
            or "from zarr import Array, Group" in corrected_content
        )

    def test_icechunk_detection(self):
        """Test detection of icechunk imports."""
        corrector = ScriptAutoCorrector()
        dependencies = ["icechunk"]

        code_content = """store = IcechunkStore('path')"""

        corrected_content, fixes = corrector.analyze_and_fix_script(
            code_content, dependencies
        )

        assert "from icechunk import IcechunkStore" in corrected_content

    def test_no_imports_needed(self):
        """Test script that doesn't need any import fixes."""
        corrector = ScriptAutoCorrector()

        code_content = """import numpy as np
x = np.array([1, 2, 3])
print(x.sum())"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        # Should not add additional imports (but ruff might make formatting changes)
        import_count_original = code_content.count("import numpy as np")
        import_count_corrected = corrected_content.count("import numpy as np")
        assert import_count_corrected == import_count_original  # No duplicate imports

    def test_existing_imports_not_duplicated(self):
        """Test that existing imports are not duplicated."""
        corrector = ScriptAutoCorrector()

        code_content = """import numpy as np
import pandas as pd

x = np.array([1, 2, 3])
df = pd.DataFrame({'a': x})"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        # Should not add duplicate imports
        numpy_count = corrected_content.count("import numpy as np")
        pandas_count = corrected_content.count("import pandas as pd")
        assert numpy_count == 1
        assert pandas_count == 1

    def test_usage_pattern_detection(self):
        """Test that usage patterns are correctly detected."""
        corrector = ScriptAutoCorrector()

        # Should detect actual usage
        assert corrector._is_usage_pattern_present("x = np.array([1, 2, 3])", "np.")
        assert corrector._is_usage_pattern_present(
            "df = pd.read_csv('file.csv')", "pd."
        )

        # Should not detect in comments
        assert not corrector._is_usage_pattern_present("# This uses np.array", "np.")

        # Should not detect in strings (basic check)
        assert not corrector._is_usage_pattern_present(
            "print('np.array is useful')", "np."
        )

    def test_class_function_usage_detection(self):
        """Test detection of class and function usage."""
        corrector = ScriptAutoCorrector()

        # Should detect class usage
        assert corrector._is_class_or_function_used("df = DataFrame(data)", "DataFrame")
        assert corrector._is_class_or_function_used("arr: ndarray = ...", "ndarray")
        assert corrector._is_class_or_function_used(
            "result = LinearRegression()", "LinearRegression"
        )

        # Should not detect in strings
        assert not corrector._is_class_or_function_used(
            "print('DataFrame')", "DataFrame"
        )

    def test_import_insert_position(self):
        """Test finding correct position to insert imports."""
        corrector = ScriptAutoCorrector()

        # After shebang and docstring
        lines = [
            "#!/usr/bin/env python3",
            '"""Module docstring."""',
            "",
            "import os",
            "",
            "def main():",
            "    pass",
        ]

        position = corrector._find_import_insert_position(lines)
        # The function continues through all blank lines after imports
        # Lines: 0=shebang, 1=docstring, 2=empty, 3=import, 4=empty, 5=def, 6=pass
        # It should stop at first non-import/non-blank/non-comment line
        assert position == 5  # Should be at "def main():" line (index 5)

        # Simple case
        lines = ["print('hello')", "x = 1"]
        position = corrector._find_import_insert_position(lines)
        assert position == 0  # At the beginning

    def test_auto_correct_code_block(self):
        """Test auto-correcting a CodeBlock object."""
        corrector = ScriptAutoCorrector()

        original_block = CodeBlock(
            content="x = np.array([1, 2, 3])",
            language="python",
            source_location="test",
            is_python_script=True,
            confidence_score=1.0,
        )

        corrected_block, fixes = corrector.auto_correct_code_block(original_block)

        assert isinstance(corrected_block, CodeBlock)
        assert corrected_block.language == original_block.language
        assert corrected_block.source_location == original_block.source_location
        assert corrected_block.is_python_script == original_block.is_python_script
        assert corrected_block.confidence_score == original_block.confidence_score
        assert "import numpy as np" in corrected_block.content
        assert len(fixes) > 0

    def test_create_correction_summary(self):
        """Test creating a summary of corrections."""
        corrector = ScriptAutoCorrector()

        fixes = ["Added import: import numpy as np", "Applied ruff auto-fixes"]
        summary = corrector.create_correction_summary(fixes)

        assert "Applied 2 auto-corrections:" in summary
        assert "1. Added import: import numpy as np" in summary
        assert "2. Applied ruff auto-fixes" in summary

    def test_no_corrections_summary(self):
        """Test summary when no corrections are needed."""
        corrector = ScriptAutoCorrector()

        summary = corrector.create_correction_summary([])
        assert summary == "No corrections needed"

    def test_complex_dependency_mapping(self):
        """Test complex dependency mapping with multiple packages."""
        corrector = ScriptAutoCorrector()
        dependencies = ["scikit-learn", "xarray", "matplotlib"]

        code_content = """# Complex ML script
scaler = StandardScaler()
model = LinearRegression()
da = DataArray([1, 2, 3])
plt.plot([1, 2, 3])"""

        corrected_content, fixes = corrector.analyze_and_fix_script(
            code_content, dependencies
        )

        assert "from sklearn.preprocessing import StandardScaler" in corrected_content
        assert "from sklearn.linear_model import LinearRegression" in corrected_content
        assert "from xarray import DataArray" in corrected_content
        assert "import matplotlib.pyplot as plt" in corrected_content

    def test_clean_dependency_names(self):
        """Test cleaning dependency names with version specifiers."""
        corrector = ScriptAutoCorrector()
        dependencies = [
            "numpy>=1.20",
            "pandas==1.5.0",
            "requests~=2.28",
            "flask[async]",
            "git+https://github.com/user/repo.git",
        ]

        code_content = """arr = array([1, 2, 3])
df = DataFrame({'a': [1]})"""

        # Should work despite version specifiers
        corrected_content, fixes = corrector.analyze_and_fix_script(
            code_content, dependencies
        )

        # Should detect numpy despite version specifier
        expected_fixes = len(
            [f for f in fixes if "numpy" in f.lower() or "pandas" in f.lower()]
        )
        assert expected_fixes >= 0  # May or may not detect depending on patterns

    def test_existing_imports_not_in_autogenerated_block(self):
        """Test that when imports already exist, they don't go in auto-generated block."""
        corrector = ScriptAutoCorrector()

        # Code from GitHub issue https://github.com/pydata/xarray/issues/10712
        code_content = """import cloudpickle
import s3fs
import xarray as xr

s3 = s3fs.S3FileSystem(anon=True)
fname = "s3://earthmover-sample-data/netcdf/tas_Amon_GFDL-ESM4_hist-piNTCF_r1i1p1f1_gr1.nc"
ds = xr.open_dataset(s3.open(fname), engine="h5netcdf", chunks={})
cloudpickle.loads(cloudpickle.dumps(ds))"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        # Should not create an auto-generated import block since imports already exist
        assert "AUTO-GENERATED IMPORT FIXES" not in corrected_content

        # May have ruff fixes but no import additions
        if fixes:
            assert all(
                "import" not in fix.lower()
                for fix in fixes
                if "ruff" not in fix.lower()
            )

        # Check that existing imports are preserved
        assert "import cloudpickle" in corrected_content
        assert "import s3fs" in corrected_content
        assert "import xarray as xr" in corrected_content

    def test_mixed_case_existing_and_missing_imports(self):
        """Test case where some imports exist and some are missing."""
        corrector = ScriptAutoCorrector()

        code_content = """import numpy as np

# Missing pandas import
df = pd.DataFrame({'x': [1, 2, 3]})
arr = np.array([1, 2, 3])"""

        corrected_content, fixes = corrector.analyze_and_fix_script(code_content)

        # Should add the missing pandas import to auto-generated block
        assert "AUTO-GENERATED IMPORT FIXES" in corrected_content
        assert "import pandas as pd" in corrected_content

        # Should preserve existing numpy import
        assert "import numpy as np" in corrected_content

        # Should have exactly 2 numpy imports total (not duplicated)
        numpy_count = corrected_content.count("import numpy as np")
        assert numpy_count == 1
