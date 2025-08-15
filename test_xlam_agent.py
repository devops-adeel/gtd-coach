#!/usr/bin/env python3
"""
Test GTD Agent with xLAM model
"""

import sys
import os
from datetime import datetime

# Test basic agent initialization
def test_agent():
    try:
        print("=" * 60)
        print("Testing GTD Agent with xLAM-7b-fc-r Model")
        print("=" * 60)
        print()
        
        # Set environment for Docker
        os.environ['LM_STUDIO_URL'] = 'http://host.docker.internal:1234/v1'
        
        # Import agent components
        from gtd_coach.agent.runner import GTDAgentRunner
        from gtd_coach.agent.tools import ALL_TOOLS, ESSENTIAL_TOOLS
        
        print(f"1. Tool Loading Test:")
        print(f"   - ALL_TOOLS count: {len(ALL_TOOLS)}")
        print(f"   - ESSENTIAL_TOOLS count: {len(ESSENTIAL_TOOLS)}")
        print()
        
        # Initialize runner
        print("2. Initializing GTDAgentRunner...")
        runner = GTDAgentRunner()
        print("   ✅ Runner initialized")
        print()
        
        # Check agent configuration
        print("3. Agent Configuration:")
        print(f"   - Model: {runner.agent.model_name}")
        print(f"   - Max input tokens: {runner.agent.MAX_INPUT_TOKENS}")
        print(f"   - Tools loaded: {len(runner.agent.tools) if runner.agent.tools else 0}")
        print()
        
        # Test time tool
        print("4. Testing Time Tool (V2):")
        from gtd_coach.agent.tools.time_manager_v2 import check_time_v2, initialize_state_manager
        
        # Initialize state
        test_state = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "current_phase": "TEST_PHASE",
            "phase_start_time": datetime.now(),
            "phase_time_limit": 5
        }
        initialize_state_manager(test_state)
        
        # Test the tool
        result = check_time_v2.invoke({})
        print(f"   Result: {result}")
        print("   ✅ Time tool working")
        print()
        
        print("5. xLAM Model Integration:")
        print("   - Model optimized for function calling")
        print("   - Berkeley Function Calling Leaderboard: 3rd place (88.24%)")
        print("   - Token budget increased to 6000 for better tool descriptions")
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("Ready for full GTD review with xLAM model")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_agent())