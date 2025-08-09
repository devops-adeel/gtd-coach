#!/usr/bin/env python3
"""
Test script for Timing + Graphiti integration
Tests the complete flow of timing analysis, pattern detection, and memory storage
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import all integration modules
from timing_integration import TimingAPI
from timing_comparison import compare_time_with_priorities, format_comparison_report
from adhd_patterns import ADHDPatternDetector
from graphiti_integration import GraphitiMemory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_timing_analysis():
    """Test timing API analysis with context switch detection"""
    print("\n" + "="*50)
    print("1. TESTING TIMING ANALYSIS")
    print("="*50)
    
    api = TimingAPI()
    
    if not api.is_configured():
        print("❌ Timing API not configured - using mock data")
        return None
    
    print("✓ Timing API configured")
    
    # Test fetching time entries
    print("\n📊 Fetching time entries...")
    entries = await api.fetch_time_entries_async(max_entries=50)
    
    if entries:
        print(f"✓ Fetched {len(entries)} time entries")
        
        # Test context switch detection
        print("\n🔄 Analyzing context switches...")
        switch_analysis = api.detect_context_switches(entries)
        
        print(f"  • Total switches: {switch_analysis['total_switches']}")
        print(f"  • Switches per hour: {switch_analysis['switches_per_hour']:.2f}")
        print(f"  • Focus periods: {len(switch_analysis['focus_periods'])}")
        print(f"  • Scatter periods: {len(switch_analysis['scatter_periods'])}")
        
        # Test focus metrics
        print("\n🎯 Calculating focus metrics...")
        focus_metrics = api.calculate_focus_metrics(switch_analysis)
        
        print(f"  • Focus score: {focus_metrics['focus_score']}/100")
        print(f"  • Interpretation: {focus_metrics['interpretation']}")
        
        # Get full analysis
        full_analysis = await api.analyze_timing_patterns_async()
        return full_analysis
    else:
        print("❌ No time entries fetched")
        return None


async def test_adhd_pattern_detection(timing_data):
    """Test ADHD pattern detection from timing data"""
    print("\n" + "="*50)
    print("2. TESTING ADHD PATTERN DETECTION")
    print("="*50)
    
    detector = ADHDPatternDetector()
    
    if not timing_data:
        print("❌ No timing data available for pattern detection")
        return None
    
    # Analyze timing patterns
    print("\n🧠 Analyzing ADHD patterns...")
    adhd_analysis = detector.analyze_timing_switches(timing_data)
    
    print(f"  • Patterns detected: {adhd_analysis['patterns_detected']}")
    print(f"  • Focus profile: {adhd_analysis['focus_profile']}")
    
    if adhd_analysis['adhd_indicators']:
        print("\n📋 ADHD Indicators:")
        for indicator in adhd_analysis['adhd_indicators']:
            severity_emoji = "🔴" if indicator['severity'] == 'high' else "🟡" if indicator['severity'] == 'medium' else "🟢"
            print(f"  {severity_emoji} {indicator['message']}")
    
    if adhd_analysis['recommendations']:
        print("\n💡 Recommendations:")
        for rec in adhd_analysis['recommendations']:
            print(f"  • {rec}")
    
    return adhd_analysis


async def test_priority_comparison(timing_data):
    """Test comparing timing data with mock GTD priorities"""
    print("\n" + "="*50)
    print("3. TESTING PRIORITY COMPARISON")
    print("="*50)
    
    # Create mock priorities for testing
    mock_priorities = [
        {"task": "Complete project documentation", "priority": "A"},
        {"task": "Review code changes", "priority": "A"},
        {"task": "Email client updates", "priority": "B"},
        {"task": "Learn new framework", "priority": "B"},
        {"task": "Organize desktop files", "priority": "C"}
    ]
    
    if not timing_data or not timing_data.get('projects'):
        print("❌ No timing projects for comparison")
        return None
    
    print(f"\n📊 Comparing {len(timing_data['projects'])} projects with {len(mock_priorities)} priorities...")
    
    comparison = compare_time_with_priorities(
        timing_data['projects'],
        mock_priorities,
        timing_data
    )
    
    # Format and display report
    report = format_comparison_report(comparison)
    print(report)
    
    return comparison


async def test_graphiti_memory_storage(timing_data, adhd_analysis):
    """Test storing timing analysis in Graphiti memory"""
    print("\n" + "="*50)
    print("4. TESTING GRAPHITI MEMORY STORAGE")
    print("="*50)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    memory = GraphitiMemory(session_id)
    memory.current_phase = "TEST"  # Set current phase for testing
    
    if not timing_data:
        print("❌ No timing data to store")
        return
    
    print(f"\n💾 Storing timing analysis for session {session_id}...")
    
    # Add timing analysis to memory
    await memory.add_timing_analysis(timing_data, adhd_analysis or {})
    
    # Add correlation insights if available
    if adhd_analysis:
        # Create mock mindsweep for correlation testing
        mock_mindsweep = {
            'coherence_score': 0.6,
            'topic_switches': 5
        }
        
        detector = ADHDPatternDetector()
        correlation = detector.correlate_timing_with_mindsweep(timing_data, mock_mindsweep)
        
        await memory.add_correlation_insights(correlation)
        print(f"  • Added correlation insights: {correlation['overall_pattern']}")
    
    # Create session summary
    review_data = {
        'session_id': session_id,
        'items_captured': 15,
        'projects_reviewed': 8,
        'decisions_made': 12
    }
    
    await memory.create_session_summary(review_data, timing_data)
    
    # Flush episodes
    episodes_saved = await memory.flush_episodes()
    print(f"\n✓ Saved {episodes_saved} episodes to Graphiti batch file")
    
    # Check if file was created
    data_dir = Path("data")
    batch_files = list(data_dir.glob(f"graphiti_batch_{session_id}_*.json"))
    
    if batch_files:
        print(f"✓ Batch file created: {batch_files[0].name}")
        
        # Show sample of saved data
        with open(batch_files[0], 'r') as f:
            batch_data = json.load(f)
            print(f"  • Episodes in batch: {len(batch_data.get('episodes', []))}")
            
            # Show episode types
            episode_types = [e['type'] for e in batch_data.get('episodes', [])]
            print(f"  • Episode types: {', '.join(set(episode_types))}")
    else:
        print("⚠️ No batch file created")


async def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("TIMING + GRAPHITI INTEGRATION TEST")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Test 1: Timing Analysis
        timing_data = await test_timing_analysis()
        
        # Test 2: ADHD Pattern Detection
        adhd_analysis = None
        if timing_data:
            adhd_analysis = await test_adhd_pattern_detection(timing_data)
        
        # Test 3: Priority Comparison
        if timing_data:
            await test_priority_comparison(timing_data)
        
        # Test 4: Graphiti Memory Storage
        await test_graphiti_memory_storage(timing_data, adhd_analysis)
        
        print("\n" + "="*60)
        print("✅ INTEGRATION TEST COMPLETE")
        print("="*60)
        
        # Summary
        if timing_data and timing_data.get('focus_metrics'):
            print(f"\n📊 Final Summary:")
            print(f"  • Focus Score: {timing_data['focus_metrics']['focus_score']}/100")
            print(f"  • Data Type: {timing_data.get('data_type')}")
            print(f"  • Projects Tracked: {len(timing_data.get('projects', []))}")
            
            if adhd_analysis:
                print(f"  • ADHD Patterns: {len(adhd_analysis.get('adhd_indicators', []))} indicators")
                print(f"  • Recommendations: {len(adhd_analysis.get('recommendations', []))} suggestions")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)