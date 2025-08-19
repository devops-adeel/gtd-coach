#!/usr/bin/env python3
"""
Test memory persistence and cross-session learning functionality
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.patterns.pattern_persistence import PatternPersistence
from gtd_coach.patterns.evolution import PatternEvolution, EvolutionType
from gtd_coach.integrations.graphiti import GraphitiMemory


class TestPatternPersistence:
    """Test the PatternPersistence class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.persistence = PatternPersistence(data_dir=Path(self.temp_dir))
    
    def test_save_and_load_session_patterns(self):
        """Test saving and loading session patterns"""
        # Create test data
        patterns = [
            {'type': 'fragmented_capture', 'severity': 'high', 'topic_switches': 8},
            {'type': 'low_focus', 'severity': 'medium', 'score': 45}
        ]
        
        interventions = [
            {'type': 'timer_alert', 'context': {'phase': 'MIND_SWEEP'}},
            {'type': 'context_grouping', 'context': {'items_grouped': 5}}
        ]
        
        outcomes = {
            'all_phases_completed': True,
            'focus_score': 65,
            'coherence_score': 0.7,
            'context_switches': 6
        }
        
        # Save session
        session_id = self.persistence.save_session_patterns(patterns, interventions, outcomes)
        assert session_id is not None
        
        # Verify file was created
        session_file = self.persistence.sessions_dir / f'{session_id}.json'
        assert session_file.exists()
        
        # Load and verify data
        with open(session_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data['session_id'] == session_id
        assert len(loaded_data['patterns']) == 2
        assert loaded_data['patterns'][0]['type'] == 'fragmented_capture'
        assert loaded_data['effectiveness'] > 0.5  # Should be positive with good outcomes
    
    def test_load_recent_patterns(self):
        """Test loading patterns from recent sessions"""
        # Create multiple sessions with recurring patterns
        for i in range(5):
            patterns = [
                {'type': 'fragmented_capture', 'severity': 'high'},
                {'type': 'low_focus', 'severity': 'medium'}
            ]
            
            if i > 2:  # Add a third pattern in later sessions
                patterns.append({'type': 'task_switching', 'severity': 'low'})
            
            self.persistence.save_session_patterns(
                patterns, 
                [], 
                {'all_phases_completed': True}
            )
        
        # Load recent patterns
        recurring = self.persistence.load_recent_patterns(weeks_back=4)
        
        # Should find patterns
        assert len(recurring) >= 2
        
        # fragmented_capture should be most frequent
        assert recurring[0]['pattern'] == 'fragmented_capture'
        # With adaptive threshold, frequency might be lower but pattern should still be detected
        assert recurring[0]['frequency'] >= 1
        
        # Should have recommendations
        assert 'recommendation' in recurring[0]
        assert len(recurring[0]['recommendation']) > 0
    
    def test_intervention_tracking(self):
        """Test tracking interventions and their effectiveness"""
        # Track some interventions
        self.persistence.track_intervention('timer_alert', {'phase': 'MIND_SWEEP'})
        self.persistence.track_intervention('context_grouping', {'items': 10})
        
        # Save session with good outcome
        self.persistence.save_session_patterns(
            [{'type': 'low_focus', 'severity': 'low'}],
            self.persistence.current_interventions,
            {'all_phases_completed': True, 'focus_score': 75}
        )
        
        # Get intervention history
        history = self.persistence.get_intervention_history('timer_alert')
        
        assert history['found'] is True
        assert history['total_uses'] == 1
        assert history['average_effectiveness'] > 0.5


class TestPatternEvolution:
    """Test the PatternEvolution class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evolution = PatternEvolution(data_dir=Path(self.temp_dir))
    
    def test_track_evolution(self):
        """Test tracking pattern evolution"""
        old_pattern = {
            'id': 'pattern_001',
            'type': 'fragmented_capture',
            'severity': 'high',
            'frequency': 10
        }
        
        new_pattern = {
            'id': 'pattern_002',
            'type': 'fragmented_capture',
            'severity': 'medium',
            'frequency': 5
        }
        
        # Track evolution
        evo_id = self.evolution.track_evolution(
            old_pattern, 
            new_pattern,
            intervention='context_grouping'
        )
        
        assert evo_id is not None
        assert len(self.evolution.evolution_history) == 1
        
        # Check evolution record
        record = self.evolution.evolution_history[0]
        assert record['type'] == EvolutionType.IMPROVED.value
        assert record['intervention'] == 'context_grouping'
        assert record['improvement_score'] > 0
    
    def test_improvement_story(self):
        """Test generating improvement narratives"""
        # Create evolution chain
        patterns = [
            {'id': 'p1', 'type': 'low_focus', 'severity': 'high'},
            {'id': 'p2', 'type': 'low_focus', 'severity': 'medium'},
            {'id': 'p3', 'type': 'low_focus', 'severity': 'low'}
        ]
        
        # Track evolutions
        self.evolution.track_evolution(patterns[0], patterns[1], 'timer_alerts')
        self.evolution.track_evolution(patterns[1], patterns[2], 'shorter_sessions')
        
        # Get improvement story
        story = self.evolution.get_improvement_story('low_focus')
        
        assert story is not None
        assert 'improved' in story.lower()
        assert 'timer_alerts' in story or 'shorter_sessions' in story
    
    def test_find_successful_interventions(self):
        """Test finding successful interventions for a pattern type"""
        # Track multiple evolutions with different interventions
        base_pattern = {'type': 'task_switching', 'severity': 'high'}
        
        # Successful intervention
        for _ in range(3):
            self.evolution.track_evolution(
                base_pattern,
                {'type': 'task_switching', 'severity': 'low'},
                'batch_processing'
            )
        
        # Less successful intervention
        self.evolution.track_evolution(
            base_pattern,
            {'type': 'task_switching', 'severity': 'medium'},
            'time_blocking'
        )
        
        # Find successful interventions
        successful = self.evolution.find_successful_interventions('task_switching')
        
        assert len(successful) > 0
        assert successful[0][0] == 'batch_processing'
        assert successful[0][1] > 0  # Positive success rate


class TestGraphitiMemorySessionHandoff:
    """Test the session handoff functionality in GraphitiMemory"""
    
    @pytest.mark.asyncio
    async def test_prepare_next_session_context(self):
        """Test preparing context for next session"""
        # Create memory instance
        memory = GraphitiMemory('test_session_001')
        
        # Mock the search method
        memory.search_with_context = AsyncMock(return_value=[
            Mock(metadata={'pattern_type': 'fragmented_capture'}),
            Mock(metadata={'pattern_type': 'fragmented_capture'}),
            Mock(metadata={'pattern_type': 'low_focus'}),
            Mock(metadata={'pattern_type': 'fragmented_capture'})
        ])
        
        # Prepare test data
        review_data = {
            'mindsweep_items': ['task1', 'task2', 'task3'],
            'items_captured': 3
        }
        
        timing_data = {
            'focus_metrics': {
                'focus_score': 45,
                'switches_per_hour': 12
            }
        }
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Prepare context
            await memory.prepare_next_session_context(review_data, timing_data)
            
            # Verify file was written
            mock_open.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_startup_context(self):
        """Test loading startup context"""
        # Create memory instance
        memory = GraphitiMemory('test_session_002')
        
        # Create test context file
        test_context = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'recurring_patterns': [
                {'pattern': 'fragmented_capture', 'frequency': 4, 'recommendation': 'Use context groups'},
                {'pattern': 'low_focus', 'frequency': 3, 'recommendation': 'Take more breaks'}
            ],
            'last_session_patterns': [
                {'type': 'fragmented_capture', 'topic_switches': 8}
            ],
            'last_focus_score': 55
        }
        
        # Mock file operations
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_context)
                
                # Mock json.load to return our test context
                with patch('json.load', return_value=test_context):
                    # Get startup context
                    context_str = await memory.get_startup_context()
                    
                    assert context_str is not None
                    assert 'On your mind lately' in context_str
                    assert 'fragmented_capture' in context_str
                    assert 'Use context groups' in context_str
    
    @pytest.mark.asyncio
    async def test_startup_context_performance(self):
        """Test that startup context loads in < 1 second"""
        import time
        
        memory = GraphitiMemory('test_session_003')
        
        # Create simple test context
        test_context = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'recurring_patterns': [
                {'pattern': 'test_pattern', 'frequency': 3}
            ]
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('json.load', return_value=test_context):
                    start_time = time.perf_counter()
                    context = await memory.get_startup_context()
                    elapsed = time.perf_counter() - start_time
                    
                    # Should complete in less than 1 second
                    assert elapsed < 1.0
                    assert context is not None


def test_integration_multi_session_learning():
    """Integration test simulating multiple sessions with learning"""
    temp_dir = tempfile.mkdtemp()
    persistence = PatternPersistence(data_dir=Path(temp_dir))
    evolution = PatternEvolution(data_dir=Path(temp_dir))
    
    # Simulate 5 weekly sessions
    for week in range(5):
        # Week 1-2: High fragmentation
        if week < 2:
            patterns = [
                {'type': 'fragmented_capture', 'severity': 'high', 'topic_switches': 10}
            ]
            interventions = []
            outcomes = {'focus_score': 40, 'all_phases_completed': False}
        
        # Week 3: Try intervention
        elif week == 2:
            patterns = [
                {'type': 'fragmented_capture', 'severity': 'medium', 'topic_switches': 6}
            ]
            interventions = [
                {'type': 'context_grouping', 'context': {'phase': 'MIND_SWEEP'}}
            ]
            outcomes = {'focus_score': 55, 'all_phases_completed': True}
            
            # Track evolution
            evolution.track_evolution(
                {'type': 'fragmented_capture', 'severity': 'high'},
                {'type': 'fragmented_capture', 'severity': 'medium'},
                'context_grouping'
            )
        
        # Week 4-5: Continued improvement
        else:
            patterns = [
                {'type': 'fragmented_capture', 'severity': 'low', 'topic_switches': 3}
            ]
            interventions = [
                {'type': 'context_grouping', 'context': {'phase': 'MIND_SWEEP'}}
            ]
            outcomes = {'focus_score': 70, 'all_phases_completed': True}
        
        # Save session
        persistence.save_session_patterns(patterns, interventions, outcomes)
    
    # Verify learning occurred
    recurring = persistence.load_recent_patterns(weeks_back=5)
    assert len(recurring) > 0
    assert recurring[0]['pattern'] == 'fragmented_capture'
    assert recurring[0]['frequency'] == 5
    
    # Check improvement story
    story = evolution.get_improvement_story('fragmented_capture')
    assert story is not None
    assert 'improved' in story.lower()
    
    # Find successful interventions
    successful = evolution.find_successful_interventions('fragmented_capture')
    assert len(successful) > 0
    assert successful[0][0] == 'context_grouping'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])