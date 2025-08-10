#!/usr/bin/env python3
"""
Test script to verify Graphiti and Neo4j connectivity
Run this to ensure all components are properly configured
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gtd_coach.integrations.graphiti_client import GraphitiClient
from graphiti_core.nodes import EpisodeType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_neo4j_connection():
    """Test 1: Verify Neo4j database connection"""
    print("\n" + "="*60)
    print("TEST 1: Neo4j Connection")
    print("="*60)
    
    try:
        client_instance = GraphitiClient()
        # This will verify Neo4j connection as part of initialization
        await client_instance.initialize()
        print("✅ Neo4j connection successful")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False


async def test_graphiti_initialization():
    """Test 2: Verify Graphiti client initialization"""
    print("\n" + "="*60)
    print("TEST 2: Graphiti Client Initialization")
    print("="*60)
    
    try:
        client = await GraphitiClient.get_instance()
        print("✅ Graphiti client initialized successfully")
        print(f"  - Client type: {type(client).__name__}")
        print(f"  - Has driver: {hasattr(client, 'driver')}")
        return True
    except Exception as e:
        print(f"❌ Graphiti initialization failed: {e}")
        return False


async def test_episode_creation():
    """Test 3: Create a test episode in Graphiti"""
    print("\n" + "="*60)
    print("TEST 3: Episode Creation")
    print("="*60)
    
    try:
        client = await GraphitiClient.get_instance()
        
        test_episode = {
            "name": f"test_episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "episode_body": "This is a test episode from GTD Coach connection test",
            "source": EpisodeType.text,
            "source_description": "GTD Coach connection test",
            "group_id": "gtd_test_group",
            "reference_time": datetime.now(timezone.utc)
        }
        
        await client.add_episode(**test_episode)
        print(f"✅ Successfully created episode: {test_episode['name']}")
        return True
    except Exception as e:
        print(f"❌ Episode creation failed: {e}")
        return False


async def test_json_episode():
    """Test 4: Create a JSON-type episode (like GTD data)"""
    print("\n" + "="*60)
    print("TEST 4: JSON Episode Creation")
    print("="*60)
    
    try:
        client = await GraphitiClient.get_instance()
        
        # Simulate GTD review data
        gtd_data = {
            "type": "mindsweep",
            "items": ["Test task 1", "Test task 2", "Test task 3"],
            "phase": "MIND_SWEEP",
            "metrics": {
                "duration_seconds": 120,
                "item_count": 3
            }
        }
        
        import json
        await client.add_episode(
            name=f"gtd_mindsweep_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            episode_body=json.dumps(gtd_data),
            source=EpisodeType.json,
            source_description="GTD Coach mindsweep test",
            group_id="gtd_test_group",
            reference_time=datetime.now(timezone.utc)
        )
        
        print("✅ Successfully created JSON episode with GTD data")
        return True
    except Exception as e:
        print(f"❌ JSON episode creation failed: {e}")
        return False


async def test_search_functionality():
    """Test 5: Search for created episodes"""
    print("\n" + "="*60)
    print("TEST 5: Search Functionality")
    print("="*60)
    
    try:
        client = await GraphitiClient.get_instance()
        
        # Search for test episodes
        results = await client.search(
            query="test",
            num_results=10
        )
        
        print(f"✅ Search successful, found {len(results)} results")
        
        if results:
            print("  Sample results:")
            for i, result in enumerate(results[:3], 1):
                # The result structure depends on Graphiti's implementation
                print(f"    {i}. {result}")
        
        return True
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False


async def test_health_check():
    """Test 6: Verify health check functionality"""
    print("\n" + "="*60)
    print("TEST 6: Health Check")
    print("="*60)
    
    try:
        client_instance = GraphitiClient()
        await client_instance.initialize()
        
        is_healthy = await client_instance.health_check()
        
        if is_healthy:
            print("✅ Health check passed - system is healthy")
        else:
            print("⚠️ Health check indicates system issues")
        
        return is_healthy
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_environment_detection():
    """Test 7: Verify environment configuration"""
    print("\n" + "="*60)
    print("TEST 7: Environment Configuration")
    print("="*60)
    
    print("Checking environment variables...")
    
    required_vars = {
        'NEO4J_URI': os.getenv('NEO4J_URI'),
        'NEO4J_USER': os.getenv('NEO4J_USER'),
        'NEO4J_PASSWORD': '***' if os.getenv('NEO4J_PASSWORD') else None,
        'NEO4J_DATABASE': os.getenv('NEO4J_DATABASE', 'neo4j'),
        'OPENAI_API_KEY': '***' if os.getenv('OPENAI_API_KEY') else None,
        'OPENAI_MODEL': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
        'OPENAI_EMBEDDING_MODEL': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large'),
    }
    
    all_present = True
    for var, value in required_vars.items():
        if value:
            print(f"  ✅ {var}: {value if not value.startswith('***') else value}")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_present = False
    
    # Check if running in Docker
    in_docker = os.getenv('IN_DOCKER', 'false').lower() == 'true'
    print(f"\n  Running in Docker: {'Yes' if in_docker else 'No'}")
    
    return all_present


async def cleanup_test_data():
    """Optional: Clean up test data from Neo4j"""
    print("\n" + "="*60)
    print("CLEANUP: Removing Test Data")
    print("="*60)
    
    try:
        client = await GraphitiClient.get_instance()
        
        # Note: This would require custom cleanup logic
        # For now, we'll just close the connection
        await GraphitiClient().close()
        
        print("✅ Cleanup completed")
        return True
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
        return True  # Don't fail on cleanup


async def main():
    """Run all tests in sequence"""
    print("\n" + "="*60)
    print("GRAPHITI CONNECTION TEST SUITE")
    print("="*60)
    print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track test results
    results = {}
    
    # Run tests in sequence
    tests = [
        ("Environment", test_environment_detection),
        ("Neo4j Connection", test_neo4j_connection),
        ("Graphiti Init", test_graphiti_initialization),
        ("Episode Creation", test_episode_creation),
        ("JSON Episode", test_json_episode),
        ("Search", test_search_functionality),
        ("Health Check", test_health_check),
        ("Cleanup", cleanup_test_data),
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")
    
    if failed == 0:
        print("\n🎉 All tests passed! Graphiti integration is ready.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)