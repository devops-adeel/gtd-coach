#!/usr/bin/env python3
"""
Simple test runner for GTD Agent that doesn't require pytest
Can be run directly with Python to verify the implementation
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test agent imports
        from gtd_coach.agent import GTDAgent, create_daily_capture_agent
        print("  ✓ Agent module imports")
        
        # Test state imports
        from gtd_coach.agent.state import AgentState, StateValidator, DailyCapture
        print("  ✓ State module imports")
        
        # Test tool imports
        from gtd_coach.agent.tools import (
            get_daily_capture_tools,
            get_weekly_review_tools,
            get_all_tools
        )
        print("  ✓ Tools module imports")
        
        # Test workflow imports
        from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
        print("  ✓ Workflow module imports")
        
        # Test command imports
        from gtd_coach.commands import cli, daily_capture, resume
        print("  ✓ Commands module imports")
        
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_state_validation():
    """Test state validation"""
    print("\nTesting state validation...")
    
    try:
        from gtd_coach.agent.state import StateValidator
        
        # Test empty state gets defaults
        state = {}
        validated = StateValidator.ensure_required_fields(state)
        
        assert 'messages' in validated, "messages field missing"
        assert 'session_id' in validated, "session_id field missing"
        assert 'workflow_type' in validated, "workflow_type field missing"
        print("  ✓ State validation works")
        
        return True
    except Exception as e:
        print(f"  ✗ State validation failed: {e}")
        return False


def test_agent_initialization():
    """Test agent can be initialized"""
    print("\nTesting agent initialization...")
    
    try:
        from gtd_coach.agent import GTDAgent
        
        # Initialize in test mode
        agent = GTDAgent(test_mode=True)
        
        assert agent.mode == 'hybrid', f"Expected hybrid mode, got {agent.mode}"
        assert agent.workflow_type == 'daily_capture', f"Expected daily_capture, got {agent.workflow_type}"
        assert agent.test_mode is True, "Test mode not set"
        
        # Check tools loaded
        tools = agent.get_available_tools()
        assert len(tools) > 0, "No tools loaded"
        
        print(f"  ✓ Agent initialized with {len(tools)} tools")
        
        return True
    except Exception as e:
        print(f"  ✗ Agent initialization failed: {e}")
        return False


def test_tool_registry():
    """Test tool registry"""
    print("\nTesting tool registry...")
    
    try:
        from gtd_coach.agent.tools import tool_registry
        
        # Check tools are registered
        all_tools = tool_registry.get_all_tools()
        assert len(all_tools) > 0, "No tools in registry"
        
        # Check categories
        capture_tools = tool_registry.get_tools_by_category('capture')
        assert len(capture_tools) > 0, "No capture tools found"
        
        # Check specific tool
        tool_info = tool_registry.get_tool_info('scan_inbox_tool')
        assert tool_info['category'] == 'capture', "Wrong category for scan_inbox_tool"
        assert tool_info['version'] == '1.0', "Wrong version"
        
        print(f"  ✓ Tool registry has {len(all_tools)} tools")
        
        return True
    except Exception as e:
        print(f"  ✗ Tool registry failed: {e}")
        return False


def test_workflow_creation():
    """Test workflow can be created"""
    print("\nTesting workflow creation...")
    
    try:
        from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
        
        # Create workflow
        workflow = DailyCaptureWorkflow(llm_client=None, use_agent_decisions=False)
        
        assert workflow.graph is not None, "Graph not created"
        assert len(workflow.tools) > 0, "No tools in workflow"
        
        print(f"  ✓ Workflow created with {len(workflow.tools)} tools")
        
        return True
    except Exception as e:
        print(f"  ✗ Workflow creation failed: {e}")
        return False


def test_cli_commands():
    """Test CLI commands are available"""
    print("\nTesting CLI commands...")
    
    try:
        from gtd_coach.commands.cli import cli
        
        # Check commands are registered
        commands = cli.commands
        expected = ['daily', 'resume', 'weekly', 'config', 'test', 'status', 'toggle', 'version']
        
        for cmd in expected:
            if cmd not in commands:
                print(f"  ✗ Missing command: {cmd}")
                return False
        
        print(f"  ✓ All {len(expected)} CLI commands available")
        
        return True
    except Exception as e:
        print(f"  ✗ CLI commands failed: {e}")
        return False


def test_factory_functions():
    """Test agent factory functions"""
    print("\nTesting factory functions...")
    
    try:
        from gtd_coach.agent import (
            create_daily_capture_agent,
            create_ad_hoc_agent
        )
        
        # Test daily capture factory
        agent = create_daily_capture_agent(test_mode=True)
        assert agent.workflow_type == 'daily_capture', "Wrong workflow type"
        print("  ✓ Daily capture agent factory works")
        
        # Test ad-hoc factory
        agent = create_ad_hoc_agent(test_mode=True)
        assert agent.workflow_type == 'ad_hoc', "Wrong workflow type"
        print("  ✓ Ad-hoc agent factory works")
        
        return True
    except Exception as e:
        print(f"  ✗ Factory functions failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("GTD Agent Simple Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_state_validation,
        test_agent_initialization,
        test_tool_registry,
        test_workflow_creation,
        test_cli_commands,
        test_factory_functions
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Passed: {sum(results)}/{len(tests)}")
    print(f"  Failed: {len(tests) - sum(results)}/{len(tests)}")
    
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())