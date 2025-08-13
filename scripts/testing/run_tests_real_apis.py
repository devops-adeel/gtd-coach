#!/usr/bin/env python3
"""
Test Runner with Real APIs
Runs all GTD Coach tests using actual API connections
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple
import time

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(text: str):
    """Print colored header"""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")

def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✅ {text}{NC}")

def print_error(text: str):
    """Print error message"""
    print(f"{RED}❌ {text}{NC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️ {text}{NC}")

def check_environment():
    """Check if required environment variables are set"""
    print_header("Checking Environment")
    
    required_vars = {
        'TIMING_API_KEY': 'Timing app API key',
        'LANGFUSE_PUBLIC_KEY': 'Langfuse public key',
        'LANGFUSE_SECRET_KEY': 'Langfuse secret key',
        'OPENAI_API_KEY': 'OpenAI API key (for Graphiti)',
    }
    
    optional_vars = {
        'LANGFUSE_HOST': 'Langfuse host (defaults to cloud)',
        'NEO4J_URI': 'Neo4j connection URI',
        'NEO4J_USERNAME': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password',
    }
    
    all_set = True
    
    # Check required vars
    for var, description in required_vars.items():
        if os.getenv(var):
            print_success(f"{var}: {description} is set")
        else:
            print_warning(f"{var}: {description} is NOT set (some tests may fail)")
            all_set = False
    
    # Check optional vars
    print("\nOptional variables:")
    for var, description in optional_vars.items():
        if os.getenv(var):
            print_success(f"{var}: {description} is set")
        else:
            print(f"  {var}: {description} not set (using defaults)")
    
    return all_set

def check_services():
    """Check if required services are running"""
    print_header("Checking Services")
    
    services = []
    
    # Check LM Studio
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        if response.status_code == 200:
            print_success("LM Studio is running on port 1234")
            services.append("lm_studio")
        else:
            print_warning("LM Studio returned unexpected status")
    except:
        print_warning("LM Studio is not accessible (some tests may fail)")
    
    # Check Neo4j
    try:
        from neo4j import GraphDatabase
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        driver.close()
        print_success("Neo4j is running and accessible")
        services.append("neo4j")
    except:
        print_warning("Neo4j is not accessible (Graphiti tests may fail)")
    
    # Check Langfuse
    try:
        from langfuse import Langfuse
        client = Langfuse()
        # Just try to initialize - no actual API call needed
        print_success("Langfuse client initialized")
        services.append("langfuse")
    except:
        print_warning("Langfuse client failed to initialize")
    
    return services

def run_test_suite(category: str, path: str, markers: str = None) -> Tuple[int, int, int]:
    """Run a test suite and return results"""
    print_header(f"Running {category}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        path,
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
        "--json-report",
        "--json-report-file=test_report.json"
    ]
    
    if markers:
        cmd.extend(["-m", markers])
    
    # Add real API flags
    env = os.environ.copy()
    env['USE_REAL_APIS'] = 'true'
    env['MOCK_EXTERNAL_APIS'] = 'false'
    env['TEST_MODE'] = 'false'
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
        
        # Parse results
        if Path("test_report.json").exists():
            with open("test_report.json") as f:
                report = json.load(f)
                summary = report.get('summary', {})
                passed = summary.get('passed', 0)
                failed = summary.get('failed', 0)
                skipped = summary.get('skipped', 0)
                
                # Show results
                if passed > 0:
                    print_success(f"Passed: {passed}")
                if failed > 0:
                    print_error(f"Failed: {failed}")
                if skipped > 0:
                    print_warning(f"Skipped: {skipped}")
                
                # Show failed test names
                if failed > 0:
                    print("\nFailed tests:")
                    for test in report.get('tests', []):
                        if test.get('outcome') == 'failed':
                            print(f"  - {test.get('nodeid', 'Unknown')}")
                
                # Clean up
                Path("test_report.json").unlink()
                
                return passed, failed, skipped
        else:
            # Fallback: parse output
            output = result.stdout + result.stderr
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")
            
            if "error" in output.lower() and failed == 0:
                print_error("Collection errors occurred")
                failed = 1
            
            return passed, failed, skipped
            
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return 0, 1, 0

def run_integration_test(name: str, script: str) -> bool:
    """Run a specific integration test script"""
    print(f"\n{YELLOW}Testing: {name}{NC}")
    
    env = os.environ.copy()
    env['USE_REAL_APIS'] = 'true'
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        if result.returncode == 0:
            print_success(f"{name} passed")
            return True
        else:
            print_error(f"{name} failed")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print_warning(f"{name} timed out")
        return False
    except Exception as e:
        print_error(f"{name} error: {e}")
        return False

def main():
    """Main test runner"""
    print_header("🚀 GTD COACH TEST RUNNER - REAL APIs")
    print("This will run all tests with actual API connections")
    print("Note: Some tests may incur API costs")
    
    # Check environment
    env_ok = check_environment()
    if not env_ok:
        print_warning("\nSome environment variables are missing.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
    
    # Check services
    services = check_services()
    print(f"\nAvailable services: {', '.join(services) if services else 'None'}")
    
    # Run test suites
    print_header("Running Test Suites")
    
    test_suites = [
        ("Unit Tests", "tests/unit", None),
        ("Integration Tests", "tests/integration", None),
        ("Agent Tests", "tests/agent", None),
        ("E2E Tests", "tests/e2e", None),
    ]
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for name, path, markers in test_suites:
        if Path(path).exists():
            passed, failed, skipped = run_test_suite(name, path, markers)
            total_passed += passed
            total_failed += failed
            total_skipped += skipped
        else:
            print_warning(f"Skipping {name}: {path} not found")
    
    # Run specific integration tests
    print_header("Running Specific Integration Tests")
    
    integration_tests = [
        ("Timing Integration", "test_timing_integration.py"),
        ("Graphiti Connection", "test_graphiti_connection.py"),
        ("Langfuse Integration", "test_langfuse.py"),
        ("Enhanced Graphiti", "test_enhanced_graphiti.py"),
        ("E2E Trace Linking", "test_e2e_trace_linking.py"),
    ]
    
    integration_passed = 0
    integration_failed = 0
    
    for name, script in integration_tests:
        if Path(script).exists():
            if run_integration_test(name, script):
                integration_passed += 1
            else:
                integration_failed += 1
        else:
            print_warning(f"Skipping {name}: {script} not found")
    
    # Final summary
    print_header("📊 FINAL SUMMARY")
    print(f"Test Suites:")
    print(f"  {GREEN}Passed: {total_passed}{NC}")
    print(f"  {RED}Failed: {total_failed}{NC}")
    print(f"  {YELLOW}Skipped: {total_skipped}{NC}")
    print(f"\nIntegration Tests:")
    print(f"  {GREEN}Passed: {integration_passed}{NC}")
    print(f"  {RED}Failed: {integration_failed}{NC}")
    
    success_rate = 0
    if (total_passed + total_failed) > 0:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
    
    print(f"\nOverall Success Rate: {success_rate:.1f}%")
    
    if total_failed == 0 and integration_failed == 0:
        print_success("\n🎉 ALL TESTS PASSED WITH REAL APIs! 🎉")
        return 0
    else:
        print_error(f"\n{total_failed + integration_failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())