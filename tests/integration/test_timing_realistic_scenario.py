#!/usr/bin/env python3
"""
Realistic Timing API Scenario Test
Tests pattern detection with realistic user input matching actual project names
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest

# Set the API key
TIMING_API_KEY = os.getenv('TIMING_API_KEY')

from gtd_coach.integrations.timing import TimingAPI
from gtd_coach.patterns.evaluation_patterns import ADHDPatternAnalyzer
from gtd_coach.analytics.evaluation_analytics import EvaluationAnalytics


class TestRealisticTimingScenario(unittest.TestCase):
    """Test realistic scenarios with actual Timing data"""
    
    def setUp(self):
        """Set up test environment"""
        # Set API key if provided
        if TIMING_API_KEY:
            os.environ['TIMING_API_KEY'] = TIMING_API_KEY
        
        self.timing = TimingAPI()
        self.test_dir = Path(tempfile.mkdtemp())
        self.eval_dir = self.test_dir / "evaluations"
        self.eval_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir)
    
    def test_realistic_pattern_detection(self):
        """Test with realistic user input based on actual Timing data"""
        
        # First, fetch real projects to understand what's actually being tracked
        projects = self.timing.fetch_projects_last_week(min_minutes=30)
        
        if not projects:
            self.skipTest("No Timing data available")
        
        print("\n" + "=" * 60)
        print("REALISTIC PATTERN DETECTION TEST")
        print("=" * 60)
        
        # Display actual projects for reference
        print(f"\n📊 Actual projects tracked (top 5):")
        for i, project in enumerate(projects[:5], 1):
            print(f"   {i}. {project['name']}: {project['time_spent']:.1f} hours")
        
        # Create three different scenarios based on real data
        scenarios = [
            {
                "name": "High Awareness",
                "description": "User mentions most of their actual work",
                "user_input": "Spent time on communication tasks, lots of email and messaging. "
                              "Did some web research and browsing. Worked on development projects. "
                              "Had some business and office work to handle.",
                "expected_pattern": "high_awareness"
            },
            {
                "name": "Selective Awareness",
                "description": "User mentions only the memorable work",
                "user_input": "Worked on the AuthZ problem and did some development. "
                              "Had a few important tasks to complete.",
                "expected_pattern": "selective_awareness"
            },
            {
                "name": "Time Blindness",
                "description": "User mentions very little of actual work",
                "user_input": "Just did some regular work, nothing special. "
                              "Caught up on a few things.",
                "expected_pattern": "time_blindness"
            }
        ]
        
        for scenario in scenarios:
            print(f"\n📝 Scenario: {scenario['name']}")
            print(f"   Description: {scenario['description']}")
            print(f"   User input: \"{scenario['user_input'][:60]}...\"")
            
            # Create evaluation data
            eval_data = {
                "session_id": f"scenario_{scenario['name'].lower().replace(' ', '_')}",
                "timestamp": datetime.now().isoformat(),
                "evaluations": [
                    {
                        "phase": "MIND_SWEEP",
                        "user_input": scenario['user_input'],
                        "coaching_quality": {"score": 0.7, "time_aware": True}
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
            
            # Save and analyze
            session_id = eval_data['session_id']
            eval_file = self.eval_dir / f"eval_{session_id}.json"
            with open(eval_file, 'w') as f:
                json.dump(eval_data, f)
            
            analyzer = ADHDPatternAnalyzer(self.test_dir)
            patterns = analyzer.analyze_session(session_id)
            
            if 'timing_validation' in patterns:
                timing_data = patterns['timing_validation']
                
                if timing_data.get('data_available'):
                    print(f"\n   Results:")
                    print(f"   - Pattern detected: {timing_data['discrepancy_pattern']}")
                    print(f"   - Invisible work: {timing_data['invisible_work_ratio']:.0%}")
                    print(f"   - Projects mentioned: {timing_data['mentioned_count']}/{timing_data['project_count']}")
                    
                    # Generate and display insight
                    analytics = EvaluationAnalytics(self.test_dir)
                    pattern_data = {'timing_validation': timing_data}
                    insights = analytics.generate_insights(pattern_data, {})
                    
                    timing_insights = [i for i in insights if any(
                        kw in i for kw in ['Time', 'Invisible', 'Awareness']
                    )]
                    
                    if timing_insights:
                        print(f"\n   Generated insight:")
                        insight = timing_insights[0]
                        # Extract just the bold title part
                        if '**' in insight:
                            title = insight.split('**')[1] if len(insight.split('**')) > 1 else insight[:50]
                            print(f"   → {title}")
    
    def test_focus_metrics_with_real_entries(self):
        """Test focus metrics calculation with real time entries"""
        
        entries = self.timing.fetch_time_entries_last_week(max_entries=50)
        
        if not entries:
            self.skipTest("No time entries available")
        
        print("\n" + "=" * 60)
        print("FOCUS METRICS ANALYSIS")
        print("=" * 60)
        
        # Analyze context switches
        switch_analysis = self.timing.detect_context_switches(entries)
        focus_metrics = self.timing.calculate_focus_metrics(switch_analysis)
        
        print(f"\n🎯 Focus Analysis Results:")
        print(f"   Focus Score: {focus_metrics['focus_score']:.0f}/100")
        print(f"   Context Switches: {switch_analysis['total_switches']}")
        print(f"   Switches per hour: {switch_analysis['switches_per_hour']:.2f}")
        
        # Interpret the score
        score = focus_metrics['focus_score']
        if score >= 90:
            print(f"\n   ✨ Excellent focus! Very few context switches detected.")
        elif score >= 70:
            print(f"\n   👍 Good focus with manageable context switching.")
        elif score >= 40:
            print(f"\n   ⚠️ Moderate focus - consider time-blocking to reduce switches.")
        else:
            print(f"\n   🔄 High context switching detected - may benefit from focus strategies.")
        
        # Show focus periods if any
        if switch_analysis['focus_periods']:
            print(f"\n   Deep focus periods (>30 min):")
            for i, period in enumerate(switch_analysis['focus_periods'][:3], 1):
                print(f"   {i}. {period['project']}: {period['duration_minutes']:.0f} min")
        
        # Show scatter periods if any
        if switch_analysis['scatter_periods']:
            print(f"\n   ⚠️ Scatter periods detected (rapid switching):")
            for period in switch_analysis['scatter_periods'][:2]:
                print(f"   - {period['switches_count']} switches at {period['timestamp'][:10]}")
    
    def test_weekly_summary_with_timing(self):
        """Test generating a weekly summary with real Timing data"""
        
        print("\n" + "=" * 60)
        print("WEEKLY SUMMARY WITH TIMING VALIDATION")
        print("=" * 60)
        
        # Create a mock session with realistic input
        eval_data = {
            "session_id": "weekly_summary_test",
            "timestamp": datetime.now().isoformat(),
            "evaluations": [
                {
                    "phase": "MIND_SWEEP",
                    "user_input": "This week I focused on communication, had lots of meetings "
                                 "and email to handle. Also did some development work and "
                                 "research for the AuthZ project.",
                    "coaching_quality": {"score": 0.75, "time_aware": True, "structure": True}
                },
                {
                    "phase": "PROJECT_REVIEW",
                    "user_input": "Main projects were AuthZ research and general communication",
                    "coaching_quality": {"score": 0.7}
                },
                {
                    "phase": "PRIORITIZATION",
                    "user_input": "Priority is finishing the AuthZ implementation",
                    "coaching_quality": {"score": 0.8}
                }
            ],
            "summary": {
                "average_scores": {
                    "task_extraction": 0.85,
                    "memory_relevance": 0.7,
                    "coaching_quality": 0.75
                }
            }
        }
        
        # Save evaluation
        eval_file = self.eval_dir / "eval_weekly_summary_test.json"
        with open(eval_file, 'w') as f:
            json.dump(eval_data, f)
        
        # Analyze with Timing validation
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        patterns = analyzer.analyze_session("weekly_summary_test")
        
        # Generate weekly summary
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Create aggregated pattern data
        aggregated_patterns = {
            'session_count': 1,
            'time_blindness': {
                'mean_score': patterns['time_blindness']['score'],
                'trend': 'stable'
            },
            'task_switching': {
                'mean_frequency': patterns['task_switching']['switch_frequency']
            },
            'executive_function': {
                'mean_score': patterns['executive_function']['overall_score']
            },
            'timing_validation': patterns.get('timing_validation', {})
        }
        
        # Generate insights
        insights = analytics.generate_insights(aggregated_patterns, {})
        
        print(f"\n📊 Weekly Summary:")
        print(f"   Sessions analyzed: 1 (test session)")
        print(f"   Time awareness score: {patterns['time_blindness']['score']:.0%}")
        print(f"   Executive function score: {patterns['executive_function']['overall_score']:.0%}")
        
        if 'timing_validation' in patterns and patterns['timing_validation'].get('data_available'):
            timing = patterns['timing_validation']
            print(f"\n   Timing Validation:")
            print(f"   - Actual projects tracked: {timing['project_count']}")
            print(f"   - Projects mentioned: {timing['mentioned_count']}")
            print(f"   - Pattern: {timing['discrepancy_pattern']}")
            print(f"   - Invisible work: {timing['invisible_work_ratio']:.0%}")
        
        print(f"\n   Key Insights ({len(insights)} total):")
        for i, insight in enumerate(insights[:3], 1):
            # Extract key message
            if '**' in insight:
                parts = insight.split('**')
                if len(parts) > 1:
                    title = parts[1]
                    print(f"   {i}. {title}")


def run_realistic_tests():
    """Run realistic scenario tests"""
    if not os.getenv('TIMING_API_KEY'):
        print("⚠️ TIMING_API_KEY not found in environment")
        print("Please set TIMING_API_KEY environment variable to run this test")
        print("Get your API key from: https://web.timingapp.com")
        return False
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRealisticTimingScenario)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_realistic_tests()
    exit(0 if success else 1)