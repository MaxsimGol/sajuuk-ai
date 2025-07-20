import unittest


def run_all_tests():
    """
    Discovers and runs all tests in the 'tests/' directory.

    This script acts as the main entry point for our project's test suite.
    It automatically finds any file starting with 'test_' and any class
    inheriting from unittest.TestCase, and runs all the tests within them.

    This allows us to verify the correctness of the entire Sajuuk AI
    architecture with a single command.
    """
    # Create a TestLoader instance
    loader = unittest.TestLoader()

    # Discover tests starting from the 'tests' directory
    # The pattern 'test_*.py' will match all our test files.
    suite = loader.discover(start_dir="tests", pattern="test_*.py")

    # Create a TestResult runner
    runner = unittest.TextTestRunner()

    # Run the test suite
    print("Discovering and running Sajuuk AI test suite...")
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed.")


if __name__ == "__main__":
    run_all_tests()
