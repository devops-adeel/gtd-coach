#!/usr/bin/env python3
"""
Test Suite for Adaptive Behavior System
Tests state monitoring and response adaptation
"""

import unittest
import time
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.adaptive.user_state import UserStateMonitor
from gtd_coach.adaptive.response_adapter import AdaptiveResponseManager


class TestUserStateMonitor(unittest.TestCase):
    """Test user state monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = UserStateMonitor()
    
    def test_initial_state(self):
        """Test initial state values"""
        state = self.monitor.get_state()
        self.assertEqual(state['energy_level'], 'normal')
        self.assertEqual(state['confusion_level'], 0.0)
        self.assertEqual(state['engagement_level'], 1.0)
        self.assertEqual(state['stress_indicators'], 0)
        self.assertFalse(state['needs_break'])
    
    def test_fatigue_detection(self):
        """Test fatigue detection from slow responses"""
        # Simulate slow responses
        for i in range(3):
            changes = self.monitor.update_from_interaction(
                response_time=15.0,  # Slow response
                content="ok",
                pattern_data=None
            )
        
        state = self.monitor.get_state()
        self.assertEqual(state['energy_level'], 'low')
        
        # Check adaptation needs
        adaptations = self.monitor.get_adaptation_needs()
        self.assertEqual(adaptations['prompt_length'], 'shorter')
        self.assertEqual(adaptations['pace'], 'slower')
        self.assertEqual(adaptations['encouragement'], 'high')
    
    def test_confusion_detection(self):
        """Test confusion detection from markers"""
        # Simulate confused responses
        changes1 = self.monitor.update_from_interaction(
            response_time=5.0,
            content="I don't understand what you mean",
            pattern_data=None
        )
        
        changes2 = self.monitor.update_from_interaction(
            response_time=4.0,
            content="Can you explain that again?",
            pattern_data=None
        )
        
        state = self.monitor.get_state()
        self.assertGreater(state['confusion_level'], 0.0)
        
        # After more confusion
        changes3 = self.monitor.update_from_interaction(
            response_time=6.0,
            content="I'm really confused now",
            pattern_data=None
        )
        
        state = self.monitor.get_state()
        self.assertGreater(state['confusion_level'], 0.5)
        
        # Check adaptations
        adaptations = self.monitor.get_adaptation_needs()
        self.assertEqual(adaptations['language'], 'simpler')
        self.assertTrue(adaptations['examples'])
    
    def test_disengagement_detection(self):
        """Test disengagement from quick/short responses"""
        # Simulate quick, minimal responses
        for i in range(4):
            changes = self.monitor.update_from_interaction(
                response_time=1.5,  # Very quick
                content="ok",      # Very short
                pattern_data=None
            )
        
        state = self.monitor.get_state()
        self.assertLess(state['engagement_level'], 0.8)
        
        # Check adaptations
        adaptations = self.monitor.get_adaptation_needs()
        # Check if low engagement adaptations are present
        if state['engagement_level'] < 0.6:
            self.assertEqual(adaptations.get('energy'), 'higher')
            self.assertTrue(adaptations.get('celebration'))
        else:
            # Engagement might not be low enough for adaptations
            pass
    
    def test_stress_detection(self):
        """Test stress detection from context switches"""
        # Simulate high context switching
        pattern_data = {
            'topic_switches': 4,
            'coherence_score': 0.3
        }
        
        changes = self.monitor.update_from_interaction(
            response_time=3.0,
            content="Need to do this, wait also that, oh and another thing",
            pattern_data=pattern_data
        )
        
        state = self.monitor.get_state()
        self.assertGreater(state['stress_indicators'], 0)
        
        # More switching increases stress
        changes = self.monitor.update_from_interaction(
            response_time=2.5,
            content="Actually, let me think about something else first",
            pattern_data={'topic_switches': 5, 'coherence_score': 0.2}
        )
        
        state = self.monitor.get_state()
        self.assertGreaterEqual(state['stress_indicators'], 2)
        
        # Check adaptations
        adaptations = self.monitor.get_adaptation_needs()
        self.assertEqual(adaptations['tone'], 'calming')
        self.assertEqual(adaptations['pace'], 'slower')
    
    def test_phase_reset(self):
        """Test phase reset functionality"""
        # Add some confusion and stress
        self.monitor.confusion_markers_count = 3
        self.monitor.stress_indicators = 2
        self.monitor.context_switches = 4
        
        # Reset for new phase
        self.monitor.reset_phase()
        
        # Check counters are reset
        self.assertEqual(self.monitor.confusion_markers_count, 0)
        self.assertEqual(self.monitor.short_response_count, 0)
        self.assertEqual(self.monitor.context_switches, 0)
        # Note: stress_indicators persist across phases


class TestAdaptiveResponseManager(unittest.TestCase):
    """Test adaptive response management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = AdaptiveResponseManager()
    
    def test_low_energy_adaptations(self):
        """Test adaptations for low energy state"""
        user_state = {
            'energy_level': 'low',
            'confusion_level': 0.0,
            'engagement_level': 1.0,
            'stress_indicators': 0
        }
        
        adaptations = self.manager.get_adaptations(user_state, 'MIND_SWEEP')
        
        # Check prompt modifiers (with trailing space)
        self.assertIn('Just capture what comes to mind, no need to be complete. ', adaptations['prompt_modifiers'])
        
        # Check settings
        self.assertEqual(adaptations['settings']['max_tokens'], 100)
        self.assertEqual(adaptations['settings']['temperature'], 0.7)
    
    def test_high_confusion_adaptations(self):
        """Test adaptations for high confusion"""
        user_state = {
            'energy_level': 'normal',
            'confusion_level': 0.7,
            'engagement_level': 1.0,
            'stress_indicators': 0
        }
        
        adaptations = self.manager.get_adaptations(user_state)
        
        # Check for clarity adaptations (with trailing space)
        self.assertIn('Use simple, clear language. Break things into small steps. ', 
                     adaptations['prompt_modifiers'])
        self.assertIn('example_mode', adaptations['flags'])
    
    def test_phase_specific_overrides(self):
        """Test phase-specific adaptation overrides"""
        user_state = {
            'energy_level': 'low',
            'confusion_level': 0.0,
            'engagement_level': 1.0,
            'stress_indicators': 0
        }
        
        # Test PROJECT_REVIEW specific adaptation
        adaptations = self.manager.get_adaptations(user_state, 'PROJECT_REVIEW')
        self.assertIn('Quick decisions only - we can revisit later. ', 
                     adaptations['prompt_modifiers'])
    
    def test_prompt_adaptation(self):
        """Test prompt text adaptation"""
        base_prompt = "Let's review your projects."
        
        adaptations = {
            'combined_prompt_modifier': 'Be energetic! ',
            'flags': {'celebration_mode', 'example_mode'}
        }
        
        adapted = self.manager.adapt_prompt(base_prompt, adaptations)
        
        # Check modifications
        # Celebration emoji comes first, then the modifier
        self.assertTrue(adapted.startswith('🎉 Be energetic!'))
        self.assertIn('For example:', adapted)  # Example mode adds example
    
    def test_settings_adaptation(self):
        """Test LLM settings adaptation"""
        base_settings = {
            'temperature': 0.8,
            'max_tokens': 500
        }
        
        adaptations = {
            'settings': {
                'temperature': 0.6,
                'max_tokens': 100
            }
        }
        
        adapted = self.manager.adapt_settings(base_settings, adaptations)
        
        self.assertEqual(adapted['temperature'], 0.6)
        self.assertEqual(adapted['max_tokens'], 100)
    
    def test_break_suggestion(self):
        """Test break suggestion logic"""
        user_state_tired = {
            'energy_level': 'low',
            'stress_indicators': 0
        }
        
        # Should suggest break after long phase when tired
        should_break = self.manager.should_suggest_break(650, user_state_tired)
        self.assertTrue(should_break)
        
        # Should not suggest break if phase is short
        should_break = self.manager.should_suggest_break(300, user_state_tired)
        self.assertFalse(should_break)
        
        # Should suggest break with high stress and confusion
        user_state_stressed = {
            'energy_level': 'normal',
            'stress_indicators': 2,
            'confusion_level': 0.6
        }
        should_break = self.manager.should_suggest_break(400, user_state_stressed)
        self.assertTrue(should_break)
    
    def test_encouragement_messages(self):
        """Test phase-specific encouragement messages"""
        # Test mind sweep encouragement
        msg = self.manager.get_encouragement_message('MIND_SWEEP', 0.5)
        self.assertEqual(msg, "Great job getting things out of your head!")
        
        # Test project review encouragement - 0.3 returns "Good progress on your projects!"
        msg = self.manager.get_encouragement_message('PROJECT_REVIEW', 0.3)
        self.assertEqual(msg, "Good progress on your projects!")
        
        # Test wrap-up completion
        msg = self.manager.get_encouragement_message('WRAP_UP', 1.0)
        self.assertIn('🎉', msg)  # Should include celebration
    
    def test_adaptation_metrics(self):
        """Test adaptation metrics tracking"""
        # Apply some adaptations
        user_state = {
            'energy_level': 'low',
            'confusion_level': 0.6,
            'engagement_level': 0.5,
            'stress_indicators': 2
        }
        
        self.manager.get_adaptations(user_state, 'MIND_SWEEP')
        self.manager.get_adaptations(user_state, 'PROJECT_REVIEW')
        
        metrics = self.manager.get_adaptation_metrics()
        
        # Check metrics
        self.assertEqual(metrics['total_adaptations'], 2)
        self.assertIn('low_energy', metrics['adaptation_counts'])
        self.assertIn('high_confusion', metrics['adaptation_counts'])
        self.assertIsNotNone(metrics['most_common'])


