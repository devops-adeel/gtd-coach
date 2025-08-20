#!/usr/bin/env python3
"""
Test script to verify agent continues after phase transitions using interrupt pattern
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gtd_coach.agent.runner import GTDAgentRunner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_conversation_continuation():
    """Test that agent continues conversation after phase transition"""
    
    print("="*60)
    print("Testing GTD Agent with Interrupt Pattern")
    print("="*60)
    print("\nThis test will verify that the agent:")
    print("1. Transitions to STARTUP phase")
    print("2. Uses conversation tools to ask questions")
    print("3. Waits for user input via interrupt")
    print("4. Continues the conversation naturally")
    print("\n" + "="*60 + "\n")
    
    try:
        # Create runner
        runner = GTDAgentRunner()
        
        # Run the weekly review
        # The agent should now:
        # 1. Receive "Let's start the GTD weekly review"
        # 2. Call transition_phase_v2 to STARTUP
        # 3. See requires_user_input=True in the response
        # 4. Call check_in_with_user_v2 with energy level questions
        # 5. The conversation tool will interrupt and wait for input
        
        result = runner.run_weekly_review()
        
        print("\n" + "="*60)
        print("Test Complete")
        print("="*60)
        
        if result == 0:
            print("✅ Test PASSED - Agent completed successfully")
            print("\nCheck the following:")
            print("1. Agent transitioned to STARTUP phase")
            print("2. Agent asked questions using conversation tools")
            print("3. System paused for user input (interrupts)")
            print("4. Conversation continued after each input")
            
            print("\nIf Langfuse is configured, check traces at:")
            print("  http://localhost:3000 or your Langfuse instance")
            print(f"  Session ID: {runner.session_id}")
        else:
            print("❌ Test FAILED - Agent exited with error")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = test_conversation_continuation()
    sys.exit(exit_code)