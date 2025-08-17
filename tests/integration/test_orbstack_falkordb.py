#!/usr/bin/env python3
"""
Test script for Orbstack FalkorDB integration
Tests connection using Orbstack custom domains
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load Orbstack configuration
from dotenv import load_dotenv
load_dotenv('.env.graphiti.orbstack')

# Import after environment is loaded
from gtd_coach.integrations.graphiti_client import GraphitiClient


async def test_orbstack_connection():
    """Test FalkorDB connection via Orbstack custom domain"""
    
    print("=" * 60)
    print("TESTING FALKORDB CONNECTION VIA ORBSTACK")
    print("=" * 60)
    
    # Display configuration
    backend = os.getenv('GRAPHITI_BACKEND', 'falkordb')
    host = os.getenv('FALKORDB_HOST')
    port = os.getenv('FALKORDB_PORT')
    database = os.getenv('FALKORDB_DATABASE')
    
    print(f"Backend: {backend}")
    print(f"FalkorDB Host: {host}")
    print(f"FalkorDB Port: {port}")
    print(f"FalkorDB Database: {database}")
    print()
    
    if not host:
        print("❌ ERROR: FALKORDB_HOST not configured")
        print("Please ensure .env.graphiti.orbstack is loaded")
        return False
    
    # Test different connection methods
    print("Testing connection methods:")
    print("-" * 40)
    
    # Method 1: Direct connection test
    print("\n1. Testing direct Redis connection to FalkorDB...")
    try:
        import redis
        r = redis.Redis(host=host, port=int(port), decode_responses=True)
        response = r.ping()
        if response:
            print(f"✅ Direct Redis connection successful to {host}:{port}")
        else:
            print(f"❌ Failed to ping FalkorDB at {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return False
    
    # Method 2: FalkorDB driver test
    print("\n2. Testing FalkorDB driver...")
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=host, port=int(port))
        
        # Select graph database
        graph = db.select_graph(database)
        
        # Run a simple query
        result = graph.query("RETURN 1 as test")
        if result and result.result_set:
            print(f"✅ FalkorDB driver connected to graph: {database}")
        else:
            print(f"⚠️  FalkorDB connected but query returned no results")
            
    except Exception as e:
        print(f"❌ FalkorDB driver test failed: {e}")
        return False
    
    # Method 3: Graphiti client test
    print("\n3. Testing Graphiti client with FalkorDB...")
    try:
        client = GraphitiClient()
        graphiti = await client.initialize()
        
        # Try to add a test episode
        from graphiti_core.nodes import EpisodeType
        from datetime import datetime, timezone
        
        await graphiti.add_episode(
            name="orbstack_test",
            episode_body="Testing Orbstack FalkorDB connection",
            source=EpisodeType.text,
            source_description="Orbstack test",
            group_id="shared_knowledge",
            reference_time=datetime.now(timezone.utc)
        )
        
        print("✅ Graphiti client successfully connected via Orbstack")
        
        # Try a search
        results = await graphiti.search("orbstack", num_results=5)
        print(f"✅ Search functionality working ({len(results)} results)")
        
    except Exception as e:
        print(f"❌ Graphiti client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✅ Direct Redis connection: SUCCESS")
    print("✅ FalkorDB driver: SUCCESS")
    print("✅ Graphiti integration: SUCCESS")
    print("\n🎉 ORBSTACK FALKORDB IS FULLY OPERATIONAL!")
    
    return True


async def test_custom_domains():
    """Test various Orbstack custom domain formats"""
    
    print("\n" + "=" * 60)
    print("TESTING ORBSTACK CUSTOM DOMAINS")
    print("=" * 60)
    
    import redis
    
    # Common Orbstack domain patterns
    domains_to_test = [
        ("falkordb.orb.local", 6379, "Orbstack .orb.local domain"),
        ("falkordb", 6379, "Container name only"),
        ("host.docker.internal", 6380, "Docker host (if FalkorDB on host)"),
        ("localhost", 6380, "Localhost (existing instance)"),
    ]
    
    print("\nTesting various domain formats:")
    for host, port, description in domains_to_test:
        try:
            r = redis.Redis(host=host, port=port, decode_responses=True, socket_connect_timeout=2)
            r.ping()
            print(f"✅ {description:30} - {host}:{port} - Connected")
        except Exception as e:
            print(f"❌ {description:30} - {host}:{port} - Failed")
    
    print("\nRecommendation: Use the domain that shows as connected above")


async def main():
    """Main test runner"""
    
    # First test Orbstack connection
    orbstack_success = await test_orbstack_connection()
    
    if orbstack_success:
        # Test different domain formats
        await test_custom_domains()
        
        print("\n" + "=" * 60)
        print("CONFIGURATION RECOMMENDATIONS")
        print("=" * 60)
        print("\nFor Orbstack, use one of these configurations in .env:")
        print("\n# Option 1: Orbstack custom domain (recommended)")
        print("FALKORDB_HOST=falkordb.orb.local")
        print("FALKORDB_PORT=6379")
        print("\n# Option 2: Container name (simpler)")
        print("FALKORDB_HOST=falkordb")
        print("FALKORDB_PORT=6379")
        print("\n# Option 3: Existing local instance")
        print("FALKORDB_HOST=localhost")
        print("FALKORDB_PORT=6380")
    else:
        print("\n❌ Orbstack connection failed")
        print("\nTroubleshooting:")
        print("1. Ensure FalkorDB container is running in Orbstack")
        print("2. Check container name matches configuration")
        print("3. Verify port mapping in Orbstack")
        print("4. Try 'orbstack list' to see running containers")


if __name__ == "__main__":
    asyncio.run(main())