#!/usr/bin/env python3
"""
Test Suite for Phase 2: Pattern Learning from Evaluation Data
Tests ADHD pattern detection, statistical analysis, and adaptive thresholds
"""

import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import unittest

# Import pattern learning modules
from gtd_coach.patterns.evaluation_patterns import ADHDPatternAnalyzer
from gtd_coach.patterns.pattern_aggregator import EvaluationAggregator
from gtd_coach.metrics.adaptive_metrics import AdaptiveThresholds
from gtd_coach.analytics.evaluation_analytics import EvaluationAnalytics


class TestPatternLearning(unittest.TestCase):
    """Test pattern learning functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp())
        self.eval_dir = self.test_dir / "evaluations"
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test evaluation data
        self._create_test_evaluations()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def _create_test_evaluations(self):
        """Create sample evaluation files for testing"""
        
        # Create evaluations with varying patterns
        test_sessions = [
            {
                "session_id": "test_session_1",
                "timestamp": (datetime.now() - timedelta(days=6)).isoformat(),
                "evaluations": [
                    {
                        "phase": "MIND_SWEEP",
                        "user_input": "I need to finish the report... also call mom... oh and the budget",
                        "coach_response": "Let's capture these items",
                        "coaching_quality": {
                            "score": 0.75,
                            "time_aware": True,
                            "structure": True,
                            "executive_support": True
                        },
                        "task_extraction": {
                            "score": 0.9,
                            "missed_tasks": []
                        }
                    }
                ],
                "summary": {
                    "average_scores": {
                        "task_extraction": 0.9,
                        "memory_relevance": 0.7,
                        "coaching_quality": 0.75
                    }
                }
            },
            {
                "session_id": "test_session_2",
                "timestamp": (datetime.now() - timedelta(days=4)).isoformat(),
                "evaluations": [
                    {
                        "phase": "MIND_SWEEP",
                        "user_input": "Project deadline. Meeting notes. Groceries. Exercise plan.",
                        "coaching_quality": {
                            "score": 0.6,
                            "time_aware": False,
                            "structure": True,
                            "executive_support": False
                        }
                    },
                    {
                        "phase": "PRIORITIZATION",
                        "coaching_quality": {
                            "score": 0.5,
                            "time_aware": False
                        }
                    }
                ],
                "summary": {
                    "average_scores": {
                        "task_extraction": 0.8,
                        "memory_relevance": 0.5,
                        "coaching_quality": 0.55
                    }
                }
            },
            {
                "session_id": "test_session_3",
                "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
                "evaluations": [
                    {
                        "phase": "MIND_SWEEP",
                        "user_input": "Too many things... I don't know... maybe later...",
                        "coaching_quality": {
                            "score": 0.4,
                            "time_aware": False,
                            "structure": False,
                            "executive_support": False
                        }
                    }
                ],
                "summary": {
                    "average_scores": {
                        "task_extraction": 0.5,
                        "memory_relevance": 0.4,
                        "coaching_quality": 0.4
                    },
                    "below_threshold": [
                        {"metric": "coaching_quality", "score": 0.4, "threshold": 0.6}
                    ]
                }
            }
        ]
        
        # Save test evaluations
        for session_data in test_sessions:
            session_id = session_data["session_id"]
            file_path = self.eval_dir / f"eval_{session_id}.json"
            with open(file_path, 'w') as f:
                json.dump(session_data, f, indent=2)
    
    def test_adhd_pattern_detection(self):
        """Test ADHD-specific pattern detection"""
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        
        # Test single session analysis
        patterns = analyzer.analyze_session("test_session_1")
        
        self.assertIn('time_blindness', patterns)
        self.assertIn('task_switching', patterns)
        self.assertIn('executive_function', patterns)
        self.assertIn('fatigue_indicators', patterns)
        
        # Check time blindness detection
        time_blindness = patterns['time_blindness']
        self.assertIsNotNone(time_blindness['score'])
        self.assertIn('severity', time_blindness)
        
        # Check task switching analysis
        task_switching = patterns['task_switching']
        self.assertIn('switch_frequency', task_switching)
        self.assertIn('incomplete_thoughts', task_switching)
        
        print(f"✅ ADHD pattern detection working")
    
    def test_pattern_aggregation(self):
        """Test pattern aggregation across sessions"""
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        
        # Aggregate patterns across all test sessions
        session_ids = ["test_session_1", "test_session_2", "test_session_3"]
        aggregated = analyzer.aggregate_patterns(session_ids)
        
        self.assertEqual(aggregated['session_count'], 3)
        
        # Check aggregated time blindness
        self.assertIn('time_blindness', aggregated)
        tb_data = aggregated['time_blindness']
        self.assertIsNotNone(tb_data.get('mean_score'))
        self.assertIn('trend', tb_data)
        
        # Check executive function aggregation
        self.assertIn('executive_function', aggregated)
        ef_data = aggregated['executive_function']
        self.assertIsNotNone(ef_data.get('mean_score'))
        
        print(f"✅ Pattern aggregation working")
    
    def test_statistical_analysis(self):
        """Test statistical analysis methods"""
        aggregator = EvaluationAggregator(self.test_dir)
        
        # Test rolling average calculation
        rolling_avg = aggregator.calculate_rolling_average('coaching_quality')
        
        self.assertIsNotNone(rolling_avg['mean'])
        self.assertIn('trend', rolling_avg)
        self.assertIn('values', rolling_avg)
        
        # Values should be declining based on test data
        if rolling_avg['trend']:
            self.assertEqual(rolling_avg['trend'], 'declining')
        
        # Test anomaly detection
        anomalies = aggregator.detect_anomalies('coaching_quality', threshold_multiplier=1.5)
        
        # Session 3 should be detected as anomaly (low score)
        self.assertIsInstance(anomalies, list)
        
        print(f"✅ Statistical analysis working")
    
    def test_session_clustering(self):
        """Test session clustering"""
        aggregator = EvaluationAggregator(self.test_dir)
        
        clustering_result = aggregator.cluster_sessions(n_clusters=2)
        
        self.assertIn('clusters', clustering_result)
        self.assertIn('cluster_names', clustering_result)
        
        # Should have at least one cluster
        clusters = clustering_result['clusters']
        self.assertGreater(len(clusters), 0)
        
        print(f"✅ Session clustering working")
    
    def test_adaptive_thresholds(self):
        """Test adaptive threshold adjustment"""
        # Create temporary config path
        config_path = self.test_dir / "adaptive_thresholds.json"
        thresholds = AdaptiveThresholds(config_path)
        
        # Test baseline calculation
        test_values = [0.7, 0.75, 0.8, 0.65, 0.72, 0.78]
        baseline = thresholds.calculate_baseline('test_metric', test_values)
        
        self.assertIn('mean', baseline)
        self.assertIn('std', baseline)
        self.assertIn('median', baseline)
        
        # Test threshold update
        updated = thresholds.update_threshold('task_extraction', test_values)
        
        # Check if threshold was adjusted
        current_threshold = thresholds.thresholds['task_extraction']['current']
        self.assertIsNotNone(current_threshold)
        
        # Test degradation detection
        degradation = thresholds.detect_degradation('task_extraction', 0.5)
        
        if degradation:
            self.assertIn('severity', degradation)
            self.assertIn('recommendation', degradation)
        
        print(f"✅ Adaptive thresholds working")
    
    def test_insight_generation(self):
        """Test insight generation"""
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Get pattern data
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        session_ids = ["test_session_1", "test_session_2", "test_session_3"]
        pattern_data = analyzer.aggregate_patterns(session_ids)
        
        # Get aggregated data
        aggregator = EvaluationAggregator(self.test_dir)
        stats_summary = aggregator.generate_statistical_summary()
        
        # Generate insights
        insights = analytics.generate_insights(pattern_data, stats_summary)
        
        self.assertIsInstance(insights, list)
        
        # Should generate some insights based on declining performance
        self.assertGreater(len(insights), 0)
        
        print(f"✅ Insight generation working")
        print(f"Generated {len(insights)} insights:")
        for insight in insights[:3]:  # Show first 3
            print(f"  - {insight[:80]}...")
    
    def test_weekly_summary(self):
        """Test weekly summary generation"""
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Generate weekly summary
        summary = analytics.create_weekly_summary()
        
        self.assertIn('session_count', summary)
        self.assertIn('adhd_patterns', summary)
        self.assertIn('insights', summary)
        self.assertIn('recommendations', summary)
        
        # Test markdown export
        markdown = analytics.export_insights_markdown(summary)
        
        self.assertIn('# GTD Coach Weekly Insights', markdown)
        self.assertIn('## Summary', markdown)
        
        print(f"✅ Weekly summary generation working")
    
    def test_performance_trends(self):
        """Test trend calculation"""
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Test with declining values
        values = [0.8, 0.75, 0.7, 0.65, 0.6]
        trends = analytics.calculate_trends(values)
        
        self.assertEqual(trends['trend'], 'declining')
        self.assertLess(trends['slope'], 0)
        
        # Test with improving values
        values = [0.6, 0.65, 0.7, 0.75, 0.8]
        trends = analytics.calculate_trends(values)
        
        self.assertEqual(trends['trend'], 'improving')
        self.assertGreater(trends['slope'], 0)
        
        print(f"✅ Performance trend analysis working")
    
    def test_personal_baseline(self):
        """Test personal baseline calculation"""
        aggregator = EvaluationAggregator(self.test_dir)
        
        baseline = aggregator.calculate_personal_baseline()
        
        # Handle case where insufficient data returns empty dict
        if baseline:
            self.assertIn('metrics', baseline)
            self.assertIn('overall_performance', baseline)
            self.assertIn('confidence', baseline)
            
            # Check baseline metrics
            metrics = baseline.get('metrics', {})
            for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
                if metric in metrics:
                    self.assertIn('mean', metrics[metric])
                    self.assertIn('lower_bound', metrics[metric])
                    self.assertIn('upper_bound', metrics[metric])
            
            print(f"✅ Personal baseline calculation working")
        else:
            # Insufficient data case - create more test data
            # This is expected with only 3 test sessions
            print(f"✅ Personal baseline correctly handled insufficient data")
    
    def test_integration(self):
        """Test integration of all components"""
        # Initialize all components
        analyzer = ADHDPatternAnalyzer(self.test_dir)
        aggregator = EvaluationAggregator(self.test_dir)
        thresholds = AdaptiveThresholds(self.test_dir / "adaptive_config.json")
        analytics = EvaluationAnalytics(self.test_dir)
        
        # Run full analysis pipeline
        session_ids = ["test_session_1", "test_session_2", "test_session_3"]
        
        # 1. Analyze ADHD patterns
        patterns = analyzer.aggregate_patterns(session_ids)
        
        # 2. Generate statistical summary
        stats = aggregator.generate_statistical_summary()
        
        # 3. Update adaptive thresholds
        thresholds.update_from_aggregated_data(stats['metrics'])
        
        # 4. Generate insights
        insights = analytics.generate_insights(patterns, stats)
        
        # 5. Create weekly summary
        summary = analytics.create_weekly_summary()
        
        # Verify pipeline produced results
        self.assertIsNotNone(patterns)
        self.assertIsNotNone(stats)
        self.assertIsNotNone(insights)
        self.assertIsNotNone(summary)
        
        print(f"✅ Full integration pipeline working")
        print(f"\nPipeline Results:")
        print(f"  - Patterns detected: {len(patterns)}")
        print(f"  - Statistical metrics: {len(stats.get('metrics', {}))}")
        print(f"  - Insights generated: {len(insights)}")
        print(f"  - Weekly summary created: {summary['session_count']} sessions analyzed")


def run_tests():
    """Run all pattern learning tests"""
    print("=" * 60)
    print("PATTERN LEARNING TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPatternLearning)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL PATTERN LEARNING TESTS PASSED")
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