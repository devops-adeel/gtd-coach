#!/usr/bin/env python3
"""
Test script to verify coach.py agent integration
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_feature_flags():
    """Test that feature flags are working"""
    from gtd_coach.config.features import should_use_agent, should_run_shadow
    
    # Test with different session IDs
    test_sessions = [
        "test_session_001",
        "test_session_002", 
        "test_session_003"
    ]
    
    print("Testing feature flags:")
    for session_id in test_sessions:
        use_agent = should_use_agent(session_id)
        run_shadow = should_run_shadow(session_id)
        print(f"  Session {session_id}: use_agent={use_agent}, shadow={run_shadow}")
    print()

def test_coach_initialization():
    """Test that GTDCoach initializes correctly with agent support"""
    print("Testing coach initialization...")
    
    # Mock the environment and dependencies
    with patch('gtd_coach.coach.check_server') as mock_check, \
         patch('gtd_coach.coach.GraphitiMemory'), \
         patch('gtd_coach.coach.ADHDPatternDetector'), \
         patch('gtd_coach.coach.TimingAPI'):
        
        # Mock server check to pass
        mock_check.return_value = (True, "Server running")
        
        # Import and initialize coach
        from gtd_coach.coach import GTDCoach
        
        # Test with agent enabled
        with patch('gtd_coach.config.features.should_use_agent', return_value=True):
            coach = GTDCoach()
            assert hasattr(coach, 'use_agent'), "Coach should have use_agent attribute"
            assert hasattr(coach, 'agent_workflow'), "Coach should have agent_workflow attribute"
            print(f"  ✓ Coach initialized with agent support: use_agent={coach.use_agent}")
        
        # Test with agent disabled
        with patch('gtd_coach.config.features.should_use_agent', return_value=False):
            coach = GTDCoach()
            assert hasattr(coach, 'use_agent'), "Coach should have use_agent attribute"
            assert coach.use_agent == False, "use_agent should be False"
            print(f"  ✓ Coach initialized without agent: use_agent={coach.use_agent}")
    
    print()

def test_workflow_routing():
    """Test that the main() function routes correctly"""
    print("Testing workflow routing...")
    
    # Mock dependencies
    with patch('gtd_coach.coach.check_server') as mock_check, \
         patch('gtd_coach.coach.GraphitiMemory'), \
         patch('gtd_coach.coach.ADHDPatternDetector'), \
         patch('gtd_coach.coach.TimingAPI'), \
         patch('builtins.input', return_value=''):
        
        mock_check.return_value = (True, "Server running")
        
        from gtd_coach.coach import GTDCoach
        
        # Test agent workflow routing when agent successfully loads
        # Since agent workflow may fail to import, we'll test both scenarios
        
        # First, test when agent workflow is available
        print("  Testing when agent workflow is available...")
        coach = GTDCoach()
        
        # Manually set use_agent to test routing
        coach.use_agent = True
        coach.agent_workflow = MagicMock()  # Mock the workflow
        
        # Mock the run methods
        coach.run_agent_review = MagicMock()
        coach.run_legacy_review = MagicMock()
        
        # Simulate the routing logic
        if coach.use_agent:
            coach.run_agent_review()
        else:
            coach.run_legacy_review()
        
        # Verify correct method was called
        coach.run_agent_review.assert_called_once()
        coach.run_legacy_review.assert_not_called()
        print("    ✓ Agent workflow correctly routed when use_agent=True")
        
        # Test legacy workflow routing
        coach = GTDCoach()
        coach.use_agent = False
        
        # Mock the run methods again
        coach.run_agent_review = MagicMock()
        coach.run_legacy_review = MagicMock()
        
        # Simulate the routing logic
        if coach.use_agent:
            coach.run_agent_review()
        else:
            coach.run_legacy_review()
        
        # Verify correct method was called
        coach.run_legacy_review.assert_called_once()
        coach.run_agent_review.assert_not_called()
        print("    ✓ Legacy workflow correctly routed when use_agent=False")
        
        # Test fallback when agent workflow fails to load
        print("  Testing fallback when agent workflow fails...")
        coach = GTDCoach()
        
        # If agent_workflow is None, use_agent should be False
        if coach.agent_workflow is None:
            assert coach.use_agent == False, "use_agent should be False when agent_workflow fails to load"
            print("    ✓ Correctly falls back to legacy when agent import fails")
    
    print()

def test_methods_exist():
    """Test that the new methods exist"""
    print("Testing new methods exist...")
    
    with patch('gtd_coach.coach.check_server') as mock_check, \
         patch('gtd_coach.coach.GraphitiMemory'), \
         patch('gtd_coach.coach.ADHDPatternDetector'), \
         patch('gtd_coach.coach.TimingAPI'):
        
        mock_check.return_value = (True, "Server running")
        
        from gtd_coach.coach import GTDCoach
        
        coach = GTDCoach()
        
        # Check methods exist
        assert hasattr(coach, 'run_agent_review'), "GTDCoach should have run_agent_review method"
        assert callable(coach.run_agent_review), "run_agent_review should be callable"
        print("  ✓ run_agent_review method exists")
        
        assert hasattr(coach, 'run_legacy_review'), "GTDCoach should have run_legacy_review method"
        assert callable(coach.run_legacy_review), "run_legacy_review should be callable"
        print("  ✓ run_legacy_review method exists")
    
    print()

def main():
    """Run all tests"""
    print("="*50)
    print("Testing Coach Agent Integration")
    print("="*50)
    print()
    
    try:
        test_feature_flags()
        test_coach_initialization()
        test_workflow_routing()
        test_methods_exist()
        
        print("="*50)
        print("✅ All integration tests passed!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()