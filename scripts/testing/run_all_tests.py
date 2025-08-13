#!/usr/bin/env python3
"""
Comprehensive test runner for GTD Coach
Handles dependencies, mocking, and runs all test suites
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
import importlib.util

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Manages test execution with proper setup and teardown"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {}
        self.missing_deps = []
        self.available_services = {}
        
    def check_dependencies(self) -> bool:
        """Check and install missing dependencies"""
        print("🔍 Checking dependencies...")
        
        required_packages = {
            'pytest': 'pytest>=7.0.0',
            'pytest_asyncio': 'pytest-asyncio>=0.21.0',
            'pytest_mock': 'pytest-mock>=3.10.0',
            'langgraph': 'langgraph==0.2.0',
            'langchain_core': 'langchain-core==0.3.0',
            'neo4j': 'neo4j==5.28.2',
            'langfuse': 'langfuse[openai]==3.2.3',
            'graphiti_core': 'graphiti-core[openai]==0.18.5',
        }
        
        for module_name, package_spec in required_packages.items():
            if not self._check_module(module_name):
                self.missing_deps.append(package_spec)
                print(f"  ❌ Missing: {package_spec}")
            else:
                print(f"  ✅ Found: {module_name}")
        
        if self.missing_deps:
            print(f"\n📦 Installing {len(self.missing_deps)} missing packages...")
            for package in self.missing_deps:
                self._install_package(package)
        
        return len(self.missing_deps) == 0 or self._verify_installations()
    
    def _check_module(self, module_name: str) -> bool:
        """Check if a Python module is installed"""
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    
    def _install_package(self, package_spec: str):
        """Install a Python package"""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package_spec],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"    ✅ Installed: {package_spec}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"    ⚠️ Failed to install {package_spec}: {e}")
            return False
    
    def _verify_installations(self) -> bool:
        """Verify that installations succeeded"""
        for package in self.missing_deps:
            # Extract module name from package spec
            module_name = package.split('[')[0].split('>=')[0].split('==')[0].replace('-', '_')
            if not self._check_module(module_name):
                return False
        return True
    
    def setup_test_environment(self):
        """Set up test environment variables and configuration"""
        print("\n⚙️ Setting up test environment...")
        
        # Create test environment file
        env_test_path = self.project_root / ".env.test"
        env_content = """
