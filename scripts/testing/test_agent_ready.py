#!/usr/bin/env python3
"""
Test script to verify agent implementations are ready for use.
Tests imports, initialization, and basic functionality with mock data.
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Test results collector
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {"passed": 0, "failed": 0}
}

def test_step(name: str, func):
    """Run a test step and record results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    
    try:
        result = func()
        test_results["tests"].append({
            "name": name,
            "status": "passed",
            "details": result
        })
        test_results["summary"]["passed"] += 1
        print(f"✅ {name}: PASSED")
        if result:
            print(f"   Details: {result}")
        return True
    except Exception as e:
        test_results["tests"].append({
            "name": name,
            "status": "failed",
            "error": str(e)
        })
        test_results["summary"]["failed"] += 1
        print(f"❌ {name}: FAILED")
        print(f"   Error: {e}")
        return False


def test_langchain_openai_import():
    """Test if langchain-openai is properly installed"""
    import langchain_openai
    from langchain_openai import ChatOpenAI
    return f"langchain-openai version: {langchain_openai.__version__ if hasattr(langchain_openai, '__version__') else 'unknown'}"


def test_agent_core_imports():
    """Test if agent core modules can be imported"""
    from gtd_coach.agent import GTDAgent
    from gtd_coach.agent.core import AgentCore
    from gtd_coach.agent.state import AgentState
    return "All core imports successful"


def test_clarify_workflow_init():
    """Test if clarify workflow can be initialized"""
    from gtd_coach.agent.workflows.daily_clarify import DailyClarifyWorkflow
    
    # Initialize without Graphiti (simpler)
    workflow = DailyClarifyWorkflow(use_graphiti=False)
    
    # Check graph is built
    if workflow.graph:
        nodes = list(workflow.graph.nodes.keys())
        return f"Workflow initialized with {len(nodes)} nodes: {', '.join(nodes[:5])}"
    else:
        raise ValueError("Workflow graph not built")


def test_review_workflow_init():
    """Test if weekly review workflow can be initialized"""
    from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
    
    workflow = WeeklyReviewWorkflow()
    
    # Check if graph exists
    if hasattr(workflow, 'graph'):
        return "Weekly review workflow initialized"
    else:
        # Check if it has the build method
        if hasattr(workflow, 'build_graph'):
            graph = workflow.build_graph()
            return f"Weekly review graph built with {len(graph.nodes)} nodes"
        else:
            raise ValueError("Workflow missing graph or build_graph method")


def test_todoist_tools():
    """Test if Todoist tools can be imported and checked"""
    from gtd_coach.agent.tools.todoist import (
        get_inbox_tasks_tool,
        check_deep_work_limit_tool,
        mark_task_complete_tool
    )
    
    # Test without API key (should return config error gracefully)
    if not os.getenv("TODOIST_API_KEY"):
        result = get_inbox_tasks_tool()
        if result.get("configured") == False:
            return "Todoist tools loaded (API key not configured - expected)"
    else:
        result = get_inbox_tasks_tool()
        if result.get("tasks") is not None:
            return f"Todoist connected: {len(result['tasks'])} inbox tasks"
    
    return "Todoist tools imported successfully"


def test_clarify_mock_execution():
    """Test clarify workflow with mock data (no real API calls)"""
    from gtd_coach.agent.workflows.daily_clarify import DailyClarifyWorkflow, ClarifyState
    
    workflow = DailyClarifyWorkflow(use_graphiti=False)
    
    # Create mock state
    mock_state = {
        "inbox_tasks": [
            {"id": "mock1", "content": "Review documentation"},
            {"id": "mock2", "content": "Fix bug in login"},
            {"id": "mock3", "content": "Buy groceries"}
        ],
        "current_task_index": 0,
        "processed_count": 0,
        "deleted_count": 0,
        "deep_work_count": 0,
        "quick_task_count": 0,
        "session_id": "test_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "session_active": True,
        "needs_break": False,
        "messages": []
    }
    
    # Test preview node (simplest node)
    if hasattr(workflow, 'preview_session_node'):
        result = workflow.preview_session_node(mock_state)
        return f"Preview node executed: {len(mock_state['inbox_tasks'])} tasks ready"
    
    return "Workflow structure verified"


def test_migration_adapter():
    """Test the migration adapter that switches between implementations"""
    from gtd_coach.migration.clarify_adapter import ClarifyMigrationAdapter
    
    adapter = ClarifyMigrationAdapter()
    
    # Check status
    status = adapter.get_migration_status()
    
    details = []
    if "days_until_deprecation" in status:
        details.append(f"Days until deprecation: {status['days_until_deprecation']}")
    if "default_implementation" in status:
        details.append(f"Default: {status['default_implementation']}")
    
    return " | ".join(details) if details else "Adapter initialized"


def test_openai_api_key():
    """Check if OpenAI API key is configured"""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return f"API key configured (length: {len(api_key)})"
    else:
        return "⚠️ OPENAI_API_KEY not set - agent won't be able to make LLM calls"


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🔬 GTD Coach Agent Readiness Test")
    print("="*60)
    print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests in order
    tests = [
        ("LangChain OpenAI Import", test_langchain_openai_import),
        ("Agent Core Imports", test_agent_core_imports),
        ("Clarify Workflow Init", test_clarify_workflow_init),
        ("Review Workflow Init", test_review_workflow_init),
        ("Todoist Tools", test_todoist_tools),
        ("Clarify Mock Execution", test_clarify_mock_execution),
        ("Migration Adapter", test_migration_adapter),
        ("OpenAI API Key", test_openai_api_key),
    ]
    
    for name, func in tests:
        test_step(name, func)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    passed = test_results["summary"]["passed"]
    failed = test_results["summary"]["failed"]
    total = passed + failed
    
    print(f"Total: {total} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    # Save results
    results_file = Path("test_agent_results.json")
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")
    
    # Recommendations
    print("\n" + "="*60)
    print("💡 Recommendations")
    print("="*60)
    
    if failed == 0:
        print("✅ All tests passed! Agent implementations appear ready.")
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY if not already set")
        print("2. Run: python -m gtd_coach clarify --dry-run")
        print("3. Monitor for any runtime issues")
    else:
        print("⚠️ Some tests failed. Issues to address:")
        for test in test_results["tests"]:
            if test["status"] == "failed":
                print(f"  - {test['name']}: {test.get('error', 'Unknown error')}")
        print("\nFix these issues before proceeding with agent rollout.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)