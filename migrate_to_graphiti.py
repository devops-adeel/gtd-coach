#!/usr/bin/env python3
"""
Migration script to import existing JSON data into Graphiti
Supports incremental migration with cost estimation and progress tracking
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from graphiti_client import GraphitiClient
from graphiti_core.nodes import EpisodeType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GraphitiMigrator:
    """Handles migration of JSON data to Graphiti"""
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize the migrator
        
        Args:
            dry_run: If True, only simulate migration without making changes
        """
        self.dry_run = dry_run
        self.processed_files = []
        self.failed_files = []
        self.cost_estimate = 0.0
        self.graphiti_client = None
        
    async def initialize(self):
        """Initialize Graphiti client if not in dry run mode"""
        if not self.dry_run:
            try:
                client_instance = GraphitiClient()
                self.graphiti_client = await client_instance.initialize()
                logger.info("✅ Graphiti client initialized for migration")
            except Exception as e:
                logger.error(f"Failed to initialize Graphiti: {e}")
                raise
    
    def _load_migration_state(self, state_file: Path) -> Dict:
        """Load migration state from file"""
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return {'processed': [], 'failed': [], 'last_run': None}
    
    def _save_migration_state(self, state_file: Path, state: Dict):
        """Save migration state to file"""
        state['last_run'] = datetime.now().isoformat()
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    async def estimate_migration_cost(self, data_dir: Path) -> tuple[int, float]:
        """
        Estimate the cost of migrating all JSON files
        
        Args:
            data_dir: Directory containing JSON files
            
        Returns:
            Tuple of (total_episodes, estimated_cost_usd)
        """
        print("\n" + "="*60)
        print("MIGRATION COST ESTIMATION")
        print("="*60)
        
        total_episodes = 0
        total_tokens = 0
        file_count = 0
        
        # Scan all JSON files
        json_files = sorted(data_dir.glob("*.json"))
        
        for json_file in json_files:
            # Skip non-Graphiti files
            if not any(prefix in json_file.name for prefix in ['graphiti_batch_', 'mindsweep_', 'priorities_']):
                continue
                
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Count episodes
                if 'episodes' in data:
                    episodes = data['episodes']
                elif isinstance(data, list):
                    episodes = data
                else:
                    episodes = [data]
                
                episode_count = len(episodes)
                total_episodes += episode_count
                
                # Estimate tokens (rough approximation)
                # Each episode typically uses ~100-200 tokens for processing
                for episode in episodes:
                    episode_str = json.dumps(episode)
                    # Rough estimate: 4 characters = 1 token
                    tokens = len(episode_str) // 4
                    # Add overhead for LLM processing
                    tokens += 150  # Base processing cost
                    total_tokens += tokens
                
                file_count += 1
                
            except Exception as e:
                logger.warning(f"Error reading {json_file.name}: {e}")
                continue
        
        # Calculate costs (OpenAI pricing as of 2024)
        # text-embedding-3-small: $0.00002 per 1K tokens
        # gpt-4.1-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        
        embedding_cost = (total_tokens / 1000) * 0.00002
        
        # Assume 20% of input tokens for output
        input_tokens = total_tokens
        output_tokens = total_tokens * 0.2
        
        llm_input_cost = (input_tokens / 1_000_000) * 0.15
        llm_output_cost = (output_tokens / 1_000_000) * 0.60
        
        total_cost = embedding_cost + llm_input_cost + llm_output_cost
        
        print(f"\n📊 Migration Statistics:")
        print(f"  - Files to process: {file_count}")
        print(f"  - Total episodes: {total_episodes}")
        print(f"  - Estimated tokens: {total_tokens:,}")
        print(f"\n💰 Cost Breakdown:")
        print(f"  - Embeddings: ${embedding_cost:.4f}")
        print(f"  - LLM Processing: ${llm_input_cost + llm_output_cost:.4f}")
        print(f"  - Total Estimated Cost: ${total_cost:.2f}")
        print(f"\n⏱️ Estimated Time: ~{total_episodes * 0.5:.1f} seconds")
        
        return total_episodes, total_cost
    
    async def migrate_file(self, json_file: Path) -> bool:
        """
        Migrate a single JSON file to Graphiti
        
        Args:
            json_file: Path to the JSON file
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            print(f"  [DRY RUN] Would migrate: {json_file.name}")
            return True
        
        if not self.graphiti_client:
            logger.error("Graphiti client not initialized")
            return False
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Determine the structure of the file
            if 'episodes' in data:
                # Graphiti batch file
                episodes = data['episodes']
                group_id = data.get('group_id', f"migrated_{json_file.stem}")
                session_id = data.get('session_id', json_file.stem)
            elif 'items' in data:
                # Mindsweep file
                episodes = [{
                    'type': 'mindsweep_capture',
                    'phase': 'MIND_SWEEP',
                    'data': data,
                    'timestamp': data.get('timestamp', datetime.now().isoformat())
                }]
                group_id = f"migrated_mindsweep_{json_file.stem}"
                session_id = json_file.stem
            elif 'priorities' in data:
                # Priorities file
                episodes = [{
                    'type': 'priorities',
                    'phase': 'PRIORITIZATION',
                    'data': data,
                    'timestamp': data.get('timestamp', datetime.now().isoformat())
                }]
                group_id = f"migrated_priorities_{json_file.stem}"
                session_id = json_file.stem
            else:
                # Unknown format, treat as single episode
                episodes = [data] if isinstance(data, dict) else data
                group_id = f"migrated_{json_file.stem}"
                session_id = json_file.stem
            
            # Process each episode
            success_count = 0
            for episode in episodes:
                try:
                    # Determine episode type
                    episode_type = episode.get('type', 'unknown')
                    
                    # Map to Graphiti source type
                    if episode_type == 'interaction':
                        source = EpisodeType.message
                    elif episode_type in ['timing_analysis', 'session_summary', 'mindsweep_capture', 'priorities']:
                        source = EpisodeType.json
                    else:
                        source = EpisodeType.text
                    
                    # Extract timestamp
                    timestamp_str = episode.get('timestamp', datetime.now().isoformat())
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                    except:
                        timestamp = datetime.now(timezone.utc)
                    
                    # Create episode in Graphiti
                    await self.graphiti_client.add_episode(
                        name=f"{episode_type}_{session_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                        episode_body=json.dumps(episode.get('data', episode)),
                        source=source,
                        source_description=f"Migrated from {json_file.name}",
                        group_id=group_id,
                        reference_time=timestamp
                    )
                    
                    success_count += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to migrate episode from {json_file.name}: {e}")
                    continue
            
            if success_count > 0:
                print(f"  ✅ {json_file.name}: Migrated {success_count}/{len(episodes)} episodes")
                return True
            else:
                print(f"  ❌ {json_file.name}: Failed to migrate any episodes")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process {json_file.name}: {e}")
            print(f"  ❌ {json_file.name}: {e}")
            return False
    
    async def migrate_incrementally(self, data_dir: Path, batch_size: int = 5):
        """
        Migrate files in small batches with progress tracking
        
        Args:
            data_dir: Directory containing JSON files
            batch_size: Number of files to process per batch
        """
        print("\n" + "="*60)
        print("INCREMENTAL MIGRATION")
        print("="*60)
        
        # Create/load migration state
        state_file = data_dir / ".migration_state.json"
        state = self._load_migration_state(state_file)
        
        # Get files to process
        json_files = sorted(data_dir.glob("*.json"))
        files_to_process = [
            f for f in json_files
            if f.name not in state['processed']
            and f.name not in state['failed']
            and not f.name.startswith('.')
            and any(prefix in f.name for prefix in ['graphiti_batch_', 'mindsweep_', 'priorities_'])
        ]
        
        if not files_to_process:
            print("✅ All files have been processed!")
            return
        
        print(f"📁 Found {len(files_to_process)} files to migrate")
        print(f"📦 Processing in batches of {batch_size}")
        
        if not self.dry_run:
            await self.initialize()
        
        # Process in batches
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(files_to_process) + batch_size - 1) // batch_size
            
            print(f"\n🔄 Processing batch {batch_num}/{total_batches}...")
            
            for json_file in batch:
                success = await self.migrate_file(json_file)
                
                if success:
                    state['processed'].append(json_file.name)
                    self.processed_files.append(json_file.name)
                else:
                    state['failed'].append(json_file.name)
                    self.failed_files.append(json_file.name)
                
                # Save state after each file
                self._save_migration_state(state_file, state)
            
            # Pause between batches
            if i + batch_size < len(files_to_process):
                print(f"\n⏸️ Pausing between batches (2 seconds)...")
                await asyncio.sleep(2)
        
        # Final summary
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"✅ Successfully migrated: {len(self.processed_files)} files")
        print(f"❌ Failed: {len(self.failed_files)} files")
        
        if self.failed_files:
            print("\nFailed files:")
            for f in self.failed_files:
                print(f"  - {f}")
            print("\nYou can retry failed files by running the migration again.")


async def main():
    """Main entry point for the migration script"""
    print("\n" + "="*60)
    print("GRAPHITI MIGRATION TOOL")
    print("="*60)
    print("Migrate existing JSON data to Neo4j via Graphiti")
    
    # Load environment
    load_dotenv('.env.graphiti')
    
    # Determine mode
    dry_run = os.getenv('MIGRATION_DRY_RUN', 'true').lower() == 'true'
    batch_size = int(os.getenv('MIGRATION_BATCH_SIZE', '5'))
    
    if dry_run:
        print("\n⚠️ Running in DRY RUN mode - no changes will be made")
        print("   Set MIGRATION_DRY_RUN=false in .env.graphiti to perform actual migration")
    else:
        print("\n🚀 Running in LIVE mode - data will be migrated to Neo4j")
    
    # Set data directory
    if os.environ.get("IN_DOCKER"):
        data_dir = Path("/app/data")
    else:
        data_dir = Path.home() / "gtd-coach" / "data"
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return 1
    
    # Create migrator
    migrator = GraphitiMigrator(dry_run=dry_run)
    
    # Estimate costs
    total_episodes, estimated_cost = await migrator.estimate_migration_cost(data_dir)
    
    if total_episodes == 0:
        print("\n✅ No data to migrate!")
        return 0
    
    # Confirm with user
    print("\n" + "="*60)
    if dry_run:
        response = input("\nProceed with DRY RUN? (y/n): ")
    else:
        print(f"⚠️ This will cost approximately ${estimated_cost:.2f} in OpenAI API fees")
        response = input("\nProceed with LIVE migration? (y/n): ")
    
    if response.lower() != 'y':
        print("Migration cancelled.")
        return 0
    
    # Run migration
    await migrator.migrate_incrementally(data_dir, batch_size)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)