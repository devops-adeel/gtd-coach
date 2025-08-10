#!/usr/bin/env python3
"""
Comprehensive test runner to achieve 100% code coverage.
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def setup_environment():
    """Set up test environment variables"""
    os.environ["LANGFUSE_HOST"] = "http://langfuse-prod-langfuse-web-1.orb.local"
    os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed"
    os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9"
    os.environ["PYTHONPATH"] = str(Path.home() / "gtd-coach")
    print(f"{GREEN}✓ Environment variables set{RESET}")

def run_test_file(test_file):
    """Run a single test file and return success status"""
    print(f"\n{BLUE}Running {test_file}...{RESET}")
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=Path.home() / "gtd-coach"
        )
        
        if result.returncode == 0:
            # Count passes in output
            passes = result.stdout.count("✓") + result.stdout.count("PASS")
            print(f"{GREEN}✓ {test_file}: {passes} tests passed{RESET}")
            return True
        else:
            print(f"{RED}✗ {test_file} failed{RESET}")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"{RED}✗ Error running {test_file}: {e}{RESET}")
        return False

def run_all_tests():
    """Run all test files"""
    test_files = [
        "test_prompt_management.py",
        "test_e2e_trace_linking.py",
        "analyze_prompt_performance.py"
    ]
    
    results = {}
    for test_file in test_files:
        results[test_file] = run_test_file(test_file)
    
    return results

def generate_coverage_report():
    """Generate coverage report for all test files"""
    print(f"\n{BLUE}Generating coverage report...{RESET}")
    
    # Focus on the main files that need testing
    files_to_test = [
        "test_prompt_management.py",
        "test_e2e_trace_linking.py",
        "analyze_prompt_performance.py"
    ]
    
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=test_prompt_management",
        "--cov=test_e2e_trace_linking", 
        "--cov=analyze_prompt_performance",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--tb=short",
        "-q",
        *files_to_test
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.home() / "gtd-coach"
        )
        
        # Parse coverage from output
        for line in result.stdout.split('\n'):
            if 'TOTAL' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage = parts[-2] if parts[-2].endswith('%') else parts[-1]
                    print(f"\n{BLUE}Overall Coverage: {coverage}{RESET}")
                    
                    # Check if 100% coverage achieved
                    coverage_num = float(coverage.rstrip('%'))
                    if coverage_num == 100:
                        print(f"{GREEN}✅ 100% test coverage achieved!{RESET}")
                    elif coverage_num >= 90:
                        print(f"{YELLOW}⚠️ {coverage_num}% coverage - almost there!{RESET}")
                    else:
                        print(f"{RED}❌ {coverage_num}% coverage - more tests needed{RESET}")
        
        # Show missing lines if any
        if "Missing" in result.stdout:
            print(f"\n{YELLOW}Files with missing coverage:{RESET}")
            for line in result.stdout.split('\n'):
                if 'test_' in line and '%' in line and 'Missing' not in line:
                    print(f"  {line.strip()}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"{RED}Error generating coverage report: {e}{RESET}")
        return False

def main():
    """Main test runner"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}GTD Coach Comprehensive Test Runner{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Setup environment
    setup_environment()
    
    # Run all tests
    print(f"\n{BLUE}Running all tests...{RESET}")
    test_results = run_all_tests()
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_file, result in test_results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{test_file:<40} {status}")
    
    print(f"{BLUE}{'-'*60}{RESET}")
    print(f"Total: {passed}/{total} test files passed")
    
    if passed == total:
        print(f"\n{GREEN}✅ All tests passed!{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ Some tests failed{RESET}")
    
    # Generate coverage report
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}COVERAGE ANALYSIS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    coverage_success = generate_coverage_report()
    
    # Final status
    if passed == total and coverage_success:
        print(f"\n{GREEN}🎉 SUCCESS: All tests pass with good coverage!{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}⚠️ More work needed to achieve 100% coverage{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())