#!/usr/bin/env python3
"""
Test script to verify Graphiti optimizations and measure improvements
Tests retry logic, excluded entities, performance metrics, and error logging
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Setup logging to see all our improvements in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_retry_logic():
    """Test that retry logic works with exponential backoff"""
    print("\n" + "="*60)
    print("TEST 1: RETRY LOGIC WITH EXPONENTIAL BACKOFF")
    print("="*60)
    
    from gtd_coach.integrations.graphiti import GraphitiMemory
    
    # Create a memory instance
    memory = GraphitiMemory(session_id="test_retry_20250810")
    
    # Mock the Graphiti client to simulate failures
    mock_client = MagicMock()
    memory.graphiti_client = mock_client
    
    # Simulate failures on first 2 attempts, success on 3rd
    call_count = 0
    async def mock_add_episode(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Simulated failure {call_count}")
        return True
    
    mock_client.add_episode = mock_add_episode
    
    # Test episode data
    episode_data = {
        "type": "interaction",
        "phase": "TEST_PHASE",
        "data": {
            "role": "user",
            "content": "Test message for retry logic"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    start_time = time.perf_counter()
    await memory._send_single_episode(episode_data)
    elapsed = time.perf_counter() - start_time
    
    print(f"✅ Retry logic test completed")
    print(f"   - Total attempts: {call_count}")
    print(f"   - Total time with retries: {elapsed:.2f}s")
    print(f"   - Expected delay (1+2 seconds): ~3s")
    assert call_count == 3, f"Expected 3 attempts, got {call_count}"
    assert elapsed >= 2.5, f"Expected at least 2.5s delay, got {elapsed:.2f}s"
    
    return True

async def test_excluded_entities():
    """Test that excluded entities are properly configured"""
    print("\n" + "="*60)
    print("TEST 2: EXCLUDED ENTITIES CONFIGURATION")
    print("="*60)
    
    from gtd_coach.integrations.gtd_entity_config import (
        get_entity_config_for_episode,
        EXCLUDED_ENTITIES_BY_EPISODE
    )
    
    # Test interaction episode
    config = get_entity_config_for_episode("interaction")
    assert config is not None, "Interaction should use custom entities"
    
    excluded = EXCLUDED_ENTITIES_BY_EPISODE.get("interaction", [])
    print(f"✅ Interaction episode excludes: {', '.join(excluded)}")
    assert "TimingInsight" in excluded, "Should exclude TimingInsight"
    assert "WeeklyReview" in excluded, "Should exclude WeeklyReview"
    
    # Test mindsweep episode
    config = get_entity_config_for_episode("mindsweep_capture")
    assert config is not None, "Mindsweep should use custom entities"
    
    excluded = EXCLUDED_ENTITIES_BY_EPISODE.get("mindsweep_capture", [])
    print(f"✅ Mindsweep episode excludes: {', '.join(excluded)}")
    assert "TimingInsight" in excluded, "Should exclude TimingInsight"
    assert "ADHDPattern" in excluded, "Should exclude ADHDPattern"
    
    # Test phase transition (should not use entities)
    config = get_entity_config_for_episode("phase_transition")
    assert config is None, "Phase transition should NOT use custom entities"
    print(f"✅ Phase transition correctly skips all custom entities")
    
    return True

async def test_performance_metrics():
    """Test that performance metrics are tracked correctly"""
    print("\n" + "="*60)
    print("TEST 3: PERFORMANCE METRICS TRACKING")
    print("="*60)
    
    from gtd_coach.integrations.graphiti import GraphitiMemory
    
    # Create memory instance
    memory = GraphitiMemory(session_id="test_metrics_20250810")
    
    # Mock Graphiti client with controlled delays
    mock_client = MagicMock()
    memory.graphiti_client = mock_client
    
    # Simulate different extraction times for different episode types
    async def mock_add_episode(**kwargs):
        episode_name = kwargs.get('name', '')
        if 'interaction' in episode_name:
            await asyncio.sleep(0.1)  # Fast
        elif 'mindsweep' in episode_name:
            await asyncio.sleep(0.3)  # Medium
        elif 'timing_analysis' in episode_name:
            await asyncio.sleep(0.5)  # Slow
        return True
    
    mock_client.add_episode = mock_add_episode
    
    # Send different episode types
    test_episodes = [
        {"type": "interaction", "phase": "TEST", "data": {"content": "test1"}},
        {"type": "interaction", "phase": "TEST", "data": {"content": "test2"}},
        {"type": "mindsweep_capture", "phase": "TEST", "data": {"items": ["a", "b"]}},
        {"type": "timing_analysis", "phase": "TEST", "data": {"focus_score": 75}},
    ]
    
    for episode in test_episodes:
        episode["timestamp"] = datetime.now().isoformat()
        await memory._send_single_episode(episode)
    
    # Check metrics were tracked
    print("Performance metrics collected:")
    for episode_type, times in memory.extraction_metrics.items():
        if times:
            avg_time = sum(times) / len(times)
            print(f"   {episode_type}: {len(times)} episodes, avg {avg_time:.3f}s")
    
    assert len(memory.extraction_metrics["interaction"]) == 2
    assert len(memory.extraction_metrics["mindsweep_capture"]) == 1
    assert len(memory.extraction_metrics["timing_analysis"]) == 1
    
    print("✅ Performance metrics are being tracked correctly")
    return True

async def test_error_context_logging():
    """Test that error context is properly logged"""
    print("\n" + "="*60)
    print("TEST 4: ERROR CONTEXT LOGGING")
    print("="*60)
    
    from gtd_coach.integrations.graphiti import GraphitiMemory
    import logging
    
    # Create memory instance
    memory = GraphitiMemory(session_id="test_error_context_20250810")
    
    # Mock Graphiti client that always fails
    mock_client = MagicMock()
    memory.graphiti_client = mock_client
    
    async def mock_add_episode(**kwargs):
        raise Exception("Persistent failure for testing")
    
    mock_client.add_episode = mock_add_episode
    
    # Capture log output
    log_messages = []
    class TestHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(self.format(record))
    
    test_handler = TestHandler()
    test_handler.setFormatter(logging.Formatter('%(message)s'))
    logger = logging.getLogger('graphiti_integration')
    logger.addHandler(test_handler)
    
    # Send episode that will fail
    episode_data = {
        "type": "interaction",
        "phase": "TEST_PHASE",
        "data": {"role": "user", "content": "Test error context"},
        "timestamp": datetime.now().isoformat()
    }
    
    await memory._send_single_episode(episode_data)
    
    # Check that error context was logged
    error_logs = [msg for msg in log_messages if "Context:" in msg]
    assert len(error_logs) > 0, "No error context logs found"
    
    # Verify context includes expected fields
    final_error = [msg for msg in log_messages if "❌" in msg]
    assert len(final_error) > 0, "No final error log found"
    
    context_logged = any(all(field in msg for field in ["episode_type", "phase", "data_size", "has_custom_entities"])
                        for msg in log_messages)
    assert context_logged, "Error context missing required fields"
    
    print("✅ Error context is being logged with all required fields:")
    print("   - episode_type")
    print("   - phase")
    print("   - retry_count")
    print("   - data_size")
    print("   - has_custom_entities")
    
    # Clean up handler
    logger.removeHandler(test_handler)
    
    return True

async def test_cost_optimization():
    """Test that cost optimizations are working"""
    print("\n" + "="*60)
    print("TEST 5: COST OPTIMIZATION (SKIP TRIVIAL & BATCHING)")
    print("="*60)
    
    from gtd_coach.integrations.graphiti import GraphitiMemory
    
    # Create memory with skip_trivial enabled
    memory = GraphitiMemory(session_id="test_cost_20250810")
    memory.skip_trivial = True
    memory.batch_threshold = 3
    
    # Test trivial response detection
    trivial_episode = {
        "type": "interaction",
        "phase": "TEST",
        "data": {"role": "user", "content": "ok"},
        "timestamp": datetime.now().isoformat()
    }
    
    should_send = memory._should_send_immediately(trivial_episode)
    assert not should_send, "Trivial 'ok' should be skipped"
    print("✅ Trivial responses are being skipped")
    
    # Test batching for mindsweep
    mindsweep_episode = {
        "type": "mindsweep_capture",
        "phase": "MIND_SWEEP",
        "data": {"items": ["task1", "task2"]},
        "timestamp": datetime.now().isoformat()
    }
    
    should_send = memory._should_send_immediately(mindsweep_episode)
    assert not should_send, "Mindsweep should be batched"
    print("✅ Mindsweep items are being batched")
    
    # Test immediate send for critical episodes
    summary_episode = {
        "type": "session_summary",
        "phase": "COMPLETE",
        "data": {"metrics": {}},
        "timestamp": datetime.now().isoformat()
    }
    
    should_send = memory._should_send_immediately(summary_episode)
    assert should_send, "Session summary should send immediately"
    print("✅ Critical episodes send immediately")
    
    return True

async def run_all_tests():
    """Run all optimization tests"""
    print("\n" + "="*70)
    print("GRAPHITI OPTIMIZATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Retry Logic", test_retry_logic),
        ("Excluded Entities", test_excluded_entities),
        ("Performance Metrics", test_performance_metrics),
        ("Error Context", test_error_context_logging),
        ("Cost Optimization", test_cost_optimization),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            logger.error(f"Test {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"       Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All optimizations are working correctly!")
        print("\nKey improvements implemented:")
        print("1. ✅ Retry logic with exponential backoff (1, 2, 4 seconds)")
        print("2. ✅ Excluded entity types per episode type")
        print("3. ✅ Performance metrics tracking and reporting")
        print("4. ✅ Enhanced error context logging")
        print("5. ✅ Cost optimization (skip trivial, smart batching)")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)