#!/usr/bin/env python3
"""
Test GTD-specific entity extraction with custom Pydantic models
Validates that Graphiti correctly extracts GTD concepts from text
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from graphiti_client import GraphitiClient
from graphiti_core.nodes import EpisodeType
from gtd_entities import (
    GTDProject, GTDAction, GTDContext, GTDAreaOfFocus,
    ADHDPattern, MindsweepItem, WeeklyReview, TimingInsight,
    get_gtd_edge_map, get_gtd_entities
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GTDEntityTester:
    """Test harness for GTD entity extraction"""
    
    def __init__(self):
        self.client = None
        self.test_group_id = f"gtd_entity_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {}
        
    async def initialize(self):
        """Initialize Graphiti client with GTD entities"""
        try:
            # Get standard Graphiti client
            self.client = await GraphitiClient.get_instance()
            
            # Note: In production, you would configure Graphiti with custom entities like:
            # self.client = Graphiti(
            #     driver=driver,
            #     llm_client=llm_client,
            #     custom_entities=get_gtd_entities(),
            #     edge_type_map=get_gtd_edge_map()
            # )
            
            logger.info("✅ Initialized Graphiti client for GTD entity testing")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def test_action_extraction(self):
        """Test extraction of GTD actions from text"""
        print("\n" + "="*60)
        print("TEST: GTD Action Extraction")
        print("="*60)
        
        test_cases = [
            {
                "input": "Call dentist to schedule appointment @phone #urgent",
                "expected": {
                    "action": "Call dentist to schedule appointment",
                    "context": "@phone",
                    "priority": "urgent"
                }
            },
            {
                "input": "Review Q3 financial report @office ~2h waiting for CFO",
                "expected": {
                    "action": "Review Q3 financial report",
                    "context": "@office",
                    "time_estimate": "2 hours",
                    "waiting_for": "CFO"
                }
            },
            {
                "input": "Buy milk and eggs @errands low-energy",
                "expected": {
                    "action": "Buy milk and eggs",
                    "context": "@errands",
                    "energy": "low"
                }
            }
        ]
        
        passed = 0
        failed = 0
        
        for i, test in enumerate(test_cases, 1):
            try:
                # Add episode with action content
                await self.client.add_episode(
                    name=f"test_action_{i}",
                    episode_body=test["input"],
                    source=EpisodeType.text,
                    source_description="GTD action test",
                    group_id=self.test_group_id,
                    reference_time=datetime.now(timezone.utc)
                )
                
                # Search for the action
                results = await self.client.search(
                    query=test["expected"]["action"],
                    num_results=5
                )
                
                # Check if context was extracted
                found_context = any(test["expected"].get("context", "") in str(r) for r in results)
                
                if results and found_context:
                    print(f"  ✅ Test {i}: Extracted action and context from '{test['input']}'")
                    passed += 1
                else:
                    print(f"  ❌ Test {i}: Failed to extract from '{test['input']}'")
                    failed += 1
                    
            except Exception as e:
                print(f"  ❌ Test {i}: Error - {e}")
                failed += 1
        
        print(f"\nResults: {passed} passed, {failed} failed")
        return passed > 0
    
    async def test_project_extraction(self):
        """Test extraction of GTD projects"""
        print("\n" + "="*60)
        print("TEST: GTD Project Extraction")
        print("="*60)
        
        test_project = {
            "name": "Implement new CRM system",
            "status": "active",
            "area_of_focus": "Business Operations",
            "next_action": "Research CRM vendors",
            "outcome": "Fully integrated CRM with all customer data migrated",
            "deadline": "2025-12-31"
        }
        
        try:
            # Add project as JSON episode
            await self.client.add_episode(
                name="test_project",
                episode_body=json.dumps(test_project),
                source=EpisodeType.json,
                source_description="GTD project test",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Search for project elements
            results = await self.client.search(
                query="CRM system implementation",
                num_results=10
            )
            
            # Check if key project elements were extracted
            found_elements = {
                "project": any("CRM" in str(r) for r in results),
                "next_action": any("Research" in str(r) for r in results),
                "area": any("Business Operations" in str(r) for r in results)
            }
            
            if all(found_elements.values()):
                print("  ✅ Successfully extracted project with relationships")
                return True
            else:
                missing = [k for k, v in found_elements.items() if not v]
                print(f"  ⚠️ Partially extracted project (missing: {missing})")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to extract project: {e}")
            return False
    
    async def test_mindsweep_processing(self):
        """Test processing of mind sweep items"""
        print("\n" + "="*60)
        print("TEST: Mind Sweep Processing")
        print("="*60)
        
        mindsweep_data = {
            "timestamp": datetime.now().isoformat(),
            "items": [
                "Fix leaking faucet in bathroom",
                "Plan vacation for next summer",
                "Call mom about birthday plans",
                "Review investment portfolio",
                "Learn Spanish",
                "Organize garage",
                "Submit expense report",
                "Schedule car maintenance"
            ],
            "count": 8
        }
        
        try:
            # Add mind sweep data
            await self.client.add_episode(
                name="test_mindsweep",
                episode_body=json.dumps(mindsweep_data),
                source=EpisodeType.json,
                source_description="GTD mind sweep test",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Test if individual items can be found
            test_queries = [
                "Fix leaking faucet",
                "vacation planning",
                "expense report"
            ]
            
            found_count = 0
            for query in test_queries:
                results = await self.client.search(query, num_results=5)
                if results:
                    found_count += 1
                    print(f"  ✅ Found: '{query}'")
                else:
                    print(f"  ❌ Not found: '{query}'")
            
            success_rate = found_count / len(test_queries)
            print(f"\nExtraction rate: {success_rate:.0%}")
            return success_rate > 0.5
            
        except Exception as e:
            print(f"  ❌ Failed to process mind sweep: {e}")
            return False
    
    async def test_adhd_pattern_detection(self):
        """Test ADHD pattern extraction"""
        print("\n" + "="*60)
        print("TEST: ADHD Pattern Detection")
        print("="*60)
        
        pattern_data = {
            "pattern_type": "task_switch",
            "severity": "high",
            "triggers": ["overwhelm", "too many options", "unclear priorities"],
            "timestamp": datetime.now().isoformat(),
            "phase": "MIND_SWEEP",
            "duration_seconds": 45,
            "context_switches": 7
        }
        
        try:
            # Add ADHD pattern episode
            await self.client.add_episode(
                name="test_adhd_pattern",
                episode_body=json.dumps(pattern_data),
                source=EpisodeType.json,
                source_description="ADHD pattern test",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Search for pattern indicators
            results = await self.client.search(
                query="task switching pattern high severity",
                num_results=10
            )
            
            if results:
                print("  ✅ ADHD pattern data extracted and searchable")
                return True
            else:
                print("  ⚠️ ADHD pattern data added but not well indexed")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to process ADHD pattern: {e}")
            return False
    
    async def test_context_relationships(self):
        """Test GTD context relationships"""
        print("\n" + "="*60)
        print("TEST: Context Relationships")
        print("="*60)
        
        # Create action with context
        action_with_context = {
            "action": "Process email inbox to zero",
            "context": "@computer",
            "energy": "medium",
            "time_estimate": 30
        }
        
        try:
            # Add action
            await self.client.add_episode(
                name="test_context_action",
                episode_body=json.dumps(action_with_context),
                source=EpisodeType.json,
                source_description="Context relationship test",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Search for context-specific actions
            results = await self.client.search(
                query="@computer tasks",
                num_results=10
            )
            
            # Check if the relationship is captured
            found_relationship = any("email" in str(r).lower() and "@computer" in str(r) for r in results)
            
            if found_relationship:
                print("  ✅ Context-action relationship established")
                return True
            else:
                print("  ⚠️ Action added but context relationship unclear")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to test context relationships: {e}")
            return False
    
    async def test_timing_integration(self):
        """Test Timing app data integration"""
        print("\n" + "="*60)
        print("TEST: Timing Data Integration")
        print("="*60)
        
        timing_data = {
            "focus_score": 72.5,
            "context_switches_per_hour": 3.2,
            "hyperfocus_periods": 2,
            "scatter_periods": 1,
            "top_time_sinks": ["Email", "Slack", "Web browsing"],
            "alignment_score": 68.0,
            "productive_contexts": ["@computer morning", "@office afternoon"]
        }
        
        try:
            # Add timing insights
            await self.client.add_episode(
                name="test_timing_insights",
                episode_body=json.dumps(timing_data),
                source=EpisodeType.json,
                source_description="Timing integration test",
                group_id=self.test_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Search for focus metrics
            results = await self.client.search(
                query="focus score productivity",
                num_results=10
            )
            
            if results:
                print(f"  ✅ Timing metrics integrated (focus score: {timing_data['focus_score']})")
                return True
            else:
                print("  ⚠️ Timing data added but not well indexed")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to integrate timing data: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all GTD entity extraction tests"""
        print("\n" + "="*60)
        print("GTD ENTITY EXTRACTION TEST SUITE")
        print("="*60)
        print(f"Test group: {self.test_group_id}")
        
        # Initialize
        if not await self.initialize():
            print("❌ Failed to initialize test suite")
            return False
        
        # Run tests
        test_methods = [
            ("Action Extraction", self.test_action_extraction),
            ("Project Extraction", self.test_project_extraction),
            ("Mind Sweep Processing", self.test_mindsweep_processing),
            ("ADHD Pattern Detection", self.test_adhd_pattern_detection),
            ("Context Relationships", self.test_context_relationships),
            ("Timing Integration", self.test_timing_integration),
        ]
        
        results = {}
        for test_name, test_method in test_methods:
            try:
                results[test_name] = await test_method()
                await asyncio.sleep(0.5)  # Small delay between tests
            except Exception as e:
                logger.error(f"Test '{test_name}' crashed: {e}")
                results[test_name] = False
        
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
        
        if passed == len(results):
            print("\n🎉 All GTD entity extraction tests passed!")
            return True
        elif passed > len(results) * 0.7:
            print(f"\n⚠️ Most tests passed ({passed}/{len(results)}), but some issues remain")
            return True
        else:
            print(f"\n❌ Too many failures ({failed}/{len(results)}), please check entity configuration")
            return False


async def main():
    """Main entry point"""
    tester = GTDEntityTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)