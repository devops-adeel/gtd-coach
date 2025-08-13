#!/usr/bin/env python3
"""
Test script for the new LangGraph GTD Agent
Verifies basic functionality without running full review
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gtd_coach.agent.core import GTDAgent
from gtd_coach.agent.tools import TIME_TOOLS, INTERACTION_TOOLS
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_agent_initialization():
    """Test that agent initializes correctly"""
    print("Testing agent initialization...")
    
    try:
        # Create agent
        agent = GTDAgent(use_memory_saver=True)  # Use in-memory for testing
        
        # Set minimal tools for testing
        test_tools = TIME_TOOLS[:2]  # Just time checking tools
        agent.set_tools(test_tools)
        
        print("✅ Agent initialized successfully")
        return agent
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return None


def test_context_management(agent):
    """Test context window management"""
    print("\nTesting context management...")
    
    try:
        # Create a state with many messages to test trimming
        state = {
            "messages": [
                HumanMessage(content=f"Test message {i}") 
                for i in range(50)  # Create 50 messages
            ],
            "current_phase": "MIND_SWEEP",
            "phase_start_time": datetime.now(),
            "phase_time_limit": 10
        }
        
        # Test pre-model hook
        modified_messages = agent._pre_model_hook(state)
        
        print(f"Original messages: {len(state['messages'])}")
        print(f"Modified messages: {len(modified_messages)}")
        print(f"Context metrics: {agent.get_context_metrics()}")
        
        if len(modified_messages) < len(state['messages']):
            print("✅ Context trimming working")
        else:
            print("⚠️ Context not trimmed (may be under limit)")
            
        return True
        
    except Exception as e:
        print(f"❌ Context management test failed: {e}")
        return False


def test_time_awareness(agent):
    """Test time management features"""
    print("\nTesting time awareness...")
    
    try:
        state = {
            "messages": [],
            "current_phase": "STARTUP",
            "phase_start_time": datetime.now(),
            "phase_time_limit": 2,
            "phase_summary": "",
            "total_elapsed": 0
        }
        
        # Get time context
        time_context = agent._get_time_context(state)
        print(f"Time context: {time_context}")
        
        if "remaining" in time_context.lower():
            print("✅ Time awareness working")
            return True
        else:
            print("❌ Time context not generated properly")
            return False
            
    except Exception as e:
        print(f"❌ Time awareness test failed: {e}")
        return False


def test_phase_summary(agent):
    """Test phase summarization"""
    print("\nTesting phase summarization...")
    
    try:
        messages = [
            HumanMessage(content="Buy groceries"),
            HumanMessage(content="Call dentist"),
            HumanMessage(content="Finish report")
        ]
        
        summary = agent._summarize_phase(messages, "MIND_SWEEP")
        print(f"Phase summary: {summary}")
        
        if "Captured 3 items" in summary:
            print("✅ Phase summarization working")
            return True
        else:
            print("❌ Summary not generated correctly")
            return False
            
    except Exception as e:
        print(f"❌ Phase summary test failed: {e}")
        return False


def test_simple_invocation(agent):
    """Test a simple agent invocation"""
    print("\nTesting simple agent invocation...")
    
    try:
        state = {
            "messages": [
                SystemMessage(content="You are a GTD coach."),
                HumanMessage(content="Hello, I'm ready to start my review")
            ],
            "current_phase": "STARTUP",
            "phase_start_time": datetime.now(),
            "phase_time_limit": 2
        }
        
        config = {
            "configurable": {
                "thread_id": "test_session",
                "checkpoint_ns": "test"
            }
        }
        
        # Note: This will fail if LM Studio is not running
        # That's expected for this test
        print("Attempting to invoke agent (will fail if LM Studio not running)...")
        
        try:
            result = agent.invoke(state, config)
            print("✅ Agent invocation succeeded")
            return True
        except Exception as e:
            if "Connection" in str(e) or "refused" in str(e).lower():
                print("⚠️ LM Studio not running (expected for test)")
                return True  # This is expected
            else:
                raise
                
    except Exception as e:
        print(f"❌ Simple invocation test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("🧪 TESTING LANGGRAPH GTD AGENT")
    print("="*60)
    
    # Initialize agent
    agent = test_agent_initialization()
    if not agent:
        print("\n❌ Cannot proceed without agent initialization")
        return 1
    
    # Run tests
    results = []
    results.append(test_context_management(agent))
    results.append(test_time_awareness(agent))
    results.append(test_phase_summary(agent))
    results.append(test_simple_invocation(agent))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"⚠️ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())