#!/usr/bin/env python3
"""
Simple test runner for GTD Coach that works around dependency conflicts
Runs tests with minimal dependencies and mocks
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def install_test_dependencies():
    """Install only essential test dependencies"""
    print("📦 Installing test dependencies...")
    
    essential_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-mock",
        "pytest-json-report",
        "requests",
        "python-dotenv",
        "PyYAML",
        "numpy",
        "scipy",
        "aiofiles",
    ]
    
    # Use --user flag to bypass externally managed environment
    for package in essential_packages:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "--quiet", package],
                check=True,
                capture_output=True
            )
            print(f"  ✅ {package}")
        except subprocess.CalledProcessError:
            print(f"  ⚠️ {package} (may already be installed)")
    
    return True

def setup_mock_environment():
    """Set up environment for testing with mocks"""
    print("\n⚙️ Setting up test environment...")
    
    # Create mock modules for conflicting dependencies
    mock_modules_code = """
# Mock implementations for testing

class MockGraphitiCore:
    class GraphitiClient:
        async def add_episode(self, data):
            return {"id": "mock_id"}
        
        async def search_nodes(self, query):
            return []
        
        async def get_user_context(self):
            return {"user_id": "test_user"}

class MockLangGraph:
    class StateGraph:
        def __init__(self, *args, **kwargs):
            pass
        
        def add_node(self, *args, **kwargs):
            pass
        
        def add_edge(self, *args, **kwargs):
            pass
        
        def compile(self, *args, **kwargs):
            return self
    
    class Command:
        def __init__(self, **kwargs):
            self.resume = kwargs.get('resume')
            self.update = kwargs.get('update')
    
    class NodeInterrupt(Exception):
        pass

class MockLangchain:
    class BaseTool:
        def __init__(self, *args, **kwargs):
            pass
        
        def invoke(self, *args, **kwargs):
            return {"result": "mocked"}

class MockNeo4j:
    class GraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):
            return MockNeo4j.Driver()
    
    class Driver:
        def close(self):
            pass

# Mock the imports
import sys
sys.modules['graphiti_core'] = MockGraphitiCore
sys.modules['langgraph'] = MockLangGraph
sys.modules['langgraph.graph'] = MockLangGraph
sys.modules['langgraph.errors'] = MockLangGraph
sys.modules['langgraph.constants'] = MockLangGraph
sys.modules['langgraph.checkpoint'] = MockLangGraph
sys.modules['langgraph.checkpoint.sqlite'] = MockLangGraph
sys.modules['langgraph.checkpoint.memory'] = MockLangGraph
sys.modules['langgraph.checkpoint.base'] = MockLangGraph
sys.modules['langchain_core'] = MockLangchain
sys.modules['langchain_core.tools'] = MockLangchain
sys.modules['langchain_openai'] = MockLangchain
sys.modules['langchain_community'] = MockLangchain
sys.modules['neo4j'] = MockNeo4j
sys.modules['langfuse'] = type('MockLangfuse', (), {})()
sys.modules['langfuse.openai'] = type('MockLangfuseOpenAI', (), {'OpenAI': object})()
"""
    
    # Write mock modules
    mock_file = project_root / "test_mocks.py"
    with open(mock_file, 'w') as f:
        f.write(mock_modules_code)
    
    # Set environment variables
    os.environ['TEST_MODE'] = 'true'
    os.environ['MOCK_EXTERNAL_APIS'] = 'true'
    os.environ['PYTHONPATH'] = str(project_root)
    
    print("  ✅ Mock environment configured")
    return mock_file

def run_tests(test_path: str, markers: str = None) -> Dict:
    """Run tests with mocks"""
    print(f"\n🧪 Running tests from {test_path}...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--no-header",
        "--json-report",
        "--json-report-file=test_report.json",
        "-p", "no:warnings"
    ]
    
    if markers:
        cmd.extend(["-m", markers])
    
    # Import mocks before running tests
    exec(open("test_mocks.py").read())
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        # Parse results
        if Path("test_report.json").exists():
            with open("test_report.json") as f:
                report = json.load(f)
                summary = report.get('summary', {})
                
                print(f"  Passed: {summary.get('passed', 0)}")
                print(f"  Failed: {summary.get('failed', 0)}")
                print(f"  Skipped: {summary.get('skipped', 0)}")
                
                # Clean up
                Path("test_report.json").unlink()
                
                return summary
        else:
            # Fallback parsing
            output = result.stdout
            if "passed" in output:
                print("  Tests executed (see output for details)")
            return {"error": "Could not parse results", "output": output[:500]}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e)}

def main():
    """Main test runner"""
    print("="*60)
    print("🚀 SIMPLE TEST RUNNER FOR GTD COACH")
    print("="*60)
    
    # Install minimal dependencies
    if not install_test_dependencies():
        print("❌ Failed to install dependencies")
        return 1
    
    # Set up mocks
    mock_file = setup_mock_environment()
    
    # Run different test categories
    test_categories = [
        ("Unit Tests", "tests/unit", "not requires_neo4j and not requires_api_keys"),
        ("Integration Tests", "tests/integration", "not slow and not requires_neo4j"),
        ("Agent Tests", "tests/agent", "not slow and not requires_neo4j and not requires_api_keys"),
    ]
    
    all_results = {}
    total_passed = 0
    total_failed = 0
    
    for name, path, markers in test_categories:
        test_path = project_root / path
        if test_path.exists():
            print(f"\n### {name} ###")
            results = run_tests(str(test_path), markers)
            all_results[name] = results
            total_passed += results.get('passed', 0)
            total_failed += results.get('failed', 0)
        else:
            print(f"\n⚠️ Skipping {name}: {path} not found")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    
    if total_failed == 0 and total_passed > 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total_failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())