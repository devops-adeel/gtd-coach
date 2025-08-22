#!/usr/bin/env python3
"""
Ultra-Simple Daily Clarify Command
Minimal decisions, maximum flow - optimized for ADHD
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.integrations.todoist import TodoistClient
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.deprecation.decorator import deprecate_daily_clarify


class DailyClarify:
    """Ultra-simple daily clarify - one decision per item"""
    
    def __init__(self):
        """Initialize with minimal setup"""
        self.logger = logging.getLogger(__name__)
        self.todoist = TodoistClient()
        
        # Optional Graphiti for future pattern tracking
        session_id = f"clarify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory = GraphitiMemory(session_id=session_id) if os.getenv('NEO4J_PASSWORD') else None
        
        # Deep work keywords - keep it simple
        self.deep_keywords = [
            'refactor', 'design', 'analyze', 'create', 'write', 
            'plan', 'research', 'build', 'architect', 'implement'
        ]
        
        # Track metrics for reality check
        self.metrics = {
            'inbox_count': 0,
            'processed': 0,
            'deleted': 0,
            'deep_work': 0,
            'quick_tasks': 0
        }
    
    def is_deep_work(self, content: str) -> bool:
        """Check if item needs deep focus time"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.deep_keywords)
    
    def process_inbox(self) -> Dict:
        """Process all inbox items with ONE decision each"""
        
        if not self.todoist.is_configured():
            print("❌ Todoist not configured. Set TODOIST_API_KEY in .env")
            return self.metrics
        
        # Get inbox items
        inbox_tasks = self.todoist.get_inbox_tasks()
        self.metrics['inbox_count'] = len(inbox_tasks)
        
        if not inbox_tasks:
            print("✅ Inbox already empty! Nothing to process.")
            return self.metrics
        
        print(f"\n📥 Found {len(inbox_tasks)} items in Todoist inbox")
        print("=" * 50)
        print("\n🎯 One decision per item: Keep or Delete?\n")
        
        # Process each item with minimal cognitive load
        for i, task in enumerate(inbox_tasks, 1):
            print(f"\n[{i}/{len(inbox_tasks)}] {task['content']}")
            
            # Single decision point
            keep = self.get_keep_decision()
            
            if keep:
                # Check if it's deep work
                is_deep = self.is_deep_work(task['content'])
                
                # Add to today with appropriate settings
                if is_deep and self.metrics['deep_work'] < 2:  # Max 2 deep work per day
                    self.todoist.add_to_today(task['content'], is_deep_work=True)
                    self.metrics['deep_work'] += 1
                    print("  → Added as DEEP WORK (2h block)")
                else:
                    self.todoist.add_to_today(task['content'], is_deep_work=False)
                    self.metrics['quick_tasks'] += 1
                    print("  → Added to today")
            else:
                self.metrics['deleted'] += 1
                print("  → Deleted")
            
            # Mark complete in inbox regardless (achieve inbox zero)
            self.todoist.mark_complete(task['id'])
            self.metrics['processed'] += 1
            
            # Break after every 5 items to prevent decision fatigue
            if i % 5 == 0 and i < len(inbox_tasks):
                print("\n--- Quick break! Take 30 seconds ---")
                input("Press Enter to continue...")
        
        return self.metrics
    
    def get_keep_decision(self) -> bool:
        """Get keep/delete decision from user"""
        while True:
            response = input("  Keep? (y/n or just Enter for yes): ").strip().lower()
            
            if response in ['', 'y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("  Please enter 'y' for yes or 'n' for no")
    
    def show_summary(self):
        """Show session summary"""
        print("\n" + "=" * 50)
        print("📊 CLARIFY COMPLETE!")
        print("=" * 50)
        
        print(f"\n✅ Processed: {self.metrics['processed']} items")
        print(f"🗑️  Deleted: {self.metrics['deleted']} items")
        print(f"🎯 Deep work blocks: {self.metrics['deep_work']}")
        print(f"📝 Quick tasks: {self.metrics['quick_tasks']}")
        
        if self.metrics['deleted'] > 0:
            deletion_rate = (self.metrics['deleted'] / self.metrics['inbox_count']) * 100
            print(f"\n💪 Deletion rate: {deletion_rate:.0f}% - Good job saying NO!")
        
        print("\n🎉 Inbox Zero achieved! Check your Today view in Todoist.")
    
    def save_metrics(self):
        """Save metrics for weekly review (optional)"""
        if not self.memory:
            return
        
        try:
            # Simple metrics storage
            episode_data = {
                "type": "daily_clarify",
                "date": datetime.now().isoformat(),
                "metrics": self.metrics
            }
            
            self.memory.add_episode(
                episode_data,
                f"Daily clarify: {self.metrics['processed']} items processed"
            )
            
            self.logger.info("Metrics saved to Graphiti")
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")
    
    @deprecate_daily_clarify
    def run(self):
        """Run the clarify session"""
        print("\n🌟 DAILY CLARIFY - Ultra Simple Mode")
        print("=====================================")
        print("Rules:")
        print("1. ONE decision per item: Keep or Delete")
        print("2. No categorization, no complex thinking")
        print("3. Maximum 2 deep work blocks per day")
        print("4. Quick break every 5 items")
        print("\nLet's achieve inbox zero!\n")
        
        try:
            # Process inbox
            self.process_inbox()
            
            # Show summary
            self.show_summary()
            
            # Optional: Save metrics
            self.save_metrics()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Session interrupted!")
            print(f"Processed {self.metrics['processed']} of {self.metrics['inbox_count']} items")
        except Exception as e:
            self.logger.error(f"Session failed: {e}")
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point"""
    import argparse
    from dotenv import load_dotenv
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Ultra-Simple Daily GTD Clarify")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run clarify session
    clarify = DailyClarify()
    clarify.run()


if __name__ == "__main__":
    main()