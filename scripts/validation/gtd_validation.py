#!/usr/bin/env python3
"""
GTD-Specific Data Validation for Graphiti
Ensures GTD relationships and data integrity in the knowledge graph
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from neo4j import AsyncGraphDatabase
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gtd_coach.integrations.graphiti_client import GraphitiClient
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.graphiti')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GTDValidator:
    """Validates GTD data integrity in Graphiti/Neo4j"""
    
    def __init__(self):
        self.driver = None
        self.graphiti_client = None
        self.validation_results = {}
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD')
        
    async def initialize(self):
        """Initialize Neo4j driver and Graphiti client"""
        try:
            # Initialize Neo4j driver
            self.driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            
            # Initialize Graphiti client
            self.graphiti_client = await GraphitiClient.get_instance()
            
            logger.info("✅ Initialized validation tools")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def validate_actions_have_contexts(self) -> Dict[str, Any]:
        """Validate that all actions have associated contexts"""
        validation_name = "Actions Have Contexts"
        
        try:
            async with self.driver.session() as session:
                # Find actions without contexts
                query = """
                MATCH (n:Entity)
                WHERE (n.name CONTAINS 'action' OR n.name CONTAINS 'task')
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@home'})
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@office'})
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@computer'})
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@phone'})
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@errands'})
                  AND NOT (n)-[:RELATES_TO|MENTIONS]->(:Entity {name: '@anywhere'})
                RETURN n.name as action, n.uuid as uuid
                LIMIT 10
                """
                
                result = await session.run(query)
                orphaned_actions = []
                async for record in result:
                    orphaned_actions.append({
                        'action': record['action'],
                        'uuid': record['uuid']
                    })
                
                passed = len(orphaned_actions) == 0
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'orphaned_count': len(orphaned_actions),
                    'orphaned_actions': orphaned_actions[:5],  # Show first 5
                    'recommendation': "Add context tags (@home, @office, etc.) to actions" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_projects_have_next_actions(self) -> Dict[str, Any]:
        """Validate that active projects have next actions"""
        validation_name = "Projects Have Next Actions"
        
        try:
            async with self.driver.session() as session:
                # Find projects without next actions
                query = """
                MATCH (p:Entity)
                WHERE p.name CONTAINS 'project'
                  AND NOT (p)-[:RELATES_TO]->(:Entity)
                RETURN p.name as project, p.uuid as uuid
                LIMIT 10
                """
                
                result = await session.run(query)
                stalled_projects = []
                async for record in result:
                    stalled_projects.append({
                        'project': record['project'],
                        'uuid': record['uuid']
                    })
                
                passed = len(stalled_projects) == 0
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'stalled_count': len(stalled_projects),
                    'stalled_projects': stalled_projects[:5],
                    'recommendation': "Define next actions for stalled projects" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_temporal_consistency(self) -> Dict[str, Any]:
        """Validate temporal ordering of episodes"""
        validation_name = "Temporal Consistency"
        
        try:
            async with self.driver.session() as session:
                # Check for temporal violations
                query = """
                MATCH (e1:Episodic)-[:MENTIONS]->(n)<-[:MENTIONS]-(e2:Episodic)
                WHERE e1.created_at > e2.created_at 
                  AND e1.reference_time < e2.reference_time
                RETURN count(*) as violations
                """
                
                result = await session.run(query)
                record = await result.single()
                violations = record['violations'] if record else 0
                
                passed = violations == 0
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'temporal_violations': violations,
                    'recommendation': "Check episode timestamps for consistency" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_mindsweep_processing(self) -> Dict[str, Any]:
        """Validate that mindsweep items are being processed"""
        validation_name = "Mindsweep Processing"
        
        try:
            async with self.driver.session() as session:
                # Check mindsweep processing rate
                query = """
                MATCH (e:Episodic)
                WHERE e.name CONTAINS 'mindsweep'
                RETURN count(e) as total_mindsweeps
                """
                
                result = await session.run(query)
                record = await result.single()
                total_mindsweeps = record['total_mindsweeps'] if record else 0
                
                # Check for converted items
                query2 = """
                MATCH (e:Episodic)-[:MENTIONS]->(n:Entity)
                WHERE e.name CONTAINS 'mindsweep'
                  AND (n)-[:RELATES_TO]->(:Entity)
                RETURN count(DISTINCT n) as processed_items
                """
                
                result2 = await session.run(query2)
                record2 = await result2.single()
                processed_items = record2['processed_items'] if record2 else 0
                
                processing_rate = (processed_items / total_mindsweeps * 100) if total_mindsweeps > 0 else 0
                passed = processing_rate > 30  # At least 30% should be processed
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'total_mindsweeps': total_mindsweeps,
                    'processed_items': processed_items,
                    'processing_rate': f"{processing_rate:.1f}%",
                    'recommendation': "Review and process more mindsweep items" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_review_frequency(self) -> Dict[str, Any]:
        """Check if reviews are happening regularly"""
        validation_name = "Review Frequency"
        
        try:
            async with self.driver.session() as session:
                # Check review frequency
                query = """
                MATCH (e:Episodic)
                WHERE e.group_id STARTS WITH 'gtd_review'
                RETURN e.created_at as review_date
                ORDER BY e.created_at DESC
                LIMIT 10
                """
                
                result = await session.run(query)
                review_dates = []
                async for record in result:
                    review_dates.append(record['review_date'])
                
                if len(review_dates) < 2:
                    passed = False
                    gap_days = None
                    recommendation = "Not enough reviews to analyze frequency"
                else:
                    # Calculate average gap between reviews
                    gaps = []
                    for i in range(len(review_dates) - 1):
                        gap = (review_dates[i] - review_dates[i+1]).days
                        gaps.append(gap)
                    
                    avg_gap = sum(gaps) / len(gaps) if gaps else 0
                    passed = avg_gap <= 7  # Weekly reviews
                    gap_days = avg_gap
                    
                    if avg_gap > 14:
                        recommendation = "Reviews are too infrequent - aim for weekly"
                    elif avg_gap > 7:
                        recommendation = "Consider more frequent reviews"
                    else:
                        recommendation = None
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'review_count': len(review_dates),
                    'average_gap_days': gap_days,
                    'recommendation': recommendation
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_adhd_pattern_tracking(self) -> Dict[str, Any]:
        """Validate ADHD pattern detection and tracking"""
        validation_name = "ADHD Pattern Tracking"
        
        try:
            async with self.driver.session() as session:
                # Check for ADHD pattern entities
                query = """
                MATCH (n:Entity)
                WHERE n.name CONTAINS 'pattern' 
                   OR n.name CONTAINS 'switch'
                   OR n.name CONTAINS 'focus'
                   OR n.name CONTAINS 'scatter'
                RETURN count(n) as pattern_count
                """
                
                result = await session.run(query)
                record = await result.single()
                pattern_count = record['pattern_count'] if record else 0
                
                # Check for pattern episodes
                query2 = """
                MATCH (e:Episodic)
                WHERE e.name CONTAINS 'pattern' OR e.name CONTAINS 'adhd'
                RETURN count(e) as pattern_episodes
                """
                
                result2 = await session.run(query2)
                record2 = await result2.single()
                pattern_episodes = record2['pattern_episodes'] if record2 else 0
                
                passed = pattern_count > 0 or pattern_episodes > 0
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'pattern_entities': pattern_count,
                    'pattern_episodes': pattern_episodes,
                    'recommendation': "Enable ADHD pattern tracking in reviews" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_priority_distribution(self) -> Dict[str, Any]:
        """Check priority distribution of tasks"""
        validation_name = "Priority Distribution"
        
        try:
            async with self.driver.session() as session:
                # Check priority distribution
                query = """
                MATCH (n:Entity)
                WHERE n.name CONTAINS 'priority'
                   OR n.name CONTAINS 'urgent'
                   OR n.name CONTAINS 'important'
                RETURN n.name as priority_item
                LIMIT 20
                """
                
                result = await session.run(query)
                priority_items = []
                async for record in result:
                    priority_items.append(record['priority_item'])
                
                # Count by priority level
                a_count = sum(1 for item in priority_items if 'A' in str(item) or 'urgent' in str(item).lower())
                b_count = sum(1 for item in priority_items if 'B' in str(item) or 'important' in str(item).lower())
                c_count = sum(1 for item in priority_items if 'C' in str(item))
                
                total = a_count + b_count + c_count
                
                if total == 0:
                    passed = False
                    recommendation = "No priorities set - add priority levels to tasks"
                else:
                    # Check for healthy distribution (not everything urgent)
                    a_percentage = (a_count / total) * 100
                    passed = a_percentage < 40  # Less than 40% should be A priority
                    
                    if a_percentage > 60:
                        recommendation = "Too many urgent items - reconsider priorities"
                    elif a_percentage > 40:
                        recommendation = "Consider if all A priorities are truly urgent"
                    else:
                        recommendation = None
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'priority_a': a_count,
                    'priority_b': b_count,
                    'priority_c': c_count,
                    'recommendation': recommendation
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def validate_data_quality(self) -> Dict[str, Any]:
        """Overall data quality metrics"""
        validation_name = "Data Quality"
        
        try:
            async with self.driver.session() as session:
                # Check for duplicate entities
                query = """
                MATCH (n1:Entity), (n2:Entity)
                WHERE n1.uuid < n2.uuid
                  AND n1.name = n2.name
                  AND n1.group_id = n2.group_id
                RETURN count(*) as duplicates
                """
                
                result = await session.run(query)
                record = await result.single()
                duplicates = record['duplicates'] if record else 0
                
                # Check for empty relationships
                query2 = """
                MATCH ()-[r:RELATES_TO]->()
                WHERE r.fact IS NULL OR r.fact = ''
                RETURN count(r) as empty_facts
                """
                
                result2 = await session.run(query2)
                record2 = await result2.single()
                empty_facts = record2['empty_facts'] if record2 else 0
                
                passed = duplicates == 0 and empty_facts == 0
                
                return {
                    'name': validation_name,
                    'passed': passed,
                    'duplicate_entities': duplicates,
                    'empty_relationships': empty_facts,
                    'recommendation': "Clean up duplicates and empty relationships" if not passed else None
                }
                
        except Exception as e:
            return {
                'name': validation_name,
                'passed': False,
                'error': str(e)
            }
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all GTD validations"""
        print("\n" + "="*60)
        print("GTD DATA VALIDATION SUITE")
        print("="*60)
        print(f"Database: {self.uri}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not await self.initialize():
            print("❌ Failed to initialize validation suite")
            return {'success': False, 'error': 'Initialization failed'}
        
        # Run all validation methods
        validations = [
            self.validate_actions_have_contexts,
            self.validate_projects_have_next_actions,
            self.validate_temporal_consistency,
            self.validate_mindsweep_processing,
            self.validate_review_frequency,
            self.validate_adhd_pattern_tracking,
            self.validate_priority_distribution,
            self.validate_data_quality,
        ]
        
        results = []
        passed_count = 0
        failed_count = 0
        
        for validation_func in validations:
            result = await validation_func()
            results.append(result)
            
            if result.get('passed'):
                passed_count += 1
                status = "✅ PASS"
            else:
                failed_count += 1
                status = "❌ FAIL"
            
            print(f"\n{status}: {result['name']}")
            
            # Print details
            for key, value in result.items():
                if key not in ['name', 'passed', 'recommendation', 'error']:
                    print(f"  - {key}: {value}")
            
            if result.get('recommendation'):
                print(f"  💡 Recommendation: {result['recommendation']}")
            
            if result.get('error'):
                print(f"  ⚠️ Error: {result['error']}")
        
        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Success Rate: {passed_count/(passed_count+failed_count)*100:.1f}%")
        
        # Critical issues
        critical_issues = [r for r in results if not r.get('passed') and r['name'] in [
            'Actions Have Contexts',
            'Projects Have Next Actions',
            'Data Quality'
        ]]
        
        if critical_issues:
            print("\n⚠️ CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"  - {issue['name']}: {issue.get('recommendation', 'Check details above')}")
        
        # Close connections
        if self.driver:
            await self.driver.close()
        
        return {
            'success': True,
            'passed': passed_count,
            'failed': failed_count,
            'results': results
        }


async def main():
    """Main entry point"""
    validator = GTDValidator()
    result = await validator.run_all_validations()
    return 0 if result['success'] and result['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)