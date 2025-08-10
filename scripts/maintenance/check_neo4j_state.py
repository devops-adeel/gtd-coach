#!/usr/bin/env python3
"""
Check the current state of the Neo4j database
Shows node counts, relationship counts, and sample data
"""

import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.graphiti')


async def check_database_state():
    """Check Neo4j database state"""
    
    # Get connection details
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    
    print("="*60)
    print("NEO4J DATABASE STATE CHECK")
    print("="*60)
    print(f"Connecting to: {uri}")
    print(f"User: {user}")
    print()
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        async with driver.session() as session:
            # Count all nodes
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            total_nodes = record['count']
            print(f"📊 Total Nodes: {total_nodes}")
            
            # Count nodes by label
            result = await session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            
            print("\n📌 Nodes by Type:")
            async for record in result:
                if record['label']:
                    print(f"  - {record['label']}: {record['count']}")
            
            # Count relationships
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            total_relationships = record['count']
            print(f"\n🔗 Total Relationships: {total_relationships}")
            
            # Count relationships by type
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                LIMIT 10
            """)
            
            print("\n🔗 Top Relationship Types:")
            async for record in result:
                print(f"  - {record['type']}: {record['count']}")
            
            # Sample episodes
            result = await session.run("""
                MATCH (e:Episodic)
                RETURN e.name as name, e.group_id as group_id
                ORDER BY e.created_at DESC
                LIMIT 5
            """)
            
            print("\n📝 Recent Episodes:")
            async for record in result:
                print(f"  - {record['name']} (group: {record['group_id']})")
            
            # Sample entities
            result = await session.run("""
                MATCH (n:Entity)
                WHERE n.name IS NOT NULL
                RETURN n.name as name, n.group_id as group_id
                ORDER BY n.created_at DESC
                LIMIT 5
            """)
            
            print("\n🏷️ Recent Entities:")
            async for record in result:
                print(f"  - {record['name']} (group: {record['group_id']})")
            
            # Check for GTD-specific content
            result = await session.run("""
                MATCH (n)
                WHERE n.name CONTAINS 'gtd' OR n.name CONTAINS 'GTD' 
                   OR n.name CONTAINS 'mindsweep' OR n.name CONTAINS 'review'
                RETURN count(n) as count
            """)
            record = await result.single()
            gtd_nodes = record['count']
            
            print(f"\n🎯 GTD-Related Nodes: {gtd_nodes}")
            
            # Check for test data
            result = await session.run("""
                MATCH (n)
                WHERE n.group_id STARTS WITH 'gtd_test' 
                   OR n.group_id STARTS WITH 'gtd_review'
                RETURN n.group_id as group_id, count(n) as count
                ORDER BY count DESC
                LIMIT 5
            """)
            
            print("\n🧪 GTD Groups:")
            async for record in result:
                print(f"  - {record['group_id']}: {record['count']} nodes")
            
            # Database size estimate
            if total_nodes > 0:
                print("\n📈 Database Summary:")
                print(f"  - Nodes: {total_nodes:,}")
                print(f"  - Relationships: {total_relationships:,}")
                print(f"  - Avg relationships per node: {total_relationships/total_nodes:.1f}")
                
                if gtd_nodes > 0:
                    print(f"  - GTD content: {gtd_nodes/total_nodes*100:.1f}% of nodes")
            
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(check_database_state())