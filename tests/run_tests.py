#!/usr/bin/env python3
"""
Test runner script for Harithma POS
"""

import sys
import os
import subprocess
import argparse

def run_tests(test_path=None, verbose=False, coverage=False, parallel=False):
    """Run the test suite with specified options."""
    
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=harithmapos', '--cov-report=html', '--cov-report=term'])
    
    if parallel:
        cmd.extend(['-n', 'auto'])
    
    if test_path:
        # Split the test path string into individual paths
        if isinstance(test_path, str) and ' ' in test_path:
            cmd.extend(test_path.split())
        else:
            cmd.append(test_path)
    else:
        cmd.append('tests/')
    
    # Add common options
    cmd.extend([
        '--tb=short',
        '--strict-markers',
        '--disable-warnings'
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 50)
    
    # Run the tests
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run Harithma POS tests')
    parser.add_argument('--path', '-p', help='Specific test file or directory to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', '-c', action='store_true', help='Run with coverage report')
    parser.add_argument('--parallel', '-n', action='store_true', help='Run tests in parallel')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    
    args = parser.parse_args()
    
    # Determine test path
    test_path = args.path
    if args.unit:
        test_path = 'tests/test_employee.py'
    elif args.integration:
        test_path = 'tests/test_employee.py'
    
    # Run tests
    exit_code = run_tests(
        test_path=test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel
    )
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()

