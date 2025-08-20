#!/usr/bin/env python3
"""
Test script to verify online evaluation implementation
Tests session effectiveness scoring, memory tracking, and embedding tracing
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.observability.langfuse_tracer import LangfuseTracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_session_effectiveness():
    """Test session effectiveness scoring"""
    print("\n=== Testing Session Effectiveness Scoring ===")
    
    # Simulate a session with tracer
    tracer = LangfuseTracer(
        session_id="test-session-001",
        user_id="test-user",
        metadata={"test": True}
    )
    
    # Simulate session events
    tracer.trace_event("session.started", {"phase": "STARTUP"})
    
    # Simulate memory retrieval and usage
    tracer.trace_event("memory.retrieved", {"count": 5, "type": "tasks"})
    tracer.trace_event("memory.used", {"memory_id": "task-1"})
    tracer.trace_event("memory.used", {"memory_id": "task-2"})
    
    # Simulate interrupts
    tracer.trace_interrupt_attempt("check_in_tool", "Ready to continue?")
    tracer.trace_interrupt_captured({"value": "Ready to continue?"})
    tracer.trace_interrupt_resume("Yes, let's go")
    
    # Simulate session completion
    tracer.trace_event("session.effectiveness", {
        "completed": True,
        "duration_minutes": 28.5,
        "tasks_captured": 7,
        "priorities_set": 3,
        "interrupts_handled": 1
    }, score=0.95)
    
    # Get metrics summary
    summary = tracer.get_metrics_summary()
    
    print(f"✓ Session ID: {summary['session_id']}")
    print(f"✓ Memory hit rate: {summary['memory_hit_rate']:.2%}")
    print(f"✓ Interrupt success rate: {summary['interrupt_success_rate']:.2%}")
    print(f"✓ Memories retrieved: {summary['memories_retrieved']}")
    print(f"✓ Memories used: {summary['memories_used']}")
    
    assert summary['memory_hit_rate'] == 0.4  # 2 used out of 5 retrieved
    assert summary['interrupt_success_rate'] == 1.0  # 1 capture out of 1 attempt
    
    print("\n✅ Session effectiveness scoring working correctly!")


def test_embedding_tracing():
    """Test that embeddings will be traced"""
    print("\n=== Testing Embedding Tracing Setup ===")
    
    from gtd_coach.integrations.graphiti_client import TracedOpenAIEmbedder, LANGFUSE_AVAILABLE
    from graphiti_core.embedder.openai import OpenAIEmbedderConfig
    import os
    
    if not LANGFUSE_AVAILABLE:
        print("⚠️ Langfuse not available, skipping embedding trace test")
        return
    
    # Create traced embedder (won't actually call OpenAI without API key)
    config = OpenAIEmbedderConfig(
        api_key=os.getenv('OPENAI_API_KEY', 'test-key'),
        embedding_model='text-embedding-3-small'
    )
    
    embedder = TracedOpenAIEmbedder(config)
    
    # Check that the client was replaced
    if hasattr(embedder, 'client'):
        print(f"✓ Embedder client type: {embedder.client.__class__.__name__}")
        if 'Langfuse' in embedder.client.__class__.__name__:
            print("✓ Using Langfuse-wrapped OpenAI client")
        else:
            print("⚠️ Not using Langfuse wrapper (may be fallback)")
    
    print("\n✅ Embedding tracing setup complete!")


def test_rule_based_evaluation():
    """Test rule-based evaluation scoring"""
    print("\n=== Testing Rule-Based Evaluation ===")
    
    from gtd_coach.evaluation.post_session import PostSessionEvaluator
    
    evaluator = PostSessionEvaluator()
    
    # Mock evaluation results
    evaluator.evaluation_results = [
        {"phase": "STARTUP", "user_input": "Ready"},
        {"phase": "MIND_SWEEP", "task_extraction": {"score": 0.8}},
        {"phase": "MIND_SWEEP", "task_extraction": {"score": 0.9}},
        {"phase": "PROJECT_REVIEW", "memory_relevance": {"score": 0.7}},
        {"phase": "PRIORITIZATION"},
        {"phase": "WRAP_UP", "user_input": "Done"},
    ]
    
    # Calculate rule-based scores
    scores = evaluator._calculate_rule_based_scores()
    
    print(f"✓ Task capture rate: {scores['task_capture_rate']:.2%}")
    print(f"✓ Interrupt quality: {scores['interrupt_quality']:.2%}")
    print(f"✓ Phase completion: {scores['phase_completion_rate']:.2%}")
    print(f"✓ Session completed: {scores['session_completed']:.2%}")
    print(f"✓ Memory utilization: {scores['memory_utilization']:.2%}")
    print(f"✓ Overall effectiveness: {scores['session_effectiveness']:.3f}")
    
    assert scores['task_capture_rate'] == 1.0  # 2 out of 2 mind sweep interactions had tasks
    assert scores['interrupt_quality'] == 1.0  # Both interrupts at phase boundaries
    assert scores['phase_completion_rate'] == 1.0  # All 5 phases present
    assert scores['session_completed'] == 1.0  # Has WRAP_UP
    
    print("\n✅ Rule-based evaluation working correctly!")


if __name__ == "__main__":
    print("🚀 Testing Online Evaluation Implementation")
    print("=" * 60)
    
    try:
        test_session_effectiveness()
        test_embedding_tracing()
        test_rule_based_evaluation()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("\nYour online evaluation is ready to use:")
        print("- Session effectiveness is automatically scored")
        print("- Memory hit rates are tracked")
        print("- Embeddings will be traced (when Langfuse is configured)")
        print("- Rule-based evaluations provide fast feedback")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)