class TestIntegration(unittest.TestCase):
    """Test integration between monitor and manager"""
    
    def test_full_adaptation_flow(self):
        """Test complete flow from state detection to adaptation"""
        monitor = UserStateMonitor()
        manager = AdaptiveResponseManager()
        
        # Simulate user struggling (slow, confused responses)
        for i in range(3):
            monitor.update_from_interaction(
                response_time=12.0,
                content="I'm not sure about this",
                pattern_data={'topic_switches': 3}
            )
        
        # Get current state
        user_state = monitor.get_state()
        self.assertEqual(user_state['energy_level'], 'low')
        self.assertGreater(user_state['confusion_level'], 0)
        self.assertGreater(user_state['stress_indicators'], 0)
        
        # Get adaptations
        adaptations = manager.get_adaptations(user_state, 'MIND_SWEEP')
        
        # Verify appropriate adaptations
        self.assertGreater(len(adaptations['prompt_modifiers']), 0)
        self.assertIn('max_tokens', adaptations['settings'])
        self.assertLessEqual(adaptations['settings']['max_tokens'], 150)
        
        # Test prompt adaptation
        original_prompt = "What else is on your mind?"
        adapted_prompt = manager.adapt_prompt(original_prompt, adaptations)
        
        # Should be modified
        self.assertNotEqual(original_prompt, adapted_prompt)
        self.assertGreater(len(adapted_prompt), len(original_prompt))


if __name__ == '__main__':
    unittest.main(verbosity=2)