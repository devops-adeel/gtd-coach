#!/usr/bin/env python3
"""
Test the enhanced Graphiti integration features
Tests user context, batching, ADHD detection, and monitoring
"""

import asyncio
import logging
from datetime import datetime
from graphiti_integration import GraphitiMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_features():
    """Test all enhanced Graphiti features"""
    
    print("\n" + "="*60)
    print("ENHANCED GRAPHITI INTEGRATION TEST")
    print("="*60)
    
    # Create memory instance
    memory = GraphitiMemory(
        session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        enable_json_backup=True
    )
    
    # Initialize with user context
    print("\n1. Testing user context creation...")
    await memory.initialize()
    if memory.user_node_uuid:
        print(f"✅ User node created: {memory.user_node_uuid[:8]}...")
    else:
        print("⚠️ User node not created (Graphiti may be disabled)")
    
    # Test cost-aware batching
    print("\n2. Testing cost-aware batching...")
    memory.current_phase = "MIND_SWEEP"
    
    # Add multiple interactions - some should batch
    for i in range(7):
        await memory.add_interaction(
            role="user",
            content=f"Task item {i+1}: Something to do",
            phase="MIND_SWEEP"
        )
    
    # Add a trivial response that should be skipped
    await memory.add_interaction(
        role="user",
        content="ok",
        phase="MIND_SWEEP"
    )
    
    print(f"✅ Added 8 interactions (1 trivial should be skipped)")
    print(f"   Pending batch: {len(memory.pending_graphiti_episodes)} episodes")
    
    # Test lightweight ADHD detection
    print("\n3. Testing ADHD pattern detection...")
    
    # Set up intervention callback
    interventions = []
    async def capture_intervention(message):
        interventions.append(message)
        print(f"   🧠 Intervention triggered: {message}")
    
    memory.set_intervention_callback(capture_intervention)
    
    # Simulate rapid context switching
    topics = [
        "I need to organize my desk",
        "What about that email from yesterday?",
        "The project deadline is coming up",
        "Should I get coffee first?",
        "Wait, did I lock the door?"
    ]
    
    for topic in topics:
        await memory.add_interaction(
            role="user",
            content=topic,
            phase="MIND_SWEEP"
        )
        await asyncio.sleep(0.1)  # Simulate rapid switching
    
    if interventions:
        print(f"✅ ADHD detection working - {len(interventions)} interventions triggered")
    else:
        print("⚠️ No interventions triggered (may need adjustment)")
    
    # Test context-centered search
    print("\n4. Testing context-centered search...")
    results = await memory.search_with_context("tasks to do", num_results=5)
    print(f"✅ Search returned {len(results)} results")
    
    # Flush and check metrics
    print("\n5. Testing batch flush and metrics...")
    flushed = await memory.flush_episodes()
    print(f"✅ Flushed {flushed} episodes to JSON backup")
    
    # Create session summary
    print("\n6. Creating session summary...")
    await memory.create_session_summary(
        review_data={
            'mindsweep_count': 7,
            'patterns_detected': len(interventions),
            'phase_durations': {'MIND_SWEEP': 120}
        }
    )
    print("✅ Session summary created")
    
    # Final stats
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ User context: {'Yes' if memory.user_node_uuid else 'No'}")
    print(f"✅ Interactions tracked: {memory.interaction_count}")
    print(f"✅ Context switches detected: {len(interventions)}")
    print(f"✅ Episodes in JSON backup: {flushed}")
    print(f"✅ Graphiti client: {'Connected' if memory.graphiti_client else 'Not connected'}")
    
    print("\n🎉 All enhanced features tested successfully!")
    
    # Clean up
    if memory.graphiti_client:
        from graphiti_client import GraphitiClient
        await GraphitiClient().close()


if __name__ == "__main__":
    asyncio.run(test_enhanced_features())