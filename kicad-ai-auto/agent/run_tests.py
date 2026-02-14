"""
Test runner script for KiCad AI Auto Agent
"""

import subprocess
import sys
import os


def run_unit_tests():
    """Run unit tests"""
    print("Running unit tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "-m", "unit"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_all_tests():
    """Run all tests"""
    print("Running all tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_tests_with_coverage():
    """Run tests with coverage report"""
    print("Running tests with coverage...")
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html"
        ],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


def run_specific_test(test_file):
    """Run a specific test file"""
    print(f"Running {test_file}...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{test_file}", "-v"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run KiCad AI Auto Agent tests")
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Run a specific test file"
    )

    args = parser.parse_args()

    if args.file:
        exit_code = run_specific_test(args.file)
    elif args.coverage:
        exit_code = run_tests_with_coverage()
    elif args.unit:
        exit_code = run_unit_tests()
    else:
        exit_code = run_all_tests()

    sys.exit(exit_code)
