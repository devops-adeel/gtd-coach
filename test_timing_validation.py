#!/usr/bin/env python3
"""
Test Timing Validation Integration
Tests the enhanced ADHD pattern analyzer with Timing app validation
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest
from unittest.mock import Mock, patch, MagicMock

# Import the enhanced pattern analyzer
from gtd_coach.patterns.evaluation_patterns import ADHDPatternAnalyzer
from gtd_coach.analytics.evaluation_analytics import EvaluationAnalytics


class TestTimingValidation(unittest.TestCase):
    """Test Timing validation integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp())
        self.eval_dir = self.test_dir / "evaluations"
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test evaluation data with MIND_SWEEP inputs
        self.test_eval_data = {
            "session_id": "test_timing_session",
            "timestamp": datetime.now().isoformat(),
            "evaluations": [
                {
                    "phase": "MIND_SWEEP",
                    "user_input": "I worked on the budget report and had some client meetings. Also did email catchup.",
                    "coach_response": "Let's capture these items",
                    "coaching_quality": {
                        "score": 0.7,
                        "time_aware": True,
                        "structure": True,
                        "executive_support": True
                    }
                },
                {
                    "phase": "PROJECT_REVIEW",
                    "user_input": "Budget analysis project needs finishing",
                    "coaching_quality": {"score": 0.6}
                }
            ],
            "summary": {
                "average_scores": {
                    "task_extraction": 0.8,
                    "memory_relevance": 0.6,
                    "coaching_quality": 0.65
                }
            }
        }
        
        # Save test evaluation file
        eval_file = self.eval_dir / "eval_test_timing_session.json"
        with open(eval_file, 'w') as f:
            json.dump(self.test_eval_data, f)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_timing_enrichment_without_client(self):
        """Test that enrichment works gracefully without Timing client"""
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        
        # Disable Timing client
        analyzer.timing_client = None
        
        patterns = analyzer.analyze_session("test_timing_session")
        
        # Should have basic patterns but no timing validation
        self.assertIn('time_blindness', patterns)
        self.assertIn('task_switching', patterns)
        self.assertNotIn('timing_validation', patterns)
        
        print("✅ Graceful handling without Timing client")
    
    @patch('gtd_coach.patterns.evaluation_patterns.TimingAPI')
    def test_timing_enrichment_with_data(self, mock_timing_class):
        """Test enrichment with simulated Timing data"""
        # Create mock Timing client
        mock_timing = Mock()
        mock_timing.is_configured.return_value = True
        mock_timing.fetch_projects_last_week.return_value = [
            {'name': 'Budget Analysis', 'time_spent': 12.5},
            {'name': 'Client Meetings', 'time_spent': 8.0},
            {'name': 'Email Management', 'time_spent': 3.5},
            {'name': 'Slack Conversations', 'time_spent': 6.0},
            {'name': 'Code Review', 'time_spent': 4.0}
        ]
        mock_timing_class.return_value = mock_timing
        
        # Create analyzer with mocked Timing
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        
        patterns = analyzer.analyze_session("test_timing_session")
        
        # Should have timing validation
        self.assertIn('timing_validation', patterns)
        timing_data = patterns['timing_validation']
        
        self.assertTrue(timing_data['data_available'])
        self.assertEqual(timing_data['project_count'], 5)
        self.assertIn('discrepancy_pattern', timing_data)
        self.assertIn('invisible_work_ratio', timing_data)
        
        # Check discrepancy pattern
        # User mentioned budget, meetings, email (3/5 projects = 60%)
        # This could be either selective_awareness or high_awareness depending on fuzzy matching
        self.assertIn(timing_data['discrepancy_pattern'], ['selective_awareness', 'high_awareness'])
        
        print(f"✅ Timing enrichment working: {timing_data['discrepancy_pattern']}")
        print(f"   Invisible work ratio: {timing_data['invisible_work_ratio']}")
    
    @patch('gtd_coach.patterns.evaluation_patterns.TimingAPI')
    def test_time_blindness_detection(self, mock_timing_class):
        """Test detection of time blindness pattern"""
        # Create mock with many unreported projects
        mock_timing = Mock()
        mock_timing.is_configured.return_value = True
        mock_timing.fetch_projects_last_week.return_value = [
            {'name': 'Project Alpha', 'time_spent': 10.0},
            {'name': 'Project Beta', 'time_spent': 8.0},
            {'name': 'Project Gamma', 'time_spent': 6.0},
            {'name': 'Project Delta', 'time_spent': 5.0},
            {'name': 'Project Epsilon', 'time_spent': 4.0},
            {'name': 'Budget Work', 'time_spent': 2.0}  # Only this matches user input
        ]
        mock_timing_class.return_value = mock_timing
        
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        patterns = analyzer.analyze_session("test_timing_session")
        
        timing_data = patterns['timing_validation']
        
        # Should detect time blindness (low coverage)
        self.assertEqual(timing_data['discrepancy_pattern'], 'time_blindness')
        
        # Should also update the time blindness pattern
        self.assertTrue(patterns['time_blindness'].get('validated', False))
        self.assertEqual(patterns['time_blindness']['severity'], 'high')
        
        print(f"✅ Time blindness detection working")
    
    @patch('gtd_coach.patterns.evaluation_patterns.TimingAPI')
    def test_invisible_work_calculation(self, mock_timing_class):
        """Test invisible work ratio calculation"""
        mock_timing = Mock()
        mock_timing.is_configured.return_value = True
        mock_timing.fetch_projects_last_week.return_value = [
            {'name': 'Budget Report', 'time_spent': 10.0},  # Mentioned
            {'name': 'Admin Tasks', 'time_spent': 15.0},   # Not mentioned
            {'name': 'Email Triage', 'time_spent': 5.0}    # Partially mentioned
        ]
        mock_timing_class.return_value = mock_timing
        
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        patterns = analyzer.analyze_session("test_timing_session")
        
        timing_data = patterns['timing_validation']
        invisible_ratio = timing_data['invisible_work_ratio']
        
        # Should have significant invisible work (Admin Tasks = 15/30 = 50%)
        self.assertGreater(invisible_ratio, 0.4)
        self.assertLessEqual(invisible_ratio, 1.0)
        
        print(f"✅ Invisible work calculation: {invisible_ratio:.0%}")
    
    def test_insight_generation_with_timing(self):
        """Test that timing insights are generated correctly"""
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Create pattern data with timing validation
        pattern_data = {
            'timing_validation': {
                'data_available': True,
                'discrepancy_pattern': 'time_blindness',
                'invisible_work_ratio': 0.65,
                'project_count': 8,
                'mentioned_count': 3
            }
        }
        
        insights = analytics.generate_insights(pattern_data, {})
        
        # Should generate timing-specific insights
        timing_insights = [i for i in insights if 'Time Blindness Pattern' in i or 'Invisible Work' in i]
        
        self.assertGreater(len(timing_insights), 0)
        
        # Check for specific insight content
        insight_text = ' '.join(insights)
        self.assertIn('Time Blindness Pattern', insight_text)
        self.assertIn('65%', insight_text)  # Invisible work percentage
        
        print(f"✅ Generated {len(timing_insights)} timing insights")
        for insight in timing_insights:
            print(f"   - {insight[:80]}...")
    
    @patch('gtd_coach.patterns.evaluation_patterns.TimingAPI')
    def test_timing_api_timeout_handling(self, mock_timing_class):
        """Test handling of Timing API timeout"""
        mock_timing = Mock()
        mock_timing.is_configured.return_value = True
        # Simulate timeout
        mock_timing.fetch_projects_last_week.side_effect = TimeoutError("API timeout")
        mock_timing_class.return_value = mock_timing
        
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        patterns = analyzer.analyze_session("test_timing_session")
        
        # Should handle timeout gracefully
        self.assertIn('timing_validation', patterns)
        timing_data = patterns['timing_validation']
        
        self.assertFalse(timing_data['data_available'])
        self.assertIn('Error', timing_data.get('reason', ''))
        
        # Other patterns should still work
        self.assertIn('time_blindness', patterns)
        self.assertIn('task_switching', patterns)
        
        print(f"✅ Timeout handling working")


def run_tests():
    """Run all timing validation tests"""
    print("=" * 60)
    print("TIMING VALIDATION TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTimingValidation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TIMING VALIDATION TESTS PASSED")
    else:
        print(f"❌ {len(result.failures)} tests failed")
        for test, traceback in result.failures:
            print(f"\nFailed: {test}")
            print(traceback)
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)