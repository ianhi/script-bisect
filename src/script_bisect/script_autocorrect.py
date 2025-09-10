"""Auto-correction for common Python script issues.

This module uses static analysis tools to detect and automatically fix
common issues in Python scripts, such as missing imports, undefined variables,
and other correctness problems.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from .issue_importer import CodeBlock
else:
    # Runtime import to avoid circular dependencies
    CodeBlock = None

console = Console()


class ScriptAutoCorrector:
    """Auto-corrects common Python script issues using static analysis."""

    def __init__(self) -> None:
        """Initialize the auto-corrector."""
        # Import correction patterns from separate module
        from .correction_patterns import COMMON_IMPORT_FIXES

        self.common_import_fixes = COMMON_IMPORT_FIXES

    def analyze_and_fix_script(
        self, code_content: str, dependencies: list[str] | None = None
    ) -> tuple[str, list[str]]:
        """Analyze script and apply auto-corrections.

        Args:
            code_content: Original Python script content
            dependencies: List of known dependencies from PEP 723 metadata

        Returns:
            Tuple of (corrected_content, list_of_fixes_applied)
        """
        fixes_applied = []
        corrected_content = code_content

        # Step 1: Use ruff to detect and fix as many issues as possible
        # Ruff can fix many import issues automatically
        ruff_fixes, ruff_content = self._apply_ruff_fixes(corrected_content)
        if ruff_fixes:
            corrected_content = ruff_content
            fixes_applied.extend(ruff_fixes)

        # Step 2: Only add missing imports if ruff couldn't fix them
        # Use minimal pattern matching focused on clear, unambiguous cases
        missing_imports, updated_content = self._detect_missing_imports_minimal(
            corrected_content, dependencies
        )
        if missing_imports:
            corrected_content = updated_content
            fixes_applied.extend([f"Added import: {imp}" for imp in missing_imports])

            # Run ruff again after adding imports to clean up formatting
            post_import_fixes, post_import_content = self._apply_ruff_fixes(
                corrected_content
            )
            if post_import_fixes:
                corrected_content = post_import_content
                fixes_applied.extend(
                    [f"Post-import fix: {fix}" for fix in post_import_fixes]
                )

        return corrected_content, fixes_applied

    def _detect_and_add_missing_imports(
        self, content: str, dependencies: list[str] | None = None
    ) -> tuple[list[str], str]:
        """Detect missing imports and add them.

        Args:
            content: Python script content
            dependencies: List of known dependencies from PEP 723 metadata

        Returns:
            Tuple of (list_of_added_imports, updated_content)
        """
        lines = content.split("\n")
        existing_imports = set()
        added_imports = []

        # Find existing imports
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                existing_imports.add(stripped)

        # Check for usage patterns that need imports
        needed_imports = set()

        # Step 2a: Check attribute patterns (np., pd., etc.)
        for pattern, import_statement in self.common_import_fixes.items():
            if (
                pattern in content
                and import_statement not in existing_imports
                # More sophisticated check to avoid false positives
                # Also check that this isn't a substring of a longer pattern
                # Make sure this pattern isn't part of a longer module name
                # e.g. don't match "pickle." in "cloudpickle.loads"
                and self._is_usage_pattern_present(content, pattern)
                and self._is_standalone_pattern(content, pattern)
            ):
                needed_imports.add(import_statement)

        # Step 2b: Use dependency context to detect class/function imports
        if dependencies:
            context_imports = self._detect_imports_from_dependencies(
                content, dependencies, existing_imports
            )
            needed_imports.update(context_imports)

        if not needed_imports:
            return [], content

        # Add imports at the beginning after any existing imports or docstring
        insert_position = self._find_import_insert_position(lines)

        new_lines = lines[:insert_position]

        # Add auto-correction comment block if we're adding imports
        if needed_imports:
            new_lines.extend(
                [
                    "",
                    "# fmt: off",
                    "# === AUTO-GENERATED IMPORT FIXES ===",
                    "# The following imports were automatically added by script-bisect",
                    "# to fix missing import errors detected in the original code.",
                ]
            )

            # Add the needed imports
            for import_stmt in sorted(needed_imports):
                new_lines.append(import_stmt)
                added_imports.append(import_stmt)

            new_lines.extend(["# === END AUTO-GENERATED FIXES ===", "# fmt: on", ""])

        new_lines.extend(lines[insert_position:])

        return added_imports, "\n".join(new_lines)

    def _detect_missing_imports_minimal(
        self, content: str, dependencies: list[str] | None = None
    ) -> tuple[list[str], str]:
        """Detect missing imports using minimal, robust pattern matching.

        Focuses on clear unambiguous cases and relies on ruff for most import fixing.

        Args:
            content: Python script content
            dependencies: List of known dependencies from PEP 723 metadata

        Returns:
            Tuple of (list_of_added_imports, updated_content)
        """
        lines = content.split("\n")
        existing_imports = set()

        # Find existing imports
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                existing_imports.add(stripped)

        # Only detect very common, unambiguous patterns
        needed_imports = set()

        # Check for dependency context imports (most reliable)
        if dependencies:
            context_imports = self._detect_imports_from_dependencies(
                content, dependencies, existing_imports
            )
            needed_imports.update(context_imports)

        # Only check for most common, unambiguous module patterns
        # Avoid aggressive substring matching that could cause false positives
        minimal_patterns = {
            # Only very common and unambiguous cases
            "np.array(": "import numpy as np",
            "np.mean(": "import numpy as np",
            "np.sum(": "import numpy as np",
            "pd.DataFrame(": "import pandas as pd",
            "pd.read_csv(": "import pandas as pd",
            "plt.plot(": "import matplotlib.pyplot as plt",
            "plt.show(": "import matplotlib.pyplot as plt",
        }

        for pattern, import_stmt in minimal_patterns.items():
            if (
                pattern in content
                and import_stmt not in existing_imports
                and self._is_actual_code_usage(content, pattern)
            ):
                needed_imports.add(import_stmt)

        if not needed_imports:
            return [], content

        # Add imports at the beginning after any existing imports or docstring
        insert_position = self._find_import_insert_position(lines)

        new_lines = lines[:insert_position]
        added_imports = []

        # Add auto-correction comment block if we're adding imports
        new_lines.extend(
            [
                "",
                "# fmt: off",
                "# === AUTO-GENERATED IMPORT FIXES ===",
                "# The following imports were automatically added by script-bisect",
                "# to fix missing import errors detected in the original code.",
            ]
        )

        # Add the needed imports
        for import_stmt in sorted(needed_imports):
            new_lines.append(import_stmt)
            added_imports.append(import_stmt)

        new_lines.extend(["# === END AUTO-GENERATED FIXES ===", "# fmt: on", ""])

        new_lines.extend(lines[insert_position:])

        return added_imports, "\n".join(new_lines)

    def _is_actual_code_usage(self, content: str, pattern: str) -> bool:
        """Check if a pattern appears in actual code (not comments or strings).

        Args:
            content: Script content to check
            pattern: Pattern to look for

        Returns:
            True if pattern is used in actual code
        """
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Basic check to avoid string literals
            # This is intentionally simple to avoid complex parsing
            if pattern in stripped and not (
                stripped.startswith('"')
                or stripped.startswith("'")
                or '"""' in stripped
                or "'''" in stripped
            ):
                return True
        return False

    def _is_usage_pattern_present(self, content: str, pattern: str) -> bool:
        """Check if a usage pattern is actually present using simple heuristics.

        Args:
            content: Script content to check
            pattern: Pattern to look for (e.g., 'np.')

        Returns:
            True if pattern is used in actual code
        """
        # Simple heuristic: check if pattern appears in non-comment lines
        lines = content.split("\n")
        for line in lines:
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Skip string literals (basic check)
            if pattern in stripped:
                # Make sure it's not inside a string literal (basic check)
                # This is imperfect but good enough for most cases
                in_string = False
                quote_char = None

                for i, char in enumerate(stripped):
                    if char in ('"', "'") and (i == 0 or stripped[i - 1] != "\\"):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None
                    elif not in_string and pattern in stripped[i : i + len(pattern)]:
                        return True

        return False

    def _is_standalone_pattern(self, content: str, pattern: str) -> bool:
        """Check if a pattern appears as a standalone module reference, not as part of a longer name.

        Args:
            content: Script content to check
            pattern: Pattern to look for (e.g., 'pickle.')

        Returns:
            True if pattern appears standalone, not as substring of longer module name
        """
        import re

        # Create regex pattern to match the module pattern only when it's not preceded by alphanumeric/underscore
        # This prevents matching "pickle." in "cloudpickle." or "my_pickle."
        pattern_escaped = re.escape(pattern)
        standalone_pattern = rf"(?<![a-zA-Z0-9_]){pattern_escaped}"

        return bool(re.search(standalone_pattern, content))

    def _find_import_insert_position(self, lines: list[str]) -> int:
        """Find the best position to insert new imports.

        Args:
            lines: Script lines

        Returns:
            Line index where imports should be inserted
        """
        # Skip shebang and encoding declarations
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#!") or "coding:" in line or "encoding:" in line:
                i += 1
                continue
            break

        # Skip docstring
        if i < len(lines) and lines[i].strip().startswith(('"""', "'''")):
            quote = '"""' if '"""' in lines[i] else "'''"
            # Check if it's a single-line docstring (opening and closing quotes on same line)
            if lines[i].count(quote) >= 2:
                i += 1  # Single line docstring, just skip this line
            else:
                i += 1  # Skip opening quote line
                while i < len(lines) and quote not in lines[i]:
                    i += 1
                if i < len(lines):
                    i += 1  # Skip closing quote line

        # Skip existing imports
        while i < len(lines):
            line = lines[i].strip()
            if (
                not line
                or line.startswith("#")
                or line.startswith(("import ", "from "))
            ):
                i += 1
            else:
                break

        return i

    def _apply_ruff_fixes(self, content: str) -> tuple[list[str], str]:
        """Use ruff to detect and fix code issues.

        Args:
            content: Python script content

        Returns:
            Tuple of (list_of_fixes_applied, fixed_content)
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)

            try:
                # Run ruff check with auto-fix
                result = subprocess.run(
                    ["ruff", "check", "--fix", "--quiet", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if (
                    result.returncode == 0 or result.returncode == 1
                ):  # 0 = no issues, 1 = issues fixed
                    # Read the potentially fixed content
                    fixed_content = temp_path.read_text(encoding="utf-8")
                    if fixed_content != content:
                        return ["Applied ruff auto-fixes"], fixed_content

            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            # ruff not available or failed
            pass

        return [], content

    def _detect_type_issues(self, content: str) -> list[str]:
        """Use mypy to detect potential type issues.

        Args:
            content: Python script content

        Returns:
            List of type issues found
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)

            try:
                # Run mypy for type checking
                result = subprocess.run(
                    ["mypy", "--no-error-summary", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.stdout:
                    # Parse mypy output for type issues
                    issues = []
                    for line in result.stdout.strip().split("\n"):
                        if "error:" in line:
                            # Extract just the error message
                            error_part = line.split("error:", 1)[1].strip()
                            issues.append(error_part)
                    return issues

            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            # mypy not available or failed
            pass

        return []

    def auto_correct_code_block(
        self, code_block: CodeBlock
    ) -> tuple[CodeBlock, list[str]]:
        """Auto-correct a code block from GitHub issues.

        Args:
            code_block: Original code block

        Returns:
            Tuple of (corrected_code_block, list_of_fixes_applied)
        """
        from .issue_importer import CodeBlock

        corrected_content, fixes_applied = self.analyze_and_fix_script(
            code_block.content
        )

        # Create a new code block with corrected content
        corrected_block = CodeBlock(
            content=corrected_content,
            language=code_block.language,
            source_location=code_block.source_location,
            is_python_script=code_block.is_python_script,
            confidence_score=code_block.confidence_score,
        )

        return corrected_block, fixes_applied

    def _detect_imports_from_dependencies(
        self, content: str, dependencies: list[str], existing_imports: set[str]
    ) -> set[str]:
        """Detect missing imports using dependency context.

        Args:
            content: Python script content
            dependencies: Known dependencies from PEP 723 metadata
            existing_imports: Set of already existing import statements

        Returns:
            Set of import statements to add
        """
        needed_imports = set()

        # Create mapping of dependency to common classes/functions
        dependency_class_mappings = {
            "xarray": {
                "DataArray": "from xarray import DataArray",
                "Dataset": "from xarray import Dataset",
                "xr.": "import xarray as xr",
            },
            "pandas": {
                "DataFrame": "from pandas import DataFrame",
                "Series": "from pandas import Series",
                "pd.": "import pandas as pd",
            },
            "numpy": {
                "ndarray": "from numpy import ndarray",
                "array": "from numpy import array",  # Could also be numpy.array
                "np.": "import numpy as np",
            },
            "matplotlib": {
                "Figure": "from matplotlib.pyplot import Figure",
                "Axes": "from matplotlib.pyplot import Axes",
                "plt.": "import matplotlib.pyplot as plt",
            },
            "scikit-learn": {
                "LinearRegression": "from sklearn.linear_model import LinearRegression",
                "LogisticRegression": "from sklearn.linear_model import LogisticRegression",
                "RandomForestClassifier": "from sklearn.ensemble import RandomForestClassifier",
                "StandardScaler": "from sklearn.preprocessing import StandardScaler",
                "train_test_split": "from sklearn.model_selection import train_test_split",
            },
            "requests": {
                "Response": "from requests import Response",
                "Session": "from requests import Session",
                "get": "from requests import get",
                "post": "from requests import post",
            },
            "pathlib": {
                "Path": "from pathlib import Path",
            },
            "datetime": {
                "datetime": "from datetime import datetime",
                "date": "from datetime import date",
                "timedelta": "from datetime import timedelta",
            },
            "collections": {
                "defaultdict": "from collections import defaultdict",
                "Counter": "from collections import Counter",
                "deque": "from collections import deque",
            },
            "zarr": {
                "Group": "from zarr import Group",
                "Array": "from zarr import Array",
                "open": "from zarr import open",
                "open_group": "from zarr import open_group",
                "zarr.": "import zarr",
            },
            "icechunk": {
                "IcechunkStore": "from icechunk import IcechunkStore",
                "icechunk.": "import icechunk",
            },
        }

        # Clean up dependency names (remove version specifiers, etc.)
        clean_dependencies = []
        for dep in dependencies:
            # Remove version specifiers, extras, URLs, etc.
            clean_dep = (
                dep.split("==")[0]
                .split(">=")[0]
                .split("<=")[0]
                .split("~=")[0]
                .split("[")[0]
                .split("@")[0]
                .strip()
            )
            clean_dependencies.append(clean_dep)

        # Check for usage of classes/functions that might come from our dependencies
        for dep in clean_dependencies:
            if dep in dependency_class_mappings:
                class_mappings = dependency_class_mappings[dep]
                for class_or_pattern, import_stmt in class_mappings.items():
                    if import_stmt in existing_imports:
                        continue

                    # Check if this class or pattern is used in the content
                    if class_or_pattern.endswith("."):
                        # This is a module alias pattern like "xr."
                        if self._is_usage_pattern_present(content, class_or_pattern):
                            needed_imports.add(import_stmt)
                    else:
                        # This is a class or function name
                        if self._is_class_or_function_used(content, class_or_pattern):
                            needed_imports.add(import_stmt)

        return needed_imports

    def _is_class_or_function_used(self, content: str, name: str) -> bool:
        """Check if a class or function name is used in the content.

        Args:
            content: Python script content
            name: Class or function name to search for

        Returns:
            True if the name is used in actual code
        """
        import re

        # Look for the name used as:
        # 1. Constructor call: Name(...)
        # 2. Assignment: variable = Name(...)
        # 3. Function call: Name()
        # 4. Type annotation: variable: Name
        patterns = [
            rf"\b{re.escape(name)}\s*\(",  # Constructor/function call
            rf"=\s*{re.escape(name)}\s*\(",  # Assignment with call
            rf":\s*{re.escape(name)}\b",  # Type annotation
            rf"\b{re.escape(name)}\b",  # Simple name usage
        ]

        lines = content.split("\n")
        for line in lines:
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Simple check to avoid string literals
            # Additional check: make sure it's not in a string literal
            if any(
                re.search(pattern, stripped) for pattern in patterns
            ) and not self._is_in_string_literal(stripped, name):
                return True

        return False

    def _is_in_string_literal(self, line: str, name: str) -> bool:
        """Check if a name appears only within string literals in a line.

        Args:
            line: Line of code
            name: Name to check for

        Returns:
            True if name only appears in string literals
        """
        # Simple heuristic: if the name appears in quotes, it's probably in a string
        # This is imperfect but good enough for most cases

        # Find all occurrences of the name
        name_positions = []
        start = 0
        while True:
            pos = line.find(name, start)
            if pos == -1:
                break
            name_positions.append(pos)
            start = pos + 1

        if not name_positions:
            return False

        # Check if any occurrence is outside quotes
        return all(
            self._position_in_quotes(line, pos) for pos in name_positions
        )  # All occurrences are inside quotes

    def _position_in_quotes(self, line: str, position: int) -> bool:
        """Check if a position in a line is inside quotes.

        Args:
            line: Line of code
            position: Character position to check

        Returns:
            True if position is inside quotes
        """
        in_single_quote = False
        in_double_quote = False

        for i, char in enumerate(line[:position]):
            if char == "'" and (i == 0 or line[i - 1] != "\\") and not in_double_quote:
                in_single_quote = not in_single_quote
            elif (
                char == '"' and (i == 0 or line[i - 1] != "\\") and not in_single_quote
            ):
                in_double_quote = not in_double_quote

        return in_single_quote or in_double_quote

    def create_correction_summary(self, fixes_applied: list[str]) -> str:
        """Create a readable summary of corrections applied.

        Args:
            fixes_applied: List of fixes that were applied

        Returns:
            Formatted summary string
        """
        if not fixes_applied:
            return "No corrections needed"

        summary = f"Applied {len(fixes_applied)} auto-corrections:\n"
        for i, fix in enumerate(fixes_applied, 1):
            summary += f"  {i}. {fix}\n"

        return summary.rstrip()
