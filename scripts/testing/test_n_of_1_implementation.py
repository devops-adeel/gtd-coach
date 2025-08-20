#!/usr/bin/env python3
"""
Test script for N-of-1 implementation
Verifies that all components work together
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add to path for imports
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from gtd_coach.metrics import NorthStarMetrics
        print("✓ NorthStarMetrics imported")
    except ImportError as e:
        print(f"✗ Failed to import NorthStarMetrics: {e}")
        return False
    
    try:
        from gtd_coach.experiments import NOf1Experimenter
        print("✓ NOf1Experimenter imported")
    except ImportError as e:
        print(f"✗ Failed to import NOf1Experimenter: {e}")
        return False
    
    try:
        from scripts.analysis.analyze_n_of_1 import NOf1Analyzer
        print("✓ NOf1Analyzer imported")
    except ImportError as e:
        print(f"✗ Failed to import NOf1Analyzer: {e}")
        return False
    
    try:
        from scripts.weekly_experiment_report import WeeklyExperimentReporter
        print("✓ WeeklyExperimentReporter imported")
    except ImportError as e:
        print(f"✗ Failed to import WeeklyExperimentReporter: {e}")
        return False
    
    return True


def test_north_star_metrics():
    """Test North Star metrics functionality"""
    print("\nTesting North Star metrics...")
    
    from gtd_coach.metrics import NorthStarMetrics
    
    # Create instance
    metrics = NorthStarMetrics("test_session_123")
    
    # Test memory relevance calculation
    retrieved = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
    used = [{'id': '1'}, {'id': '3'}]
    relevance = metrics.calculate_memory_relevance(retrieved, used)
    
    expected = 2/3  # 2 out of 3 used
    if abs(relevance - expected) < 0.01:
        print(f"✓ Memory relevance calculation: {relevance:.2f}")
    else:
        print(f"✗ Memory relevance calculation failed: {relevance} != {expected}")
        return False
    
    # Test time to insight
    import time
    time.sleep(0.1)  # Simulate delay
    time_to_insight = metrics.measure_time_to_insight()  # Let it use current time
    
    if time_to_insight is not None and time_to_insight >= 0:
        print(f"✓ Time to insight tracking: {time_to_insight}s")
    else:
        print(f"✗ Time to insight tracking failed: {time_to_insight}")
        return False
    
    # Test task follow-through
    planned = [{'task': 'Task 1'}, {'task': 'Task 2'}]
    completed = [{'task': 'task 1'}]  # Case insensitive match
    followthrough = metrics.track_task_followthrough(planned, completed)
    
    expected = 0.5  # 1 out of 2 completed
    if abs(followthrough - expected) < 0.01:
        print(f"✓ Task follow-through calculation: {followthrough:.2f}")
    else:
        print(f"✗ Task follow-through calculation failed: {followthrough} != {expected}")
        return False
    
    return True


def test_experiment_framework():
    """Test N-of-1 experiment framework"""
    print("\nTesting experiment framework...")
    
    from gtd_coach.experiments import NOf1Experimenter
    
    # Create instance
    experimenter = NOf1Experimenter()
    
    # Test current experiment retrieval
    current_exp = experimenter.get_current_experiment()
    if current_exp and 'name' in current_exp:
        print(f"✓ Current experiment: {current_exp['name']}")
    else:
        print("✗ Failed to get current experiment")
        return False
    
    # Test condition retrieval
    condition = experimenter.get_condition_for_session(1)
    if condition and 'value' in condition:
        print(f"✓ Condition for session 1: {condition['value']}")
    else:
        print("✗ Failed to get condition")
        return False
    
    # Test ABAB pattern
    conditions = []
    for i in range(1, 5):
        cond = experimenter.get_condition_for_session(i)
        conditions.append(cond['value'])
    
    # Should have ABAB pattern (two unique values)
    unique_conditions = list(set(conditions))
    if len(unique_conditions) <= 2 and conditions[0] == conditions[2] and conditions[1] == conditions[3]:
        print(f"✓ ABAB pattern: {conditions}")
    else:
        print(f"✗ ABAB pattern failed: {conditions}")
        return False
    
    # Test experiment metadata
    metadata = experimenter.get_experiment_metadata()
    if metadata and 'experiment_week' in metadata:
        print(f"✓ Experiment metadata generated")
    else:
        print("✗ Failed to generate metadata")
        return False
    
    return True


def test_analysis_tools():
    """Test analysis tools with mock data"""
    print("\nTesting analysis tools...")
    
    from scripts.analysis.analyze_n_of_1 import NOf1Analyzer
    
    # Create analyzer
    analyzer = NOf1Analyzer()
    
    # Create mock traces
    mock_traces = [
        {
            'session_id': 'test_1',
            'session_start': datetime.now().isoformat(),
            'metrics': {
                'memory_relevance_score': 0.7,
                'time_to_first_capture': 25,
                'task_followthrough_rate': 0.6
            },
            'experiment_value': 'condition_a',
            'experiment_variable': 'test_variable',
            'session_in_pattern': 1
        },
        {
            'session_id': 'test_2',
            'session_start': datetime.now().isoformat(),
            'metrics': {
                'memory_relevance_score': 0.8,
                'time_to_first_capture': 20,
                'task_followthrough_rate': 0.7
            },
            'experiment_value': 'condition_b',
            'experiment_variable': 'test_variable',
            'session_in_pattern': 2
        }
    ]
    
    # Test variance analysis
    variance = analyzer.analyze_within_condition_variance(mock_traces)
    if variance and len(variance) > 0:
        print(f"✓ Variance analysis completed: {len(variance)} conditions")
    else:
        print("✗ Variance analysis failed")
        return False
    
    # Test effect size calculation
    effect_sizes = analyzer.calculate_personal_effect_size(mock_traces)
    if effect_sizes:
        print(f"✓ Effect size calculation completed")
    else:
        print("✗ Effect size calculation failed")
        return False
    
    # Test order effects
    order_effects = analyzer.detect_order_effects(mock_traces)
    print(f"✓ Order effect analysis completed")
    
    return True


def test_weekly_reporter():
    """Test weekly report generation"""
    print("\nTesting weekly reporter...")
    
    from scripts.weekly_experiment_report import WeeklyExperimentReporter
    
    # Create reporter
    reporter = WeeklyExperimentReporter()
    
    # Test report generation (will use mock data if no real data)
    try:
        report = reporter.generate_full_report()
        if report and len(report) > 100:
            print(f"✓ Weekly report generated ({len(report)} characters)")
        else:
            print("✗ Report generation failed")
            return False
    except Exception as e:
        print(f"✗ Report generation error: {e}")
        return False
    
    return True


def test_integration():
    """Test that all components work together"""
    print("\nTesting integration...")
    
    from gtd_coach.metrics import NorthStarMetrics
    from gtd_coach.experiments import NOf1Experimenter
    
    # Create instances
    metrics = NorthStarMetrics("integration_test")
    experimenter = NOf1Experimenter()
    
    # Simulate a session
    print("Simulating GTD session...")
    
    # Get current experiment
    exp_metadata = experimenter.get_experiment_metadata()
    print(f"  Experiment: {exp_metadata.get('experiment_name', 'Unknown')}")
    print(f"  Variable: {exp_metadata.get('experiment_variable', 'Unknown')}")
    print(f"  Condition: {exp_metadata.get('experiment_value', 'Unknown')}")
    
    # Test override capability
    if experimenter.should_override():
        print(f"  Override Active: True")
    
    # Track some metrics
    metrics.measure_time_to_insight()
    metrics.calculate_memory_relevance([{'id': '1'}], [{'id': '1'}])
    
    # Get all metrics
    all_metrics = metrics.get_all_metrics()
    print(f"  Metrics tracked: {len(all_metrics)}")
    
    # Save metrics
    try:
        data_dir = Path.home() / "gtd-coach" / "data" / "test"
        data_dir.mkdir(parents=True, exist_ok=True)
        metrics.save_metrics(data_dir)
        print("✓ Integration test completed successfully")
        
        # Clean up test file
        test_file = data_dir / f"north_star_metrics_{metrics.session_id}.json"
        if test_file.exists():
            test_file.unlink()
            
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("N-OF-1 IMPLEMENTATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("North Star Metrics", test_north_star_metrics),
        ("Experiment Framework", test_experiment_framework),
        ("Analysis Tools", test_analysis_tools),
        ("Weekly Reporter", test_weekly_reporter),
        ("Integration", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())