#!/usr/bin/env python3
"""
Test script for LLM-as-a-Judge evaluation system
Tests the post-session evaluation without running a full GTD review
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from gtd_coach.evaluation import PostSessionEvaluator
from gtd_coach.evaluation.criteria import EvaluationCriteria


def test_evaluation_prompts():
    """Test evaluation criteria prompt generation"""
    print("Testing evaluation prompts...")
    print("-" * 50)
    
    # Test task extraction prompt
    interaction = {
        'phase': 'MIND_SWEEP',
        'user_input': "I need to prepare the quarterly report, call John about the project, and maybe look into that new software tool if I have time",
        'extracted_tasks': ["Prepare quarterly report", "Call John about project"]
    }
    
    prompt = EvaluationCriteria.get_task_extraction_prompt(interaction)
    print("\n📝 Task Extraction Prompt (preview):")
    print(prompt[:500] + "...")
    
    # Test memory relevance prompt
    interaction = {
        'phase': 'PROJECT_REVIEW',
        'user_input': "Working on the marketing campaign",
        'retrieved_memories': [
            "Last week struggled with campaign timeline",
            "Previously mentioned needing design resources"
        ],
        'coach_response': "Let's focus on the timeline. You mentioned last week this was challenging."
    }
    
    prompt = EvaluationCriteria.get_memory_relevance_prompt(interaction)
    print("\n🧠 Memory Relevance Prompt (preview):")
    print(prompt[:500] + "...")
    
    # Test coaching quality prompt
    interaction = {
        'phase': 'PRIORITIZATION',
        'time_remaining': '2 minutes',
        'user_input': "I have so many things to do, I don't know where to start",
        'coach_response': "Let's break this down. Pick your top 3 most urgent items. We have 2 minutes left, so let's be quick but thoughtful."
    }
    
    prompt = EvaluationCriteria.get_coaching_quality_prompt(interaction)
    print("\n🏆 Coaching Quality Prompt (preview):")
    print(prompt[:500] + "...")
    
    print("\n✅ Prompt generation successful!")


def test_mock_evaluation():
    """Test evaluation with mock session data"""
    print("\n\nTesting mock session evaluation...")
    print("-" * 50)
    
    # Create mock session data
    mock_session = {
        'session_id': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'duration': 28.5,
        'interactions': [
            {
                'timestamp': datetime.now().isoformat(),
                'phase': 'MIND_SWEEP',
                'user_input': 'I need to finish the budget report and schedule team meetings',
                'coach_response': 'Great! I\'ve captured those tasks. What else is on your mind?',
                'extracted_tasks': ['Finish budget report', 'Schedule team meetings'],
                'retrieved_memories': []
            },
            {
                'timestamp': datetime.now().isoformat(),
                'phase': 'PRIORITIZATION',
                'user_input': 'The budget report is most urgent',
                'coach_response': 'Excellent. Let\'s mark that as your A priority. You have 2 minutes left to assign priorities to the remaining items.',
                'time_remaining': '2 minutes',
                'retrieved_memories': ['Last week: Budget report was mentioned as stressful']
            }
        ],
        'review_data': {
            'projects_reviewed': 5,
            'decisions_made': 8,
            'items_captured': 12
        }
    }
    
    # Initialize evaluator
    print("Initializing evaluator...")
    evaluator = PostSessionEvaluator()
    
    # Run evaluation (fire-and-forget)
    print(f"Evaluating session {mock_session['session_id']}...")
    evaluator.evaluate_session(mock_session)
    
    print("✅ Evaluation queued successfully (running in background)")
    print("\nNote: Check ~/gtd-coach/data/evaluations/ for results after a few seconds")


def test_configuration():
    """Test configuration loading"""
    print("\n\nTesting configuration...")
    print("-" * 50)
    
    config_path = Path.home() / "gtd-coach" / "config" / "evaluation" / "judge_config.yaml"
    
    if config_path.exists():
        print(f"✅ Configuration file found at {config_path}")
        
        # Try to load and display key settings
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            eval_config = config.get('evaluation', {})
            print(f"\nKey settings:")
            print(f"  Enabled: {eval_config.get('enabled', False)}")
            print(f"  Mode: {eval_config.get('mode', 'unknown')}")
            print(f"  Models:")
            for task, model in eval_config.get('models', {}).items():
                print(f"    {task}: {model}")
            print(f"  Thresholds:")
            for metric, threshold in eval_config.get('thresholds', {}).items():
                print(f"    {metric}: {threshold}")
        except ImportError:
            print("⚠️  PyYAML not installed - run: pip install PyYAML")
            print("Configuration file exists but cannot be parsed without PyYAML")
    else:
        print(f"⚠️  Configuration file not found at {config_path}")
        print("Using default configuration")


def test_threshold_calculation():
    """Test dynamic threshold calculation"""
    print("\n\nTesting threshold calculation...")
    print("-" * 50)
    
    # Test base thresholds
    print("Base thresholds (no user history):")
    for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
        threshold = EvaluationCriteria.get_intervention_threshold(metric)
        print(f"  {metric}: {threshold}")
    
    # Test with user history
    print("\nPersonalized thresholds (with user history):")
    user_history = {
        'task_extraction_average': 0.85,
        'memory_relevance_average': 0.65,
        'coaching_quality_average': 0.75
    }
    
    for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
        threshold = EvaluationCriteria.get_intervention_threshold(metric, user_history)
        print(f"  {metric}: {threshold} (based on avg: {user_history.get(f'{metric}_average', 'N/A')})")


def main():
    """Run all tests"""
    print("\n🧪 LLM-as-a-Judge Evaluation System Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Prompt generation
        test_evaluation_prompts()
        
        # Test 2: Configuration
        test_configuration()
        
        # Test 3: Threshold calculation
        test_threshold_calculation()
        
        # Test 4: Mock evaluation (must be last as it's async)
        test_mock_evaluation()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("\nNext steps:")
        print("1. Check ~/gtd-coach/data/evaluations/ for evaluation results")
        print("2. Run a full GTD review to test with real data")
        print("3. Monitor Langfuse dashboard for evaluation scores (if configured)")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()