# Test Environment Configuration
TEST_MODE=true
LM_STUDIO_URL=http://localhost:1234
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
MOCK_EXTERNAL_APIS=true
GRAPHITI_SKIP_TRIVIAL=true
GRAPHITI_BATCH_SIZE=5
USE_GTD_ENTITIES=false
SEMAPHORE_LIMIT=2
"""
        
        with open(env_test_path, 'w') as f:
            f.write(env_content.strip())
        
        # Set environment variables
        os.environ['TEST_MODE'] = 'true'
        os.environ['MOCK_EXTERNAL_APIS'] = 'true'
        os.environ['PYTHONPATH'] = str(self.project_root)
        
        print("  ✅ Test environment configured")
    
    def check_services(self):
        """Check availability of external services"""
        print("\n🔌 Checking external services...")
        
        # Check Neo4j
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "testpassword")
            )
            driver.close()
            self.available_services['neo4j'] = True
            print("  ✅ Neo4j: Available")
        except Exception:
            self.available_services['neo4j'] = False
            print("  ⚠️ Neo4j: Not available (tests will use mocks)")
        
        # Check LM Studio
        try:
            import requests
            response = requests.get("http://localhost:1234/v1/models", timeout=1)
            self.available_services['lm_studio'] = response.status_code == 200
            print("  ✅ LM Studio: Available")
        except Exception:
            self.available_services['lm_studio'] = False
            print("  ⚠️ LM Studio: Not available (tests will use mocks)")
        
        return self.available_services
    
    def run_test_suite(self, category: str, path: str, markers: str = None) -> Tuple[bool, Dict]:
        """Run a specific test suite"""
        print(f"\n🧪 Running {category} tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            path,
            "-v",
            "--tb=short",
            "--no-header",
            "--json-report",
            f"--json-report-file=test_report_{category}.json"
        ]
        
        if markers:
            # Skip tests requiring unavailable services
            skip_markers = []
            if not self.available_services.get('neo4j'):
                skip_markers.append("not requires_neo4j")
            if not self.available_services.get('lm_studio'):
                skip_markers.append("not requires_lm_studio")
            
            if skip_markers:
                markers = f"{markers} and {' and '.join(skip_markers)}"
            
            cmd.extend(["-m", markers])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            # Parse results
            report_file = self.project_root / f"test_report_{category}.json"
            if report_file.exists():
                with open(report_file) as f:
                    report = json.load(f)
                    
                summary = report.get('summary', {})
                passed = summary.get('passed', 0)
                failed = summary.get('failed', 0)
                skipped = summary.get('skipped', 0)
                total = summary.get('total', 0)
                
                print(f"  Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")
                
                # Store results
                self.test_results[category] = {
                    'passed': passed,
                    'failed': failed,
                    'skipped': skipped,
                    'total': total,
                    'success': failed == 0
                }
                
                # Clean up report file
                report_file.unlink()
                
                return failed == 0, self.test_results[category]
            else:
                # Fallback: parse output
                output = result.stdout + result.stderr
                if "passed" in output:
                    # Extract test counts from output
                    import re
                    match = re.search(r'(\d+) passed', output)
                    passed = int(match.group(1)) if match else 0
                    match = re.search(r'(\d+) failed', output)
                    failed = int(match.group(1)) if match else 0
                    
                    self.test_results[category] = {
                        'passed': passed,
                        'failed': failed,
                        'success': failed == 0
                    }
                    print(f"  Results: {passed} passed, {failed} failed")
                    return failed == 0, self.test_results[category]
                
                return False, {'error': 'Could not parse results'}
                
        except Exception as e:
            print(f"  ❌ Error running {category} tests: {e}")
            return False, {'error': str(e)}
    
    def run_all_tests(self):
        """Run all test suites in order"""
        print("\n" + "="*60)
        print("🚀 RUNNING ALL GTD COACH TESTS")
        print("="*60)
        
        # Check dependencies
        if not self.check_dependencies():
            print("\n❌ Missing dependencies. Please install required packages.")
            return False
        
        # Setup environment
        self.setup_test_environment()
        
        # Check services
        self.check_services()
        
        # Define test suites
        test_suites = [
            ("Unit Tests", "tests/unit", "unit"),
            ("Integration Tests", "tests/integration", "integration and not slow"),
            ("Agent Tests (Fast)", "tests/agent", "not slow and not requires_neo4j"),
            ("Agent Tests (E2E)", "tests/agent", "slow or e2e"),
        ]
        
        all_passed = True
        
        # Run each test suite
        for name, path, markers in test_suites:
            test_path = self.project_root / path
            if test_path.exists():
                success, results = self.run_test_suite(name, str(test_path), markers)
                all_passed = all_passed and success
            else:
                print(f"\n⚠️ Skipping {name}: Path {path} not found")
        
        # Print summary
        self.print_summary(all_passed)
        
        return all_passed
    
    def print_summary(self, all_passed: bool):
        """Print test execution summary"""
        print("\n" + "="*60)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*60)
        
        total_passed = sum(r.get('passed', 0) for r in self.test_results.values())
        total_failed = sum(r.get('failed', 0) for r in self.test_results.values())
        total_skipped = sum(r.get('skipped', 0) for r in self.test_results.values())
        total_tests = sum(r.get('total', 0) for r in self.test_results.values())
        
        for category, results in self.test_results.items():
            status = "✅" if results.get('success', False) else "❌"
            print(f"\n{status} {category}:")
            print(f"   Passed: {results.get('passed', 0)}")
            print(f"   Failed: {results.get('failed', 0)}")
            print(f"   Skipped: {results.get('skipped', 0)}")
        
        print(f"\n{'='*60}")
        print(f"TOTAL: {total_passed}/{total_tests} passed")
        print(f"Failed: {total_failed}, Skipped: {total_skipped}")
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n❌ {total_failed} tests failed. Please review the failures above.")
        
        print("="*60)


def main():
    """Main entry point"""
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()