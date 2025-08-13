#!/usr/bin/env python3
"""
Comprehensive Test Suite with Real APIs
Runs all tests including unit, integration, and real API tests
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'

def print_header(text, color=BLUE):
    """Print a colored header"""
    print(f"\n{color}{'='*70}{NC}")
    print(f"{color}{text:^70}{NC}")
    print(f"{color}{'='*70}{NC}")

def run_command(cmd, description, timeout=60):
    """Run a command and return success status"""
    print(f"\n{YELLOW}→ {description}{NC}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Check for success patterns in output
        output = result.stdout + result.stderr
        
        if "FAILED" in output or "failed" in output and "0 failed" not in output:
            # Check if it's actually a failure
            if "passed" in output.lower():
                # Extract pass/fail counts
                import re
                passed_match = re.search(r'(\d+) passed', output)
                failed_match = re.search(r'(\d+) failed', output)
                
                passed = int(passed_match.group(1)) if passed_match else 0
                failed = int(failed_match.group(1)) if failed_match else 0
                
                if failed > 0:
                    print(f"{RED}  ✗ {failed} tests failed{NC}")
                    return False
                elif passed > 0:
                    print(f"{GREEN}  ✓ {passed} tests passed{NC}")
                    return True
            
            print(f"{RED}  ✗ Command failed{NC}")
            return False
        
        if result.returncode == 0:
            print(f"{GREEN}  ✓ Success{NC}")
            return True
        else:
            print(f"{RED}  ✗ Exit code: {result.returncode}{NC}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{RED}  ✗ Timeout after {timeout} seconds{NC}")
        return False
    except Exception as e:
        print(f"{RED}  ✗ Error: {e}{NC}")
        return False

def main():
    """Run comprehensive test suite"""
    start_time = datetime.now()
    
    print_header("🚀 COMPREHENSIVE GTD COACH TEST SUITE", CYAN)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Activate virtual environment and set environment
    venv_activate = "source test_venv/bin/activate && source ~/.env"
    
    # Test categories
    test_suites = [
        {
            'name': 'Environment Check',
            'tests': [
                (f"{venv_activate} && python --version", "Python version"),
                (f"{venv_activate} && pip list | grep -E 'langgraph|langchain|graphiti|neo4j|langfuse' | head -10", "Key packages"),
            ]
        },
        {
            'name': 'Service Connectivity',
            'tests': [
                ("curl -s http://localhost:1234/v1/models | head -1", "LM Studio API"),
                (f"{venv_activate} && python -c \"from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', '!uK-TkCGWdrFfbZUw*j6')); driver.verify_connectivity(); print('Neo4j connected')\"", "Neo4j Database"),
                (f"{venv_activate} && python -c \"import os; print('Timing API key:', 'Set' if os.getenv('TIMING_API_KEY') else 'Missing')\"", "Timing API Key"),
                (f"{venv_activate} && python -c \"import os; print('Langfuse keys:', 'Set' if os.getenv('LANGFUSE_PUBLIC_KEY') else 'Missing')\"", "Langfuse Keys"),
            ]
        },
        {
            'name': 'Unit Tests',
            'tests': [
                (f"{venv_activate} && python -m pytest tests/unit/test_adaptive.py -v --tb=short", "Adaptive Behavior Tests"),
                (f"{venv_activate} && python -m pytest tests/unit/test_pattern_detector.py -v --tb=short", "Pattern Detection Tests"),
                (f"{venv_activate} && python -m pytest tests/unit/test_evaluation.py -v --tb=short", "Evaluation Tests"),
                (f"{venv_activate} && python -m pytest tests/unit/test_custom_entities.py -v --tb=short", "Custom Entity Tests"),
            ]
        },
        {
            'name': 'Integration Tests',
            'tests': [
                (f"{venv_activate} && python -m pytest test_coach_integration.py -v --tb=short", "Coach Integration"),
                (f"{venv_activate} && python -m pytest tests/integration -v --tb=short --co -q | head -20", "Integration Test Discovery"),
            ]
        },
        {
            'name': 'Real API Tests',
            'tests': [
                (f"{venv_activate} && python test_timing_real_api.py", "Timing API Integration"),
                (f"{venv_activate} && python test_langfuse_real_api.py", "Langfuse API Integration"),
                (f"{venv_activate} && python test_neo4j_real_api.py", "Neo4j Database Integration"),
            ]
        },
        {
            'name': 'LLM Integration',
            'tests': [
                (f"{venv_activate} && python -c \"import requests; r = requests.post('http://localhost:1234/v1/chat/completions', json={{'model': 'meta-llama-3.1-8b-instruct', 'messages': [{{'role': 'user', 'content': 'Say test passed in 2 words'}}], 'max_tokens': 10}}); print('LLM Response:', r.json()['choices'][0]['message']['content'])\"", "LM Studio LLM Call"),
            ]
        }
    ]
    
    # Track results
    total_passed = 0
    total_failed = 0
    failed_suites = []
    
    # Run each test suite
    for suite in test_suites:
        print_header(suite['name'])
        suite_passed = 0
        suite_failed = 0
        
        for cmd, description in suite['tests']:
            if run_command(cmd, description):
                suite_passed += 1
                total_passed += 1
            else:
                suite_failed += 1
                total_failed += 1
        
        # Suite summary
        print(f"\n{CYAN}Suite Summary:{NC}")
        print(f"  {GREEN}Passed: {suite_passed}{NC}")
        if suite_failed > 0:
            print(f"  {RED}Failed: {suite_failed}{NC}")
            failed_suites.append(suite['name'])
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_header("📊 FINAL RESULTS", CYAN)
    print(f"Duration: {duration:.1f} seconds")
    print(f"\n{GREEN}Total Passed: {total_passed}{NC}")
    print(f"{RED}Total Failed: {total_failed}{NC}")
    
    if failed_suites:
        print(f"\n{RED}Failed Suites:{NC}")
        for suite in failed_suites:
            print(f"  - {suite}")
    
    # Success rate
    if total_passed + total_failed > 0:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    # Final verdict
    print()
    if total_failed == 0:
        print(f"{GREEN}{'='*70}{NC}")
        print(f"{GREEN}{'🎉 ALL TESTS PASSED WITH REAL APIs! 🎉':^70}{NC}")
        print(f"{GREEN}{'='*70}{NC}")
        return 0
    else:
        print(f"{RED}{'='*70}{NC}")
        print(f"{RED}{f'⚠️ {total_failed} TESTS FAILED ⚠️':^70}{NC}")
        print(f"{RED}{'='*70}{NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())