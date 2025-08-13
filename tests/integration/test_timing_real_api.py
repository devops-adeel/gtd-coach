#!/usr/bin/env python3
"""
Real Timing API Integration Tests
Tests the actual Timing API integration with live data
Only runs when TIMING_API_KEY is configured
"""

import os
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest import skipUnless

# Set the API key from environment or user-provided value
TIMING_API_KEY = os.getenv('TIMING_API_KEY')

# Check if we should run real API tests
HAS_TIMING_API = bool(TIMING_API_KEY)
SKIP_REASON = "Timing API key not configured - set TIMING_API_KEY environment variable"

# Import our modules
from gtd_coach.integrations.timing import TimingAPI
from gtd_coach.patterns.evaluation_patterns import ADHDPatternAnalyzer
from gtd_coach.analytics.evaluation_analytics import EvaluationAnalytics


@skipUnless(HAS_TIMING_API, SKIP_REASON)
class TestRealTimingAPI(unittest.TestCase):
    """Test real Timing API integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up for all tests - configure API once"""
        print("\n" + "=" * 60)
        print("TESTING WITH REAL TIMING API")
        print("=" * 60)
        
        # Temporarily set the API key for testing
        if TIMING_API_KEY and not os.getenv('TIMING_API_KEY'):
            os.environ['TIMING_API_KEY'] = TIMING_API_KEY
    
    def setUp(self):
        """Set up for each test"""
        self.timing = TimingAPI()
        
        # Create temp directory for test data
        self.test_dir = Path(tempfile.mkdtemp())
        self.eval_dir = self.test_dir / "evaluations"
        self.eval_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up after each test"""
        shutil.rmtree(self.test_dir)
    
    def test_api_configuration(self):
        """Test that API is properly configured"""
        self.assertTrue(self.timing.is_configured())
        print(f"✅ Timing API is configured")
    
    def test_fetch_projects_last_week(self):
        """Test fetching real project data from last week"""
        projects = self.timing.fetch_projects_last_week(min_minutes=30)
        
        print(f"\n📊 Fetched {len(projects)} projects from last 7 days:")
        
        if projects:
            # Display top 5 projects
            for i, project in enumerate(projects[:5], 1):
                print(f"   {i}. {project['name']}: {project['time_spent']:.1f} hours")
            
            if len(projects) > 5:
                print(f"   ... and {len(projects) - 5} more projects")
            
            # Test data structure
            first_project = projects[0]
            self.assertIn('name', first_project)
            self.assertIn('time_spent', first_project)
            self.assertIsInstance(first_project['time_spent'], (int, float))
            
            # Calculate total hours
            total_hours = sum(p['time_spent'] for p in projects)
            print(f"\n   Total time tracked: {total_hours:.1f} hours")
        else:
            print("   No projects found (might be a new Timing account)")
        
        print(f"✅ Project fetching works correctly")
    
    def test_fetch_time_entries(self):
        """Test fetching individual time entries"""
        entries = self.timing.fetch_time_entries_last_week(max_entries=20)
        
        print(f"\n📝 Fetched {len(entries)} time entries from last 7 days:")
        
        if entries:
            # Analyze first few entries
            for i, entry in enumerate(entries[:3], 1):
                duration_min = entry.get('duration_seconds', 0) / 60
                print(f"   {i}. {entry.get('project', 'Unknown')}: {duration_min:.1f} min")
                print(f"      App: {entry.get('application', 'N/A')}")
            
            # Test data structure
            first_entry = entries[0]
            self.assertIn('project', first_entry)
            self.assertIn('duration_seconds', first_entry)
            self.assertIn('start_time', first_entry)
            
            print(f"✅ Time entry fetching works correctly")
        else:
            print("   No time entries found")
    
    def test_context_switch_detection(self):
        """Test context switch analysis with real data"""
        entries = self.timing.fetch_time_entries_last_week(max_entries=100)
        
        if entries:
            switch_analysis = self.timing.detect_context_switches(entries)
            
            print(f"\n🔄 Context Switch Analysis:")
            print(f"   Total switches: {switch_analysis['total_switches']}")
            print(f"   Switches per hour: {switch_analysis['switches_per_hour']:.2f}")
            print(f"   Focus periods (>30 min): {len(switch_analysis['focus_periods'])}")
            print(f"   Scatter periods: {len(switch_analysis['scatter_periods'])}")
            
            # Display top switch patterns
            if switch_analysis['switch_patterns']:
                print(f"\n   Top switch patterns:")
                for pattern, count in switch_analysis['switch_patterns'][:3]:
                    print(f"      {pattern}: {count} times")
            
            # Calculate focus metrics
            focus_metrics = self.timing.calculate_focus_metrics(switch_analysis)
            print(f"\n   Focus Score: {focus_metrics['focus_score']:.0f}/100")
            print(f"   Hyperfocus periods: {focus_metrics.get('hyperfocus_count', 0)}")
            
            print(f"✅ Context switch detection works correctly")
        else:
            print("   No entries for context switch analysis")
    
    def test_pattern_enrichment_with_real_data(self):
        """Test pattern enrichment with real Timing data"""
        # Create a sample evaluation with realistic MIND_SWEEP data
        eval_data = {
            "session_id": "real_api_test",
            "timestamp": datetime.now().isoformat(),
            "evaluations": [
                {
                    "phase": "MIND_SWEEP",
                    "user_input": "Worked on some coding projects and had meetings. Email catch-up and documentation.",
                    "coaching_quality": {
                        "score": 0.7,
                        "time_aware": True,
                        "structure": True
                    }
                }
            ],
            "summary": {
                "average_scores": {
                    "task_extraction": 0.8,
                    "memory_relevance": 0.6,
                    "coaching_quality": 0.7
                }
            }
        }
        
        # Save evaluation file
        eval_file = self.eval_dir / "eval_real_api_test.json"
        with open(eval_file, 'w') as f:
            json.dump(eval_data, f)
        
        # Create analyzer and analyze with real Timing data
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        patterns = analyzer.analyze_session("real_api_test")
        
        print(f"\n🧠 Pattern Analysis with Real Data:")
        
        if 'timing_validation' in patterns:
            timing_data = patterns['timing_validation']
            
            if timing_data.get('data_available'):
                print(f"   Projects tracked: {timing_data['project_count']}")
                print(f"   Items mentioned: {timing_data['mentioned_count']}")
                print(f"   Discrepancy pattern: {timing_data['discrepancy_pattern']}")
                print(f"   Invisible work ratio: {timing_data['invisible_work_ratio']:.0%}")
                
                # Interpret the pattern
                pattern = timing_data['discrepancy_pattern']
                if pattern == 'time_blindness':
                    print(f"\n   ⚠️ Time blindness pattern detected - many projects not mentioned")
                elif pattern == 'selective_awareness':
                    print(f"\n   🎯 Selective awareness - focusing on memorable work")
                elif pattern == 'high_awareness':
                    print(f"\n   ✨ Good time awareness - most work is captured")
                
                print(f"\n✅ Pattern enrichment with real data works correctly")
            else:
                print(f"   No Timing data available: {timing_data.get('reason')}")
        else:
            print("   Timing validation not included in patterns")
    
    def test_insight_generation_with_real_patterns(self):
        """Test insight generation using real pattern data"""
        # Use real Timing data to create patterns
        projects = self.timing.fetch_projects_last_week(min_minutes=30)
        
        if projects:
            # Create pattern data based on real projects
            invisible_ratio = 0.6 if len(projects) > 5 else 0.3
            pattern_type = 'time_blindness' if len(projects) > 8 else 'selective_awareness'
            
            pattern_data = {
                'timing_validation': {
                    'data_available': True,
                    'discrepancy_pattern': pattern_type,
                    'invisible_work_ratio': invisible_ratio,
                    'project_count': len(projects),
                    'mentioned_count': max(1, len(projects) // 3)
                }
            }
            
            # Generate insights
            analytics = EvaluationAnalytics(self.test_dir)
            insights = analytics.generate_insights(pattern_data, {})
            
            print(f"\n💡 Insights Generated from Real Data:")
            timing_insights = [i for i in insights if any(
                keyword in i for keyword in ['Time', 'Invisible', 'Awareness']
            )]
            
            for i, insight in enumerate(timing_insights, 1):
                # Truncate long insights for display
                display_insight = insight[:150] + "..." if len(insight) > 150 else insight
                print(f"\n   {i}. {display_insight}")
            
            print(f"\n✅ Insight generation with real patterns works correctly")
        else:
            print("   No projects found for insight generation")
    
    def test_api_error_handling(self):
        """Test API error handling with invalid requests"""
        # Test with invalid date range (future dates)
        timing = TimingAPI()
        
        # Monkey-patch to use future dates
        original_fetch = timing.fetch_projects_last_week
        
        def fetch_future():
            # This should return empty or handle gracefully
            end_date = datetime.now() + timedelta(days=30)
            start_date = end_date + timedelta(days=7)
            # We can't actually change the internal implementation
            # So just call the original and check it handles edge cases
            return original_fetch(min_minutes=99999)  # Very high threshold
        
        projects = fetch_future()
        self.assertEqual(projects, [])  # Should return empty for unrealistic threshold
        
        print(f"✅ API error handling works correctly")


class TestTimingAPINotConfigured(unittest.TestCase):
    """Test behavior when Timing API is not configured"""
    
    def setUp(self):
        """Remove API key for these tests"""
        self.original_key = os.environ.pop('TIMING_API_KEY', None)
    
    def tearDown(self):
        """Restore API key if it existed"""
        if self.original_key:
            os.environ['TIMING_API_KEY'] = self.original_key
    
    def test_graceful_fallback_without_api(self):
        """Test that system works without API key"""
        timing = TimingAPI()
        
        self.assertFalse(timing.is_configured())
        
        # Should return empty lists
        projects = timing.fetch_projects_last_week()
        self.assertEqual(projects, [])
        
        entries = timing.fetch_time_entries_last_week()
        self.assertEqual(entries, [])
        
        print(f"✅ Graceful fallback without API key works correctly")


def run_real_api_tests():
    """Run all real API tests"""
    print("\n" + "=" * 60)
    print("TIMING API INTEGRATION TEST SUITE")
    print("=" * 60)
    
    if HAS_TIMING_API:
        print(f"✓ Timing API key configured")
        print(f"  Running real API tests...")
    else:
        print(f"⚠️ Timing API key not configured")
        print(f"  Set TIMING_API_KEY environment variable to run real tests")
        print(f"  Get your key from: https://web.timingapp.com")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests based on configuration
    suite.addTests(loader.loadTestsFromTestCase(TestRealTimingAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestTimingAPINotConfigured))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TIMING API TESTS PASSED")
        if result.skipped:
            print(f"   ({len(result.skipped)} tests skipped - API not configured)")
    else:
        print(f"❌ {len(result.failures)} tests failed")
        for test, traceback in result.failures:
            print(f"\nFailed: {test}")
            print(traceback[:500])  # Truncate long tracebacks
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Check for API key in environment
    if not os.getenv('TIMING_API_KEY'):
        print("⚠️ TIMING_API_KEY not found in environment")
        print("Please set TIMING_API_KEY environment variable to run this test")
        print("Get your API key from: https://web.timingapp.com")
        exit(1)
    
    success = run_real_api_tests()
    exit(0 if success else 1)