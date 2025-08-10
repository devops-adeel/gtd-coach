#!/usr/bin/env python3
"""
Performance Benchmarking for GTD Operations in Graphiti
Tests latency requirements for critical GTD workflows
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gtd_coach.integrations.graphiti_client import GraphitiClient
from graphiti_core.nodes import EpisodeType
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GTDBenchmark:
    """Benchmark GTD operations for performance"""
    
    # Target latencies (in seconds)
    TARGETS = {
        'episode_creation': 0.100,  # 100ms for real-time capture
        'mindsweep_search': 0.200,  # 200ms for review flow
        'priority_retrieval': 0.150,  # 150ms for quick decisions
        'pattern_detection': 0.500,  # 500ms (can be async)
        'context_query': 0.200,  # 200ms for context switching
        'project_search': 0.250,  # 250ms for project review
    }
    
    def __init__(self, iterations: int = 10):
        self.client = None
        self.iterations = iterations
        self.results = {}
        self.test_group_id = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def initialize(self):
        """Initialize Graphiti client"""
        try:
            self.client = await GraphitiClient.get_instance()
            logger.info("✅ Initialized benchmark client")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def benchmark_episode_creation(self) -> Dict[str, Any]:
        """Benchmark episode creation (critical for real-time capture)"""
        test_name = "episode_creation"
        timings = []
        
        for i in range(self.iterations):
            episode_data = {
                "name": f"benchmark_episode_{i}",
                "episode_body": f"Urgent: Call doctor @phone #{i}",
                "source": EpisodeType.text,
                "source_description": "Benchmark test",
                "group_id": self.test_group_id,
                "reference_time": datetime.now(timezone.utc)
            }
            
            start = time.perf_counter()
            try:
                await self.client.add_episode(**episode_data)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Episode creation failed: {e}")
                timings.append(float('inf'))
            
            # Small delay between iterations
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    async def benchmark_mindsweep_search(self) -> Dict[str, Any]:
        """Benchmark mind sweep item search"""
        test_name = "mindsweep_search"
        
        # First, add some mindsweep data
        mindsweep_items = [
            "Fix leaking faucet",
            "Plan vacation",
            "Call mom",
            "Review portfolio",
            "Learn Spanish"
        ]
        
        for item in mindsweep_items:
            await self.client.add_episode(
                name=f"mindsweep_{item[:10]}",
                episode_body=item,
                source=EpisodeType.text,
                source_description="Mindsweep benchmark",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
        
        # Now benchmark searches
        timings = []
        queries = ["faucet", "vacation", "portfolio", "spanish", "call"]
        
        for i in range(self.iterations):
            query = queries[i % len(queries)]
            
            start = time.perf_counter()
            try:
                results = await self.client.search(query, num_results=5)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Search failed: {e}")
                timings.append(float('inf'))
            
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    async def benchmark_priority_retrieval(self) -> Dict[str, Any]:
        """Benchmark priority-based retrieval"""
        test_name = "priority_retrieval"
        
        # Add prioritized items
        priorities = ["A", "B", "C"]
        for priority in priorities:
            for i in range(3):
                await self.client.add_episode(
                    name=f"priority_{priority}_{i}",
                    episode_body=f"Task with priority {priority}: Item {i}",
                    source=EpisodeType.text,
                    source_description="Priority benchmark",
                    group_id=self.test_group_id,
                    reference_time=datetime.now(timezone.utc)
                )
        
        # Benchmark priority searches
        timings = []
        
        for i in range(self.iterations):
            priority = priorities[i % len(priorities)]
            
            start = time.perf_counter()
            try:
                results = await self.client.search(f"priority {priority}", num_results=10)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Priority search failed: {e}")
                timings.append(float('inf'))
            
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    async def benchmark_pattern_detection(self) -> Dict[str, Any]:
        """Benchmark ADHD pattern detection (can be async)"""
        test_name = "pattern_detection"
        
        # Add pattern data
        pattern_data = {
            "pattern_type": "task_switch",
            "severity": "high",
            "context_switches": 7,
            "duration_seconds": 45
        }
        
        timings = []
        
        for i in range(self.iterations):
            pattern_data["context_switches"] = 5 + (i % 5)
            
            start = time.perf_counter()
            try:
                await self.client.add_episode(
                    name=f"pattern_{i}",
                    episode_body=json.dumps(pattern_data),
                    source=EpisodeType.json,
                    source_description="Pattern benchmark",
                    group_id=self.test_group_id,
                    reference_time=datetime.now(timezone.utc)
                )
                
                # Search for pattern
                results = await self.client.search("task switch pattern", num_results=5)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Pattern detection failed: {e}")
                timings.append(float('inf'))
            
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    async def benchmark_context_query(self) -> Dict[str, Any]:
        """Benchmark context-based queries"""
        test_name = "context_query"
        
        # Add context-specific tasks
        contexts = ["@home", "@office", "@computer", "@phone", "@errands"]
        for context in contexts:
            for i in range(2):
                await self.client.add_episode(
                    name=f"task_{context}_{i}",
                    episode_body=f"Task to do {context}: Item {i}",
                    source=EpisodeType.text,
                    source_description="Context benchmark",
                    group_id=self.test_group_id,
                    reference_time=datetime.now(timezone.utc)
                )
        
        # Benchmark context queries
        timings = []
        
        for i in range(self.iterations):
            context = contexts[i % len(contexts)]
            
            start = time.perf_counter()
            try:
                results = await self.client.search(f"{context} tasks", num_results=10)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Context query failed: {e}")
                timings.append(float('inf'))
            
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    async def benchmark_project_search(self) -> Dict[str, Any]:
        """Benchmark project-related searches"""
        test_name = "project_search"
        
        # Add project data
        projects = [
            {"name": "Website Redesign", "next_action": "Create mockups"},
            {"name": "Budget Planning", "next_action": "Gather receipts"},
            {"name": "Home Renovation", "next_action": "Get contractor quotes"},
        ]
        
        for project in projects:
            await self.client.add_episode(
                name=f"project_{project['name'][:10]}",
                episode_body=json.dumps(project),
                source=EpisodeType.json,
                source_description="Project benchmark",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
        
        # Benchmark project searches
        timings = []
        queries = ["Website", "Budget", "Renovation", "next action", "project"]
        
        for i in range(self.iterations):
            query = queries[i % len(queries)]
            
            start = time.perf_counter()
            try:
                results = await self.client.search(query, num_results=10)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
            except Exception as e:
                logger.error(f"Project search failed: {e}")
                timings.append(float('inf'))
            
            await asyncio.sleep(0.05)
        
        return self._analyze_timings(test_name, timings)
    
    def _analyze_timings(self, test_name: str, timings: List[float]) -> Dict[str, Any]:
        """Analyze timing results"""
        # Remove any inf values
        valid_timings = [t for t in timings if t != float('inf')]
        
        if not valid_timings:
            return {
                'name': test_name,
                'passed': False,
                'error': 'All operations failed'
            }
        
        target = self.TARGETS[test_name]
        mean_time = statistics.mean(valid_timings)
        median_time = statistics.median(valid_timings)
        min_time = min(valid_timings)
        max_time = max(valid_timings)
        p95 = sorted(valid_timings)[int(len(valid_timings) * 0.95)] if len(valid_timings) > 1 else max_time
        
        # Pass if 95th percentile is under target
        passed = p95 <= target
        
        return {
            'name': test_name,
            'passed': passed,
            'target': target,
            'mean': mean_time,
            'median': median_time,
            'min': min_time,
            'max': max_time,
            'p95': p95,
            'samples': len(valid_timings),
            'failures': len(timings) - len(valid_timings)
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        print("\n" + "="*60)
        print("GTD PERFORMANCE BENCHMARK SUITE")
        print("="*60)
        print(f"Iterations per test: {self.iterations}")
        print(f"Test group: {self.test_group_id}")
        
        if not await self.initialize():
            print("❌ Failed to initialize benchmark suite")
            return {'success': False}
        
        # Warm up the connection
        print("\n🔥 Warming up connection...")
        for _ in range(3):
            await self.client.search("warmup", num_results=1)
            await asyncio.sleep(0.1)
        
        # Run benchmarks
        benchmarks = [
            ("Episode Creation", self.benchmark_episode_creation),
            ("Mind Sweep Search", self.benchmark_mindsweep_search),
            ("Priority Retrieval", self.benchmark_priority_retrieval),
            ("Pattern Detection", self.benchmark_pattern_detection),
            ("Context Query", self.benchmark_context_query),
            ("Project Search", self.benchmark_project_search),
        ]
        
        results = []
        passed_count = 0
        failed_count = 0
        
        for bench_name, bench_func in benchmarks:
            print(f"\n📊 Running: {bench_name}")
            result = await bench_func()
            results.append(result)
            
            if result.get('passed'):
                passed_count += 1
                status = "✅ PASS"
            else:
                failed_count += 1
                status = "❌ FAIL"
            
            print(f"{status}: {bench_name}")
            print(f"  Target: {result.get('target', 'N/A'):.3f}s")
            print(f"  Mean: {result.get('mean', 0):.3f}s")
            print(f"  Median: {result.get('median', 0):.3f}s")
            print(f"  P95: {result.get('p95', 0):.3f}s")
            print(f"  Range: {result.get('min', 0):.3f}s - {result.get('max', 0):.3f}s")
            
            if result.get('failures', 0) > 0:
                print(f"  ⚠️ Failures: {result['failures']}")
        
        # Summary
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        print(f"✅ Passed: {passed_count}/{len(benchmarks)}")
        print(f"❌ Failed: {failed_count}/{len(benchmarks)}")
        
        # Performance grade
        if passed_count == len(benchmarks):
            grade = "A - Excellent"
        elif passed_count >= len(benchmarks) * 0.8:
            grade = "B - Good"
        elif passed_count >= len(benchmarks) * 0.6:
            grade = "C - Acceptable"
        else:
            grade = "F - Needs Improvement"
        
        print(f"\n🏆 Performance Grade: {grade}")
        
        # Critical operations check
        critical_ops = ['episode_creation', 'mindsweep_search', 'priority_retrieval']
        critical_results = [r for r in results if r['name'] in critical_ops]
        critical_passed = all(r.get('passed') for r in critical_results)
        
        if not critical_passed:
            print("\n⚠️ CRITICAL: Some essential GTD operations are too slow:")
            for r in critical_results:
                if not r.get('passed'):
                    print(f"  - {r['name']}: {r.get('p95', 0):.3f}s (target: {r.get('target'):.3f}s)")
        
        return {
            'success': True,
            'passed': passed_count,
            'failed': failed_count,
            'grade': grade,
            'results': results
        }


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark GTD operations')
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of iterations per test (default: 10)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    benchmark = GTDBenchmark(iterations=args.iterations)
    result = await benchmark.run_all_benchmarks()
    
    return 0 if result['success'] and result['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)