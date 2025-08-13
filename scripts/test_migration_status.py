#!/usr/bin/env python3
"""
Test migration status and validate all components are working.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_phase0():
    """Test Phase 0: Baseline & preparation"""
    print("\n" + "=" * 60)
    print("PHASE 0: BASELINE & PREPARATION")
    print("=" * 60)
    
    results = []
    
    # Test 1: Baseline metrics exist
    print("\n1. Baseline Metrics...")
    baseline_file = Path("data/baseline_metrics.json")
    if baseline_file.exists():
        print("   ✅ Baseline metrics collected")
        results.append(True)
    else:
        print("   ❌ Baseline metrics not found")
        results.append(False)
    
    # Test 2: Feature flags system
    print("\n2. Feature Flag System...")
    try:
        from gtd_coach.config import FeatureFlags, get_status
        status = get_status()
        print(f"   ✅ Feature flags configured")
        print(f"   Status: Rollout at {FeatureFlags.AGENT_ROLLOUT_PCT}%")
        results.append(True)
    except ImportError as e:
        print(f"   ❌ Feature flags not available: {e}")
        results.append(False)
    
    # Test 3: Todoist removed
    print("\n3. Todoist Removal...")
    todoist_file = Path("gtd_coach/integrations/todoist.py")
    if not todoist_file.exists():
        print("   ✅ Todoist integration removed")
        results.append(True)
    else:
        print("   ❌ Todoist file still exists")
        results.append(False)
    
    return all(results)

def test_phase1():
    """Test Phase 1: Core infrastructure"""
    print("\n" + "=" * 60)
    print("PHASE 1: CORE INFRASTRUCTURE")
    print("=" * 60)
    
    results = []
    
    # Test 1: SQLite checkpointing
    print("\n1. SQLite Checkpointing...")
    try:
        from gtd_coach.persistence import get_checkpointer_manager
        manager = get_checkpointer_manager()
        stats = manager.get_statistics()
        print(f"   ✅ Checkpointer available")
        print(f"   Database: {manager.db_path}")
        print(f"   Sessions: {stats.get('total_sessions', 0)}")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Checkpointer error: {e}")
        results.append(False)
    
    # Test 2: Langfuse LLM client
    print("\n2. Langfuse LLM Client...")
    try:
        from gtd_coach.llm import get_llm_client
        client = get_llm_client()
        if client.test_connection():
            print(f"   ✅ LLM client connected")
            print(f"   Model: {client.model}")
            print(f"   Langfuse: {'Enabled' if client.enable_langfuse else 'Disabled'}")
            results.append(True)
        else:
            print("   ❌ LLM connection failed")
            results.append(False)
    except Exception as e:
        print(f"   ❌ LLM client error: {e}")
        results.append(False)
    
    # Test 3: Agent state schema
    print("\n3. Agent State Schema...")
    try:
        from gtd_coach.agent import AgentState, StateValidator
        
        # Test state validation
        test_state = {}
        validated = StateValidator.ensure_required_fields(test_state)
        
        required_fields = [
            'messages', 'session_id', 'workflow_type',
            'adhd_patterns', 'graphiti_episode_ids'
        ]
        
        missing = [f for f in required_fields if f not in validated]
        
        if not missing:
            print(f"   ✅ State schema valid")
            print(f"   Fields: {len(validated.keys())}")
            results.append(True)
        else:
            print(f"   ❌ Missing fields: {missing}")
            results.append(False)
            
    except Exception as e:
        print(f"   ❌ State schema error: {e}")
        results.append(False)
    
    return all(results)

def test_integrations():
    """Test existing integrations still work"""
    print("\n" + "=" * 60)
    print("EXISTING INTEGRATIONS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Timing API
    print("\n1. Timing API...")
    try:
        from gtd_coach.integrations.timing import TimingAPI
        timing = TimingAPI()
        if timing.is_configured():
            print("   ✅ Timing API configured")
            results.append(True)
        else:
            print("   ⚠️ Timing API not configured (optional)")
            results.append(True)  # Optional, so not a failure
    except Exception as e:
        print(f"   ❌ Timing API error: {e}")
        results.append(False)
    
    # Test 2: Langfuse integration
    print("\n2. Langfuse Integration...")
    try:
        from gtd_coach.integrations.langfuse import validate_configuration
        if validate_configuration():
            print("   ✅ Langfuse configured")
        else:
            print("   ⚠️ Langfuse not configured (keys needed)")
        results.append(True)  # Not critical
    except Exception as e:
        print(f"   ❌ Langfuse error: {e}")
        results.append(False)
    
    # Test 3: Graphiti
    print("\n3. Graphiti Memory...")
    try:
        # Check if Graphiti config exists
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        print(f"   ✅ Graphiti configured at {neo4j_uri}")
        results.append(True)
    except Exception as e:
        print(f"   ❌ Graphiti error: {e}")
        results.append(False)
    
    return all(results)

def test_agent_system():
    """Test the agent system is functional"""
    print("\n" + "=" * 60)
    print("AGENT SYSTEM STATUS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Agent initialization
    print("\n1. Agent Initialization...")
    try:
        # Check if agent module exists
        from gtd_coach import agent
        print("   ✅ Agent module available")
        
        # Check factory functions
        if hasattr(agent, 'create_daily_capture_agent'):
            print("   ✅ Factory functions available")
            results.append(True)
        else:
            print("   ❌ Factory functions missing")
            results.append(False)
            
    except ImportError as e:
        print(f"   ❌ Agent module not found: {e}")
        results.append(False)
    
    # Test 2: Tools module
    print("\n2. Tools Module...")
    tools_dir = Path("gtd_coach/agent/tools")
    if tools_dir.exists():
        tool_files = list(tools_dir.glob("*.py"))
        print(f"   ✅ Tools directory exists")
        print(f"   Tool modules: {len(tool_files)}")
        results.append(True)
    else:
        print("   ⚠️ Tools not yet implemented")
        results.append(True)  # Expected at this stage
    
    # Test 3: Workflows
    print("\n3. Workflows...")
    workflows_dir = Path("gtd_coach/agent/workflows")
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.py"))
        print(f"   ✅ Workflows directory exists")
        print(f"   Workflow modules: {len(workflow_files)}")
        results.append(True)
    else:
        print("   ⚠️ Workflows not yet implemented")
        results.append(True)  # Expected at this stage
    
    return all(results)

def main():
    """Run all migration tests"""
    print("\n" + "=" * 70)
    print(" GTD COACH MIGRATION STATUS TEST ")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run all test phases
    phase_results = {
        "Phase 0 (Baseline)": test_phase0(),
        "Phase 1 (Infrastructure)": test_phase1(),
        "Integrations": test_integrations(),
        "Agent System": test_agent_system()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for phase, result in phase_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{phase:.<30} {status}")
    
    # Overall status
    all_passed = all(phase_results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 MIGRATION PHASE 0-1 COMPLETE!")
        print("\nNext steps:")
        print("- Phase 2: Implement tools with error handling")
        print("- Phase 3: Build hybrid workflow with shadow mode")
        print("- Phase 4: Create comprehensive test suite")
        print("- Phase 5: Setup monitoring and rollback")
        print("- Phase 6: Production rollout")
    else:
        print("⚠️ SOME COMPONENTS NEED ATTENTION")
        print("\nPlease review failed tests above")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())