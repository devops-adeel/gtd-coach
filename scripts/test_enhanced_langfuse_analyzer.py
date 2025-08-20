#!/usr/bin/env python3
"""
Test script to verify the enhanced Langfuse analyzer functions work correctly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.analyze_langfuse_traces import (
    analyze_phase_transition,
    extract_prompt_metadata,
    format_conversation_flow,
    validate_state_continuity
)

# Create mock observation object
class MockObservation:
    def __init__(self, name=None, obs_type=None, metadata=None, input_data=None, output_data=None, start_time=None):
        self.name = name
        self.type = obs_type
        self.metadata = metadata
        self.input = input_data
        self.output = output_data
        self.start_time = start_time
        self.id = "mock-obs-id"

def test_phase_transition_analysis():
    """Test phase transition detection"""
    print("Testing phase transition analysis...")
    
    observations = [
        MockObservation(
            metadata={'phase': 'MIND_SWEEP'},
            output_data={'tasks': ['Task 1', 'Task 2']}
        ),
        MockObservation(
            metadata={'phase': 'PROJECT_REVIEW'},
            output_data={'tasks': []}  # Tasks lost!
        )
    ]
    
    transitions = analyze_phase_transition("test-trace", observations)
    
    assert len(transitions) == 1
    assert transitions[0]['from_phase'] == 'MIND_SWEEP'
    assert transitions[0]['to_phase'] == 'PROJECT_REVIEW'
    assert 'tasks' in transitions[0]['state_lost']
    
    print("✅ Phase transition analysis working correctly")

def test_prompt_metadata_extraction():
    """Test prompt metadata extraction"""
    print("Testing prompt metadata extraction...")
    
    observations = [
        MockObservation(
            obs_type="GENERATION",
            metadata={'prompt_name': 'gtd-coach-firm', 'version': 'v3'},
            input_data={'messages': [{'role': 'system', 'content': 'You are a firm GTD coach'}]}
        ),
        MockObservation(
            obs_type="GENERATION",
            metadata={'prompt_name': 'gtd-coach-firm', 'version': 'v3'}
        )
    ]
    
    prompt_usage = extract_prompt_metadata(observations)
    
    assert 'gtd-coach-firm' in prompt_usage
    assert prompt_usage['gtd-coach-firm']['count'] == 2
    assert 'v3' in prompt_usage['gtd-coach-firm']['versions']
    
    print("✅ Prompt metadata extraction working correctly")

def test_conversation_flow_formatting():
    """Test conversation flow formatting"""
    print("Testing conversation flow formatting...")
    
    from datetime import datetime
    
    observations = [
        MockObservation(
            name="check_in_with_user",
            start_time=datetime.now(),
            input_data={'query': 'How are you doing?'}
        ),
        MockObservation(
            obs_type="GENERATION",
            start_time=datetime.now(),
            input_data={'messages': [
                {'role': 'user', 'content': 'I need to capture some tasks'},
                {'role': 'assistant', 'content': 'Let me help you with that'}
            ]},
            metadata={'phase': 'MIND_SWEEP', 'time_remaining': 10}
        )
    ]
    
    flow = format_conversation_flow(observations, show_metadata=True)
    
    assert '🔔 INTERRUPT' in flow
    assert '👤 User:' in flow
    assert '🤖 Agent:' in flow
    assert '📍 Phase: MIND_SWEEP' in flow
    assert '⏱️ Time remaining: 10 min' in flow
    
    print("✅ Conversation flow formatting working correctly")

def test_state_validation():
    """Test state continuity validation"""
    print("Testing state continuity validation...")
    
    observations = [
        MockObservation(
            output_data={'tasks': ['Task 1', 'Task 2'], 'projects': ['Project A']}
        ),
        MockObservation(
            output_data={'tasks': [], 'projects': ['Project A']}  # Tasks lost!
        ),
        MockObservation(
            name="memory_retrieval",
            metadata={'relevance_score': 0.3}  # Low relevance!
        )
    ]
    
    validation = validate_state_continuity(observations)
    
    assert len(validation['state_losses']) == 1
    assert validation['state_losses'][0]['lost_item'] == 'tasks'
    assert len(validation['warnings']) == 1
    assert validation['warnings'][0]['type'] == 'low_memory_relevance'
    
    print("✅ State validation working correctly")

if __name__ == "__main__":
    print("="*50)
    print("Testing Enhanced Langfuse Analyzer Functions")
    print("="*50)
    
    try:
        test_phase_transition_analysis()
        test_prompt_metadata_extraction()
        test_conversation_flow_formatting()
        test_state_validation()
        
        print("\n" + "="*50)
        print("✅ All tests passed successfully!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)