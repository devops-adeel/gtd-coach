#!/usr/bin/env python3
"""
Comprehensive test runner for GTD Coach test suite.
Executes tests in categories with proper mocking and reporting.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{CYAN}▶ {title}{RESET}")
    print(f"{CYAN}{'-'*40}{RESET}")


def setup_environment() -> None:
    """Set up test environment variables from .env.test."""
    print_section("Setting up test environment")
    
    # Ensure we're using .env.test, not .env.graphiti
    env_test = Path(__file__).parent / '.env.test'
    if not env_test.exists():
        print(f"{RED}✗ .env.test not found! Creating secure test configuration...{RESET}")
        # This shouldn't happen as we already created it, but just in case
        return
    
    # Load .env.test
    with open(env_test) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    # Force test mode
    os.environ['TEST_MODE'] = 'true'
    os.environ['PYTHONPATH'] = str(Path(__file__).parent)
    
    print(f"{GREEN}✓ Test environment configured (using mock credentials){RESET}")
    print(f"  - Neo4j: {os.environ.get('NEO4J_URI', 'not set')}")
    print(f"  - OpenAI: {'mock' if 'mock' in os.environ.get('OPENAI_API_KEY', '') else 'WARNING: Real key detected!'}")
    print(f"  - Test Mode: {os.environ.get('TEST_MODE', 'not set')}")


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    print_section("Checking dependencies")
    
    required = ['pytest', 'pytest-asyncio', 'pytest-cov', 'pytest-mock']
    missing = []
    
    for package in required:
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract version
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':')[1].strip()
                        print(f"{GREEN}✓ {package} ({version}){RESET}")
                        break
            else:
                missing.append(package)
                print(f"{RED}✗ {package} not found{RESET}")
        except Exception as e:
            missing.append(package)
            print(f"{RED}✗ {package} check failed: {e}{RESET}")
    
    if missing:
        print(f"\n{YELLOW}Missing packages: {', '.join(missing)}{RESET}")
        print(f"{YELLOW}Install with: pip install {' '.join(missing)}{RESET}")
        return False
    
    return True


def discover_tests() -> Dict[str, List[str]]:
    """Discover and categorize all test files."""
    print_section("Discovering tests")
    
    test_dir = Path(__file__).parent / 'tests'
    categories = {
        'unit': [],
        'integration': [],
        'other': []
    }
    
    # Find all test files
    for test_file in test_dir.rglob('test_*.py'):
        # Skip __pycache__ and venv
        if '__pycache__' in str(test_file) or 'venv' in str(test_file):
            continue
        
        relative_path = test_file.relative_to(Path(__file__).parent)
        
        # Categorize based on directory structure
        if 'unit' in test_file.parts:
            categories['unit'].append(str(relative_path))
        elif 'integration' in test_file.parts:
            categories['integration'].append(str(relative_path))
        else:
            categories['other'].append(str(relative_path))
    
    # Print discovery results
    total = sum(len(files) for files in categories.values())
    print(f"Found {total} test files:")
    print(f"  - Unit tests: {len(categories['unit'])}")
    print(f"  - Integration tests: {len(categories['integration'])}")
    print(f"  - Other tests: {len(categories['other'])}")
    
    return categories


def run_test_category(category: str, test_files: List[str], verbose: bool = True) -> Tuple[bool, Dict]:
    """Run a category of tests and return results."""
    print_section(f"Running {category} tests")
    
    if not test_files:
        print(f"{YELLOW}No {category} tests found{RESET}")
        return True, {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0}
    
    # Build pytest command
    cmd = [
        sys.executable, '-m', 'pytest',
        '--tb=short',
        '--no-header',
        '-q' if not verbose else '-v',
        '--color=yes',
        f'--junit-xml=test-results-{category}.xml',
        '--import-mode=importlib'
    ]
    
    # Add marker filter for categories
    if category == 'unit':
        cmd.append('-m')
        cmd.append('not integration and not requires_neo4j and not requires_api_keys')
    elif category == 'integration':
        cmd.append('-m')
        cmd.append('not requires_neo4j and not requires_api_keys')
    
    # Add test files
    cmd.extend(test_files)
    
    # Run tests
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )
        
        duration = time.time() - start_time
        
        # Parse results from output
        output = result.stdout + result.stderr
        stats = parse_pytest_output(output)
        
        # Print summary
        if stats['passed'] > 0:
            print(f"{GREEN}✓ {stats['passed']} passed{RESET}", end=' ')
        if stats['failed'] > 0:
            print(f"{RED}✗ {stats['failed']} failed{RESET}", end=' ')
        if stats['skipped'] > 0:
            print(f"{YELLOW}⊘ {stats['skipped']} skipped{RESET}", end=' ')
        
        print(f"(in {duration:.2f}s)")
        
        # Show failures if any
        if stats['failed'] > 0 and verbose:
            print(f"\n{RED}Failed tests:{RESET}")
            for line in output.split('\n'):
                if 'FAILED' in line:
                    print(f"  {line.strip()}")
        
        return result.returncode == 0, stats
        
    except Exception as e:
        print(f"{RED}✗ Error running {category} tests: {e}{RESET}")
        return False, {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': str(e)}


def parse_pytest_output(output: str) -> Dict:
    """Parse pytest output to extract statistics."""
    stats = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Look for summary line
    for line in output.split('\n'):
        if 'passed' in line or 'failed' in line or 'skipped' in line:
            # Extract numbers from patterns like "5 passed, 2 failed"
            import re
            
            passed = re.search(r'(\d+) passed', line)
            if passed:
                stats['passed'] = int(passed.group(1))
            
            failed = re.search(r'(\d+) failed', line)
            if failed:
                stats['failed'] = int(failed.group(1))
            
            skipped = re.search(r'(\d+) skipped', line)
            if skipped:
                stats['skipped'] = int(skipped.group(1))
            
            errors = re.search(r'(\d+) error', line)
            if errors:
                stats['errors'] = int(errors.group(1))
    
    stats['total'] = stats['passed'] + stats['failed'] + stats['skipped'] + stats['errors']
    return stats


def run_coverage_analysis() -> None:
    """Run coverage analysis on the test suite."""
    print_section("Running coverage analysis")
    
    cmd = [
        sys.executable, '-m', 'pytest',
        '--cov=gtd_coach',
        '--cov-report=term-missing:skip-covered',
        '--cov-report=html',
        '--quiet',
        'tests/',
        '--import-mode=importlib',
        '-m', 'not requires_neo4j and not requires_api_keys'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Extract coverage percentage
        for line in result.stdout.split('\n'):
            if 'TOTAL' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage = parts[-1]
                    if coverage.endswith('%'):
                        cov_value = float(coverage[:-1])
                        if cov_value >= 80:
                            print(f"{GREEN}✓ Coverage: {coverage}{RESET}")
                        elif cov_value >= 60:
                            print(f"{YELLOW}⚠ Coverage: {coverage}{RESET}")
                        else:
                            print(f"{RED}✗ Coverage: {coverage}{RESET}")
                        
                        print(f"  HTML report: htmlcov/index.html")
                        break
        
    except Exception as e:
        print(f"{YELLOW}⚠ Coverage analysis failed: {e}{RESET}")


def generate_report(results: Dict) -> None:
    """Generate a comprehensive test report."""
    print_header("TEST EXECUTION SUMMARY")
    
    # Calculate totals
    total_tests = sum(r.get('total', 0) for r in results.values())
    total_passed = sum(r.get('passed', 0) for r in results.values())
    total_failed = sum(r.get('failed', 0) for r in results.values())
    total_skipped = sum(r.get('skipped', 0) for r in results.values())
    
    # Print category results
    for category, stats in results.items():
        if stats.get('total', 0) > 0:
            status = "✓" if stats.get('failed', 0) == 0 else "✗"
            color = GREEN if status == "✓" else RED
            print(f"\n{category.upper():12} {color}{status}{RESET}")
            print(f"  Tests:    {stats.get('total', 0)}")
            print(f"  Passed:   {stats.get('passed', 0)}")
            print(f"  Failed:   {stats.get('failed', 0)}")
            print(f"  Skipped:  {stats.get('skipped', 0)}")
    
    # Print overall summary
    print(f"\n{BOLD}OVERALL{RESET}")
    print(f"  Total:    {total_tests}")
    print(f"  {GREEN}Passed:   {total_passed}{RESET}")
    if total_failed > 0:
        print(f"  {RED}Failed:   {total_failed}{RESET}")
    if total_skipped > 0:
        print(f"  {YELLOW}Skipped:  {total_skipped}{RESET}")
    
    # Calculate success rate
    if total_tests > 0:
        success_rate = (total_passed / (total_tests - total_skipped)) * 100 if (total_tests - total_skipped) > 0 else 0
        
        if success_rate >= 90:
            print(f"\n{GREEN}✅ Success Rate: {success_rate:.1f}%{RESET}")
        elif success_rate >= 70:
            print(f"\n{YELLOW}⚠️  Success Rate: {success_rate:.1f}%{RESET}")
        else:
            print(f"\n{RED}❌ Success Rate: {success_rate:.1f}%{RESET}")
    
    # Save report to file
    report_file = Path(__file__).parent / 'test_report.json'
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'total': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'skipped': total_skipped,
                'success_rate': success_rate if total_tests > 0 else 0
            }
        }, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main test execution flow."""
    print_header("GTD COACH COMPREHENSIVE TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        print(f"\n{RED}❌ Missing dependencies. Please install them first.{RESET}")
        return 1
    
    # Discover tests
    test_categories = discover_tests()
    
    # Run tests by category
    results = {}
    all_passed = True
    
    # Run unit tests first (they should be fastest and most reliable)
    if test_categories['unit']:
        passed, stats = run_test_category('unit', test_categories['unit'], verbose=False)
        results['unit'] = stats
        all_passed = all_passed and passed
    
    # Run integration tests
    if test_categories['integration']:
        passed, stats = run_test_category('integration', test_categories['integration'], verbose=False)
        results['integration'] = stats
        all_passed = all_passed and passed
    
    # Run other tests
    if test_categories['other']:
        passed, stats = run_test_category('other', test_categories['other'], verbose=False)
        results['other'] = stats
        all_passed = all_passed and passed
    
    # Run coverage analysis
    run_coverage_analysis()
    
    # Generate report
    generate_report(results)
    
    # Final status
    print(f"\n{BLUE}{'='*60}{RESET}")
    if all_passed:
        print(f"{GREEN}🎉 All tests passed successfully!{RESET}")
        return 0
    else:
        print(f"{YELLOW}⚠️  Some tests failed. Review the output above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())