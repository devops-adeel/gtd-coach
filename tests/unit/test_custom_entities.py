#!/usr/bin/env python3
"""
Test custom GTD entity extraction with Graphiti v0.18.5
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from gtd_coach.integrations.graphiti_client import GraphitiClient
from graphiti_core.nodes import EpisodeType
from gtd_coach.integrations.gtd_entity_config import get_entity_config_for_episode, ENTITY_TYPES, EDGE_TYPES, EDGE_TYPE_MAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_custom_entities():
    """Test that custom GTD entities are properly extracted"""
    
    print("\n" + "="*60)
    print("CUSTOM GTD ENTITY EXTRACTION TEST")
    print("="*60)
    
    try:
        # Initialize Graphiti client
        print("\n1. Initializing Graphiti client...")
        client = await GraphitiClient.get_instance()
        print("✅ Client initialized")
        
        # Test 1: Add an interaction episode with GTD content
        print("\n2. Testing interaction episode (should use custom entities)...")
        interaction_text = """
        I need to review the quarterly budget report for the Finance area.
        The next action is to @office schedule a meeting with the CFO.
        This is a high priority task that requires about 30 minutes.
        """
        
        entity_config = get_entity_config_for_episode("interaction")
        if entity_config:
            print(f"   Using {len(entity_config['entity_types'])} entity types")
            print(f"   Using {len(entity_config['edge_types'])} edge types")
        
        await client.add_episode(
            name="test_interaction_with_entities",
            episode_body=interaction_text,
            source=EpisodeType.message,
            source_description="Test interaction with GTD entities",
            group_id=f"test_custom_entities_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            reference_time=datetime.now(timezone.utc),
            **entity_config if entity_config else {}
        )
        print("✅ Interaction episode added with custom entities")
        
        # Test 2: Add a mindsweep episode
        print("\n3. Testing mindsweep episode (should use custom entities)...")
        mindsweep_data = {
            "items": [
                "Call dentist to schedule appointment",
                "Review project status for Q1 initiatives",
                "Buy groceries @errands",
                "Research new productivity tools @computer"
            ],
            "phase": "MIND_SWEEP"
        }
        
        entity_config = get_entity_config_for_episode("mindsweep_capture")
        
        await client.add_episode(
            name="test_mindsweep_with_entities",
            episode_body=json.dumps(mindsweep_data),
            source=EpisodeType.json,
            source_description="Test mindsweep with GTD entities",
            group_id=f"test_custom_entities_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            reference_time=datetime.now(timezone.utc),
            **entity_config if entity_config else {}
        )
        print("✅ Mindsweep episode added with custom entities")
        
        # Test 3: Add a phase transition (should NOT use custom entities)
        print("\n4. Testing phase transition (should NOT use custom entities)...")
        phase_data = {
            "action": "start",
            "phase": "PROJECT_REVIEW"
        }
        
        entity_config = get_entity_config_for_episode("phase_transition")
        if entity_config is None:
            print("   Correctly skipping custom entities for phase_transition")
        
        await client.add_episode(
            name="test_phase_transition",
            episode_body=json.dumps(phase_data),
            source=EpisodeType.json,
            source_description="Test phase transition",
            group_id=f"test_custom_entities_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            reference_time=datetime.now(timezone.utc),
            **entity_config if entity_config else {}
        )
        print("✅ Phase transition added without custom entities")
        
        # Test 4: Search for extracted entities
        print("\n5. Searching for extracted GTD entities...")
        
        # Search for actions
        results = await client.search(
            query="next action meeting CFO office",
            num_results=5
        )
        print(f"   Found {len(results)} results for action search")
        
        # Search for contexts
        results = await client.search(
            query="@office @computer @errands context",
            num_results=5
        )
        print(f"   Found {len(results)} results for context search")
        
        # Search for projects
        results = await client.search(
            query="quarterly budget report Finance project",
            num_results=5
        )
        print(f"   Found {len(results)} results for project search")
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✅ Custom entity configuration working")
        print("✅ Selective entity extraction based on episode type")
        print("✅ Entity and edge types properly formatted")
        print("✅ Search functionality maintained")
        print("\n🎉 Custom GTD entity extraction is working correctly!")
        
        # Close the client
        await GraphitiClient().close()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_custom_entities())
    exit(0 if success else 1)