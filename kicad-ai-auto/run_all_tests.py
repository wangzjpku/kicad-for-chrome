#!/usr/bin/env python3
"""
Master test runner for KiCad AI Auto project
Runs all tests: backend (Python) and frontend (TypeScript)
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def run_backend_tests(coverage=False, verbose=False):
    """Run Python backend tests"""
    print("\n" + "=" * 60)
    print("Running Backend (Python) Tests")
    print("=" * 60 + "\n")

    agent_dir = Path(__file__).parent / "agent"

    cmd = [sys.executable, "-m", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])

    result = subprocess.run(cmd, cwd=agent_dir)
    return result.returncode


def run_frontend_tests(coverage=False, verbose=False):
    """Run TypeScript frontend tests"""
    print("\n" + "=" * 60)
    print("Running Frontend (TypeScript) Tests")
    print("=" * 60 + "\n")

    web_dir = Path(__file__).parent / "web"

    cmd = ["npm", "run", "test"]
    if coverage:
        cmd = ["npm", "run", "test:coverage"]
    if not verbose:
        # vitest runs in watch mode by default, use --run for single run
        cmd = ["npm", "run", "test", "--", "--run"]

    result = subprocess.run(cmd, cwd=web_dir)
    return result.returncode


def run_playwright_tests():
    """Run Playwright E2E tests"""
    print("\n" + "=" * 60)
    print("Running Playwright E2E Tests")
    print("=" * 60 + "\n")

    playwright_dir = Path(__file__).parent / "playwright-tests"

    cmd = [sys.executable, "-m", "pytest", "-v"]

    result = subprocess.run(cmd, cwd=playwright_dir)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for KiCad AI Auto project"
    )
    parser.add_argument(
        "--backend",
        action="store_true",
        help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend",
        action="store_true",
        help="Run only frontend tests"
    )
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Run Playwright E2E tests (requires running services)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # If no specific tests selected, run all
    run_all = not (args.backend or args.frontend or args.playwright)

    exit_codes = []

    if run_all or args.backend:
        code = run_backend_tests(coverage=args.coverage, verbose=args.verbose)
        exit_codes.append(("Backend", code))

    if run_all or args.frontend:
        code = run_frontend_tests(coverage=args.coverage, verbose=args.verbose)
        exit_codes.append(("Frontend", code))

    if args.playwright:
        code = run_playwright_tests()
        exit_codes.append(("Playwright", code))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, code in exit_codes:
        status = "PASSED" if code == 0 else "FAILED"
        print(f"  {name}: {status}")

    # Return non-zero if any tests failed
    return 0 if all(code == 0 for _, code in exit_codes) else 1


if __name__ == "__main__":
    sys.exit(main())
