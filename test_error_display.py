# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///

"""Test script that will fail to test error display"""


def main() -> bool:
    # This should fail
    print("This test will fail")
    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
