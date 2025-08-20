#!/usr/bin/env python3
"""
Test script to measure performance impact of Graphiti enhancements.
Tests dynamic prompts, memory augmentation, smart batching, and temporal decay.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.agent.runner import GTDAgentRunner


class PerformanceMetrics:
    """Track performance metrics for analysis"""
    
    def __init__(self):
        self.metrics = {
            'dynamic_prompt_generation': [],
            'memory_search': [],
            'batch_processing': [],
            'temporal_decay': [],
            'tool_augmentation': []
        }
    
    def record(self, category: str, duration: float, details: Dict[str, Any] = None):
        """Record a performance measurement"""
        self.metrics[category].append({
            'duration': duration,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        })
    
    def report(self):
        """Generate performance report"""
        print("\n" + "=" * 60)
        print("GRAPHITI ENHANCEMENT PERFORMANCE REPORT")
        print("=" * 60)
        
        for category, measurements in self.metrics.items():
            if measurements:
                durations = [m['duration'] for m in measurements]
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                
                print(f"\n{category.upper().replace('_', ' ')}:")
                print(f"  Measurements: {len(measurements)}")
                print(f"  Average: {avg_duration:.3f}s")
                print(f"  Min: {min_duration:.3f}s")
                print(f"  Max: {max_duration:.3f}s")
                
                # Print details of slowest operation
                if max_duration > 1.0:
                    slowest = max(measurements, key=lambda x: x['duration'])
                    print(f"  ⚠️ Slowest operation: {slowest['duration']:.3f}s")
                    if slowest['details']:
                        print(f"     Details: {slowest['details']}")
        
        print("\n" + "=" * 60)


async def test_dynamic_prompt_generation(metrics: PerformanceMetrics):
    """Test performance of dynamic system message generation"""
    print("\n📝 Testing Dynamic Prompt Generation...")
    
    # Mock the GraphitiMemory to simulate user facts
    with patch('gtd_coach.agent.runner.GraphitiMemory') as MockMemory:
        mock_memory = AsyncMock()
        mock_memory.is_configured.return_value = True
        mock_memory.search_with_context.return_value = [
            MagicMock(fact="User prefers morning reviews", score=0.9),
            MagicMock(fact="User struggles with focus after 3pm", score=0.8),
            MagicMock(fact="User works best with 25-minute focus blocks", score=0.85),
            MagicMock(fact="User has ADHD inattentive type", score=0.95),
            MagicMock(fact="User responds well to gentle accountability", score=0.7)
        ]
        MockMemory.return_value = mock_memory
        
        runner = GTDAgentRunner(user_id="test_user")
        runner.memory = mock_memory
        
        # Test cold cache (first fetch)
        start = time.perf_counter()
        user_facts = await runner.get_user_facts_cached()
        cold_duration = time.perf_counter() - start
        metrics.record('dynamic_prompt_generation', cold_duration, 
                      {'type': 'cold_cache', 'facts_count': len(user_facts)})
        print(f"  ✓ Cold cache fetch: {cold_duration:.3f}s for {len(user_facts)} facts")
        
        # Test warm cache (subsequent fetches)
        for i in range(5):
            start = time.perf_counter()
            user_facts = await runner.get_user_facts_cached()
            warm_duration = time.perf_counter() - start
            metrics.record('dynamic_prompt_generation', warm_duration, 
                          {'type': 'warm_cache', 'facts_count': len(user_facts)})
        
        print(f"  ✓ Warm cache fetches: avg {sum([m['duration'] for m in metrics.metrics['dynamic_prompt_generation'][1:6]])/5:.3f}s")
        
        # Test cache expiry
        runner.cache_time = time.time() - (25 * 3600)  # Simulate 25 hours old cache
        start = time.perf_counter()
        user_facts = await runner.get_user_facts_cached()
        expired_duration = time.perf_counter() - start
        metrics.record('dynamic_prompt_generation', expired_duration, 
                      {'type': 'expired_cache', 'facts_count': len(user_facts)})
        print(f"  ✓ Expired cache refresh: {expired_duration:.3f}s")


async def test_memory_augmented_tools(metrics: PerformanceMetrics):
    """Test performance of memory-augmented tool execution"""
    print("\n🔧 Testing Memory-Augmented Tools...")
    
    from gtd_coach.agent.tools.capture import capture_item_tool
    from gtd_coach.agent.tools.adaptive import detect_patterns_tool
    
    # Mock state with captures
    state = {
        'session_id': 'test_session',
        'captures': [
            {'content': f'Task {i}'} for i in range(10)
        ],
        'stress_level': 'high',
        'adhd_patterns': ['overwhelm', 'task_switching']
    }
    
    # Mock GraphitiMemory
    with patch('gtd_coach.agent.tools.capture.GraphitiMemory') as MockMemory:
        mock_memory = MagicMock()
        mock_memory.is_configured.return_value = True
        
        # Mock search results with categorization hints
        async def mock_search(query, num_results):
            await asyncio.sleep(0.1)  # Simulate network latency
            return [
                MagicMock(fact="Task captured: Review budget (category: review)", score=0.8),
                MagicMock(fact="Task captured: Email client (category: communication)", score=0.7)
            ]
        
        mock_memory.search_with_context = mock_search
        MockMemory.return_value = mock_memory
        
        # Test capture tool with memory augmentation
        start = time.perf_counter()
        result = capture_item_tool.invoke({
            'content': 'Review quarterly report',
            'source': 'brain_dump',
            'state': state
        })
        capture_duration = time.perf_counter() - start
        metrics.record('tool_augmentation', capture_duration, 
                      {'tool': 'capture_item', 'with_memory': True})
        print(f"  ✓ Capture tool with memory: {capture_duration:.3f}s")
        
        # Test without enough captures (no memory search)
        state_small = {**state, 'captures': [{'content': 'Task 1'}]}
        start = time.perf_counter()
        result = capture_item_tool.invoke({
            'content': 'Small task',
            'source': 'brain_dump',
            'state': state_small
        })
        no_memory_duration = time.perf_counter() - start
        metrics.record('tool_augmentation', no_memory_duration, 
                      {'tool': 'capture_item', 'with_memory': False})
        print(f"  ✓ Capture tool without memory: {no_memory_duration:.3f}s")
        
        # Calculate overhead
        overhead = capture_duration - no_memory_duration
        print(f"  📊 Memory augmentation overhead: {overhead:.3f}s")


async def test_smart_batching(metrics: PerformanceMetrics):
    """Test performance of smart batching for episode processing"""
    print("\n📦 Testing Smart Batching...")
    
    memory = GraphitiMemory('test_session', enable_json_backup=False)
    
    # Mock the graphiti client
    mock_client = AsyncMock()
    mock_client.add_episode = AsyncMock()
    memory.graphiti_client = mock_client
    
    # Add different types of episodes to test grouping
    episodes_to_batch = [
        {'type': 'interaction', 'data': {'content': f'Message {i}'}} 
        for i in range(15)
    ] + [
        {'type': 'mindsweep_capture', 'data': {'items': [f'Item {i}']}} 
        for i in range(8)
    ] + [
        {'type': 'behavior_pattern', 'data': {'pattern': f'Pattern {i}'}} 
        for i in range(5)
    ]
    
    # Queue episodes
    for episode in episodes_to_batch:
        memory.pending_graphiti_episodes.append({
            **episode,
            'timestamp': datetime.now().isoformat(),
            'session_id': 'test',
            'group_id': 'test_group'
        })
    
    # Test batch processing
    start = time.perf_counter()
    await memory._flush_graphiti_batch()
    batch_duration = time.perf_counter() - start
    
    metrics.record('batch_processing', batch_duration, 
                  {'total_episodes': len(episodes_to_batch),
                   'types': ['interaction', 'mindsweep_capture', 'behavior_pattern']})
    
    print(f"  ✓ Processed {len(episodes_to_batch)} episodes in {batch_duration:.3f}s")
    print(f"  ✓ Episodes per second: {len(episodes_to_batch)/batch_duration:.1f}")
    
    # Verify grouping worked
    call_count = mock_client.add_episode.call_count
    print(f"  ✓ API calls made: {call_count} (grouped from {len(episodes_to_batch)} episodes)")
    
    # Test with trivial filtering
    memory.skip_trivial = True
    memory.pending_graphiti_episodes = [
        {'type': 'interaction', 'data': {'content': 'ok'}, 
         'timestamp': datetime.now().isoformat(), 'session_id': 'test', 'group_id': 'test'},
        {'type': 'interaction', 'data': {'content': 'thanks'}, 
         'timestamp': datetime.now().isoformat(), 'session_id': 'test', 'group_id': 'test'},
        {'type': 'interaction', 'data': {'content': 'Important message here'}, 
         'timestamp': datetime.now().isoformat(), 'session_id': 'test', 'group_id': 'test'}
    ]
    
    mock_client.add_episode.reset_mock()
    start = time.perf_counter()
    await memory._flush_graphiti_batch()
    filter_duration = time.perf_counter() - start
    
    metrics.record('batch_processing', filter_duration, 
                  {'with_filtering': True, 'filtered_count': 2})
    
    print(f"  ✓ Filtered batch processing: {filter_duration:.3f}s")
    print(f"  ✓ Trivial episodes filtered: 2 out of 3")


async def test_temporal_decay(metrics: PerformanceMetrics):
    """Test performance and accuracy of temporal decay scoring"""
    print("\n⏰ Testing Temporal Decay...")
    
    memory = GraphitiMemory('test_session')
    
    # Create mock search results with different ages
    current_time = datetime.now(timezone.utc)
    mock_results = [
        MagicMock(
            fact="Recent memory from today",
            score=0.9,
            timestamp=(current_time - timedelta(days=0)).isoformat()
        ),
        MagicMock(
            fact="Memory from last week",
            score=0.9,
            timestamp=(current_time - timedelta(days=7)).isoformat()
        ),
        MagicMock(
            fact="Memory from last month",
            score=0.9,
            timestamp=(current_time - timedelta(days=30)).isoformat()
        ),
        MagicMock(
            fact="Old memory from 3 months ago",
            score=0.9,
            timestamp=(current_time - timedelta(days=90)).isoformat()
        )
    ]
    
    # Test decay application
    start = time.perf_counter()
    results_with_decay = memory._apply_temporal_decay(mock_results)
    decay_duration = time.perf_counter() - start
    
    metrics.record('temporal_decay', decay_duration, 
                  {'results_count': len(mock_results)})
    
    print(f"  ✓ Applied decay to {len(mock_results)} results in {decay_duration:.3f}s")
    
    # Verify decay factors
    for result in results_with_decay:
        print(f"  📊 Age: {result.age_days}d, Decay: {result.decay_factor:.3f}, "
              f"Score: {result.score:.3f} → {result.decayed_score:.3f}")
    
    # Test with different decay rates
    for decay_rate in [0.01, 0.05, 0.1]:
        os.environ['GRAPHITI_DECAY_RATE'] = str(decay_rate)
        start = time.perf_counter()
        memory._apply_temporal_decay(mock_results.copy())
        rate_duration = time.perf_counter() - start
        metrics.record('temporal_decay', rate_duration, 
                      {'decay_rate': decay_rate})
    
    print(f"  ✓ Tested multiple decay rates: 0.01, 0.05, 0.1")
    
    # Test sorting by decayed score
    start = time.perf_counter()
    sorted_results = sorted(results_with_decay, 
                           key=lambda r: r.decayed_score, 
                           reverse=True)
    sort_duration = time.perf_counter() - start
    
    print(f"  ✓ Sorting by decayed score: {sort_duration:.3f}s")
    print(f"  ✓ Top result: '{sorted_results[0].fact[:30]}...' (score: {sorted_results[0].decayed_score:.3f})")


async def main():
    """Run all performance tests"""
    print("\n🚀 Starting Graphiti Enhancement Performance Tests")
    print("=" * 60)
    
    metrics = PerformanceMetrics()
    
    try:
        # Run all tests
        await test_dynamic_prompt_generation(metrics)
        await test_memory_augmented_tools(metrics)
        await test_smart_batching(metrics)
        await test_temporal_decay(metrics)
        
        # Generate report
        metrics.report()
        
        # Performance recommendations
        print("\n💡 PERFORMANCE RECOMMENDATIONS:")
        print("-" * 40)
        
        # Check dynamic prompt performance
        dynamic_metrics = metrics.metrics['dynamic_prompt_generation']
        if dynamic_metrics:
            avg_cold = sum(m['duration'] for m in dynamic_metrics if m['details'].get('type') == 'cold_cache') / \
                      len([m for m in dynamic_metrics if m['details'].get('type') == 'cold_cache'])
            if avg_cold > 2.0:
                print("⚠️ Cold cache fetch is slow. Consider:")
                print("  - Reducing number of facts fetched")
                print("  - Pre-warming cache at startup")
        
        # Check memory augmentation overhead
        tool_metrics = metrics.metrics['tool_augmentation']
        if tool_metrics:
            with_memory = [m for m in tool_metrics if m['details'].get('with_memory')]
            without_memory = [m for m in tool_metrics if not m['details'].get('with_memory')]
            if with_memory and without_memory:
                overhead = sum(m['duration'] for m in with_memory) / len(with_memory) - \
                          sum(m['duration'] for m in without_memory) / len(without_memory)
                if overhead > 0.5:
                    print(f"⚠️ Memory augmentation adds {overhead:.2f}s overhead. Consider:")
                    print("  - Reducing search result count")
                    print("  - Caching frequent queries")
        
        # Check batch processing efficiency
        batch_metrics = metrics.metrics['batch_processing']
        if batch_metrics:
            for m in batch_metrics:
                if 'total_episodes' in m['details']:
                    eps = m['details']['total_episodes'] / m['duration']
                    if eps < 10:
                        print(f"⚠️ Batch processing is slow ({eps:.1f} episodes/sec). Consider:")
                        print("  - Increasing sub-batch size")
                        print("  - Reducing API call overhead")
        
        print("\n✅ Performance testing complete!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())