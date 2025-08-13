#!/usr/bin/env python3
"""
Tests for AgentState schema and validation
"""

import pytest
from datetime import datetime
from gtd_coach.agent.state import AgentState, StateValidator, DailyCapture


class TestAgentState:
    """Test AgentState schema and fields"""
    
    def test_agent_state_initialization(self):
        """Test basic AgentState initialization"""
        state = {
            'messages': [],
            'session_id': 'test_123',
            'workflow_type': 'daily_capture'
        }
        
        # Should accept valid state
        assert state['session_id'] == 'test_123'
        assert state['workflow_type'] == 'daily_capture'
    
    def test_state_validator_ensure_required_fields(self):
        """Test StateValidator.ensure_required_fields"""
        # Empty state should get defaults
        state = {}
        validated = StateValidator.ensure_required_fields(state)
        
        assert 'messages' in validated
        assert 'session_id' in validated
        assert 'workflow_type' in validated
        assert validated['workflow_type'] == 'ad_hoc'  # Default is ad_hoc, not daily_capture
        assert isinstance(validated['messages'], list)
        
        # Existing fields should be preserved
        state = {'session_id': 'existing_id'}
        validated = StateValidator.ensure_required_fields(state)
        assert validated['session_id'] == 'existing_id'
    
    def test_daily_capture_model(self):
        """Test DailyCapture model"""
        capture = DailyCapture(
            content="Review project proposal",
            capture_method="inbox_scan",
            source="outlook",
            adhd_flag=False
        )
        
        assert capture.content == "Review project proposal"
        assert capture.capture_method == "inbox_scan"
        assert capture.source == "outlook"
        assert capture.adhd_flag is False
        assert capture.id is not None  # Should auto-generate ID
        assert capture.created_at is not None
    
    def test_state_with_all_fields(self):
        """Test state with all optional fields populated"""
        state = StateValidator.ensure_required_fields({})
        
        # Add all optional fields
        state['user_id'] = 'user_123'
        state['user_context'] = {'name': 'Test User'}
        state['adhd_patterns'] = ['rapid_switching', 'overwhelm']
        state['accountability_mode'] = 'firm'
        state['captures'] = [
            {'content': 'Item 1', 'id': '1'},
            {'content': 'Item 2', 'id': '2'}
        ]
        state['processed_items'] = []
        state['projects'] = []
        state['focus_score'] = 75.5
        state['context_switches'] = [
            {'from': 'email', 'to': 'slack', 'duration': 30}
        ]
        state['current_phase'] = 'capture'
        state['completed_phases'] = ['startup', 'load_context']
        
        # All fields should be accessible
        assert state['user_id'] == 'user_123'
        assert state['accountability_mode'] == 'firm'
        assert len(state['adhd_patterns']) == 2
        assert state['focus_score'] == 75.5
    
    def test_state_validator_validate_transitions(self):
        """Test state transition validation"""
        state = StateValidator.ensure_required_fields({})
        state['current_phase'] = 'startup'
        
        # Valid transitions from startup
        assert StateValidator.validate_phase_transition(
            state, 'timing_review'
        ) is True
        assert StateValidator.validate_phase_transition(
            state, 'capture'
        ) is True
        
        # Invalid transition (skipping to wrapup)
        assert StateValidator.validate_phase_transition(
            state, 'wrapup'
        ) is False
    
    def test_state_consistency_validation(self):
        """Test state consistency validation"""
        # Valid state
        state = StateValidator.ensure_required_fields({})
        issues = StateValidator.validate_state_consistency(state)
        assert len(issues) == 0
        
        # Invalid workflow_type
        state['workflow_type'] = 'invalid_type'
        issues = StateValidator.validate_state_consistency(state)
        assert any('Invalid workflow_type' in issue for issue in issues)
        
        # Fix it back
        state['workflow_type'] = 'daily_capture'
        
        # Invalid accountability_mode
        state['accountability_mode'] = 'invalid_mode'
        issues = StateValidator.validate_state_consistency(state)
        assert any('Invalid accountability_mode' in issue for issue in issues)


class TestStateManipulation:
    """Test state manipulation and updates"""
    
    def test_add_message_to_state(self):
        """Test adding messages to state"""
        state = StateValidator.ensure_required_fields({})
        
        # Add human message
        state['messages'].append({
            'role': 'user',
            'content': 'Test message'
        })
        
        assert len(state['messages']) == 1
        assert state['messages'][0]['role'] == 'user'
    
    def test_update_phase_tracking(self):
        """Test phase tracking updates"""
        state = StateValidator.ensure_required_fields({})
        
        # Update phase
        state['current_phase'] = 'capture'
        state['completed_phases'].append('startup')
        state['completed_phases'].append('load_context')
        
        assert state['current_phase'] == 'capture'
        assert 'startup' in state['completed_phases']
        assert 'load_context' in state['completed_phases']
        assert len(state['completed_phases']) == 2
    
    def test_pattern_detection_updates(self):
        """Test ADHD pattern detection updates"""
        state = StateValidator.ensure_required_fields({})
        
        # Add patterns
        state['adhd_patterns'].append('rapid_switching')
        state['adhd_patterns'].append('overwhelm')
        
        # Update pattern analysis
        state['pattern_analysis'] = {
            'severity': 'high',
            'patterns': {
                'rapid_switching': {'count': 5, 'severity': 'high'},
                'overwhelm': {'count': 3, 'severity': 'medium'}
            }
        }
        
        assert len(state['adhd_patterns']) == 2
        assert state['pattern_analysis']['severity'] == 'high'
    
    def test_accountability_mode_changes(self):
        """Test accountability mode transitions"""
        state = StateValidator.ensure_required_fields({})
        
        # Should start as adaptive
        assert state['accountability_mode'] == 'adaptive'
        
        # Change to firm
        state['accountability_mode'] = 'firm'
        assert state['accountability_mode'] == 'firm'
        
        # Change to gentle
        state['accountability_mode'] = 'gentle'
        assert state['accountability_mode'] == 'gentle'
        
        # Track history
        if 'behavior_adjustments' not in state:
            state['behavior_adjustments'] = []
        
        state['behavior_adjustments'].append({
            'from': 'adaptive',
            'to': 'firm',
            'reason': 'High pattern severity',
            'timestamp': datetime.now().isoformat()
        })
        
        assert len(state['behavior_adjustments']) == 1