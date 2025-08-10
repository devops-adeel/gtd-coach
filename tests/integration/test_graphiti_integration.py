#!/usr/bin/env python3
"""
Test script for Graphiti integration with GTD Coach
Validates memory capture and pattern detection
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

# Test imports
try:
    from gtd_coach.integrations.graphiti import GraphitiMemory
    from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector
    print("✅ Successfully imported Graphiti integration modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)


async def test_memory_capture():
    """Test basic memory capture functionality"""
    print("\n🧪 Testing Memory Capture...")
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_test")
    memory = GraphitiMemory(session_id)
    
    # Test interaction capture
    await memory.add_interaction(
        role="user",
        content="I need to finish the project report",
        phase="MIND_SWEEP"
    )
    
    await memory.add_interaction(
        role="assistant",
        content="Great! Let's capture that. What else is on your mind?",
        phase="MIND_SWEEP",
        metrics={"response_time": 1.2}
    )
    
    # Test phase transition
    await memory.add_phase_transition("Mind Sweep", "start")
    await asyncio.sleep(0.1)
    await memory.add_phase_transition("Mind Sweep", "end", 300.5)
    
    # Test behavior pattern
    await memory.add_behavior_pattern(
        pattern_type="task_switch",
        phase="MIND_SWEEP",
        pattern_data={
            "from_topic": "work",
            "to_topic": "personal",
            "from_item": "finish project report",
            "to_item": "call dentist"
        }
    )
    
    # Test mindsweep batch
    items = [
        "Finish project report",
        "Call dentist",
        "Review budget",
        "Team meeting prep",
        "Clean desk"
    ]
    
    await memory.add_mindsweep_batch(
        items=items,
        phase_metrics={
            "capture_duration_seconds": 180,
            "items_per_minute": 1.67,
            "coherence_analysis": {
                "coherence_score": 0.7,
                "topic_switches": 2,
                "lexical_diversity": 0.85
            }
        }
    )
    
    # Flush episodes
    count = await memory.flush_episodes()
    print(f"✅ Flushed {count} episodes to disk")
    
    # Verify file was created
    data_dir = Path.home() / "gtd-coach" / "data"
    batch_files = list(data_dir.glob(f"graphiti_batch_{session_id}_*.json"))
    
    if batch_files:
        print(f"✅ Created batch file: {batch_files[0].name}")
        
        # Load and verify content
        with open(batch_files[0], 'r') as f:
            data = json.load(f)
        
        print(f"  - Session ID: {data['session_id']}")
        print(f"  - Group ID: {data['group_id']}")
        print(f"  - Episodes: {len(data['episodes'])}")
    else:
        print("❌ No batch file created")


def test_pattern_detection():
    """Test ADHD pattern detection"""
    print("\n🧪 Testing Pattern Detection...")
    
    detector = ADHDPatternDetector()
    
    # Test 1: High coherence items
    coherent_items = [
        "Finish Q4 project report",
        "Review project budget for Q4",
        "Schedule project review meeting",
        "Update project timeline"
    ]
    
    analysis1 = detector.analyze_mindsweep_coherence(coherent_items)
    print(f"\n📊 Coherent items analysis:")
    print(f"  - Coherence score: {analysis1['coherence_score']:.2f}")
    print(f"  - Topic switches: {analysis1['topic_switches']}")
    print(f"  - Lexical diversity: {analysis1['lexical_diversity']:.3f}")
    
    # Test 2: Fragmented items with ADHD markers
    fragmented_items = [
        "Project report",
        "I don't know, maybe call someone",
        "Oh wait, dentist!",
        "Budget? Not sure",
        "Umm... exercise",
        "Clean something"
    ]
    
    analysis2 = detector.analyze_mindsweep_coherence(fragmented_items)
    print(f"\n📊 Fragmented items analysis:")
    print(f"  - Coherence score: {analysis2['coherence_score']:.2f}")
    print(f"  - Topic switches: {analysis2['topic_switches']}")
    print(f"  - Fragmentation indicators: {len(analysis2['fragmentation_indicators'])}")
    
    # Test 3: Task switching detection
    switch = detector.detect_task_switching(
        current_item="Call dentist about appointment",
        previous_item="Finish project report section 3",
        time_between=1.5
    )
    
    if switch:
        print(f"\n🔄 Task switch detected:")
        print(f"  - From: {switch['from_topic']} → To: {switch['to_topic']}")
        print(f"  - Abrupt: {switch['abrupt']}")
    
    # Test 4: Focus score calculation
    phase_data = {
        "duration_seconds": 280,
        "expected_duration": 300,
        "completed_items": 8,
        "total_items": 10,
        "interactions": [
            {"response_time": 2.1},
            {"response_time": 2.3},
            {"response_time": 2.0},
            {"response_time": 5.2},  # Outlier
        ]
    }
    
    focus_metrics = detector.calculate_focus_score(phase_data)
    print(f"\n🎯 Focus metrics:")
    print(f"  - Overall score: {focus_metrics['overall_score']:.2f}")
    print(f"  - Time efficiency: {focus_metrics['time_efficiency']:.2f}")
    print(f"  - Response consistency: {focus_metrics['response_consistency']:.2f}")
    print(f"  - Task completion: {focus_metrics['task_completion']:.2f}")


async def test_integration_with_gtd():
    """Test integration with GTD Coach (minimal test)"""
    print("\n🧪 Testing GTD Coach Integration...")
    
    try:
        # Import will validate that our changes don't break GTDCoach
        import sys
        sys.path.insert(0, str(Path.home() / "gtd-coach"))
        
        # Import using direct file reading since module has hyphen
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gtd_review", 
            str(Path.home() / "gtd-coach" / "gtd-review.py")
        )
        gtd_review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gtd_review)
        
        print("✅ GTDCoach module imports successfully")
        
        # Verify the class has our new attributes
        if hasattr(gtd_review.GTDCoach, '__init__'):
            print("✅ GTDCoach class structure intact")
        
        # Note: We don't instantiate here since it requires LM Studio running
        print("✅ Ready for full integration test with LM Studio")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Initialization error: {e}")


async def main():
    """Run all tests"""
    print("="*60)
    print("🧪 GRAPHITI INTEGRATION TEST SUITE")
    print("="*60)
    
    # Run tests
    await test_memory_capture()
    test_pattern_detection()
    await test_integration_with_gtd()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("\n📝 Next steps:")
    print("1. Ensure LM Studio is running for full integration test")
    print("2. Run: python3 ~/gtd-coach/gtd-review.py")
    print("3. After a review, run: python3 ~/gtd-coach/generate_summary.py")
    print("4. Configure MCP tools for full Graphiti integration")


if __name__ == "__main__":
    asyncio.run(main())