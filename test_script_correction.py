#!/usr/bin/env python3

import sys

sys.path.insert(0, 'src')

from script_bisect.issue_importer import CodeBlock
from script_bisect.script_autocorrect import ScriptAutoCorrector

# Test the auto-corrector with a problematic script
test_code = """x = np.array([1], dtype=np.uint32)
y = np.array([1.0], dtype=np.float32)
v = np.array([[1]], dtype=np.uint32)

da_2d = DataArray(v, dims=["x", "y"], coords={"x": x, "y": y})
df_2d = da_2d.to_dataframe(name="v")
print(df_2d.reset_index().dtypes)"""

corrector = ScriptAutoCorrector()
code_block = CodeBlock(
    content=test_code,
    language="python",
    source_location="test",
    is_python_script=True,
    confidence_score=1.0
)

corrected_block, fixes = corrector.auto_correct_code_block(code_block)

print("=== ORIGINAL CODE ===")
print(test_code)
print("\n=== FIXES APPLIED ===")
for fix in fixes:
    print(f"• {fix}")
print("\n=== CORRECTED CODE ===")
print(corrected_block.content)
