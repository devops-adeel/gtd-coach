#!/usr/bin/env python3
"""
Daily GTD-Timing Alignment Check
Compares yesterday's time tracking with today's GTD priorities
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.integrations.todoist import TodoistAPI
from gtd_coach.integrations.timing import TimingAPI
from gtd_coach.integrations.timing_comparison import (
    compare_time_with_priorities,
    generate_simple_time_summary,
    suggest_time_adjustments
)
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector
from gtd_coach.deprecation.decorator import deprecate_daily_alignment


class DailyAlignmentChecker:
    """Daily alignment checker for GTD and Timing data"""
    
    def __init__(self):
        """Initialize with API clients and configuration"""
        self.todoist = TodoistAPI()
        self.timing = TimingAPI()
        self.memory = GraphitiMemory() if os.getenv('NEO4J_PASSWORD') else None
        self.pattern_detector = ADHDPatternDetector()
        self.logger = logging.getLogger(__name__)
        
        # Data directory for storing results
        self.data_dir = Path.home() / "gtd-coach" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_yesterdays_time_data(self) -> Dict:
        """Fetch and analyze yesterday's time tracking data
        
        Returns:
            Dictionary with time analysis
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self.logger.info(f"Fetching time data for {yesterday}")
        
        # Get detailed time entries and analysis
        try:
            # Use async method if available
            if hasattr(self.timing, 'analyze_timing_patterns_async'):
                timing_data = await self.timing.analyze_timing_patterns_async()
            else:
                # Fallback to sync methods
                entries = self.timing.fetch_time_entries_last_week(max_entries=200)
                projects = self.timing.fetch_projects_last_week(min_minutes=5)
                
                # Filter to yesterday only
                yesterday_entries = [
                    e for e in entries
                    if e['start_time'] and yesterday in e['start_time']
                ]
                
                # Analyze context switches
                switch_analysis = self.timing.detect_context_switches(yesterday_entries)
                focus_metrics = self.timing.calculate_focus_metrics(switch_analysis)
                
                timing_data = {
                    'projects': projects,
                    'entries': yesterday_entries[:20],
                    'focus_metrics': focus_metrics,
                    'switch_analysis': switch_analysis
                }
            
            return timing_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch timing data: {e}")
            return {
                'projects': [],
                'entries': [],
                'focus_metrics': None,
                'switch_analysis': None
            }
    
    async def get_todays_priorities(self) -> Dict:
        """Fetch today's priorities and GTD data from Todoist
        
        Returns:
            Dictionary with Todoist data
        """
        if not self.todoist.is_configured():
            self.logger.warning("Todoist not configured")
            return {
                'priorities': [],
                'next_actions': [],
                'contexts': []
            }
        
        try:
            # Get today's priorities
            priorities = self.todoist.get_todays_priorities(limit=5)
            
            # Get next actions
            next_actions = self.todoist.get_next_actions(limit=10)
            
            # Get active GTD projects
            gtd_projects = self.todoist.get_gtd_projects()
            active_projects = [
                p for p in gtd_projects 
                if p.get('phase') in ['REFINE', 'REVISIT']
            ]
            
            return {
                'priorities': priorities,
                'next_actions': next_actions,
                'active_projects': active_projects[:5],
                'total_active': len(active_projects)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Todoist data: {e}")
            return {
                'priorities': [],
                'next_actions': [],
                'active_projects': []
            }
    
    def analyze_alignment(self, timing_data: Dict, todoist_data: Dict) -> Dict:
        """Analyze alignment between time spent and priorities
        
        Args:
            timing_data: Yesterday's timing data
            todoist_data: Today's priorities from Todoist
        
        Returns:
            Alignment analysis
        """
        # Use the comparison function from timing_comparison module
        if timing_data['projects'] and todoist_data['priorities']:
            comparison = compare_time_with_priorities(
                timing_data['projects'],
                todoist_data['priorities'],
                timing_data
            )
        else:
            comparison = {
                'aligned_projects': [],
                'untracked_priorities': todoist_data['priorities'],
                'time_sinks': timing_data['projects'][:5] if timing_data['projects'] else [],
                'alignment_score': 0,
                'recommendations': []
            }
        
        # Calculate uncategorized percentage
        total_hours = sum(p['time_spent'] for p in timing_data['projects']) if timing_data['projects'] else 0
        misc_hours = sum(
            p['time_spent'] for p in timing_data['projects']
            if 'misc' in p['name'].lower() or 'break' in p['name'].lower()
        ) if timing_data['projects'] else 0
        
        uncategorized_percent = (misc_hours / total_hours * 100) if total_hours > 0 else 0
        
        # Add ADHD-specific metrics if available
        adhd_insights = {}
        if timing_data.get('focus_metrics'):
            adhd_insights = {
                'focus_score': timing_data['focus_metrics']['focus_score'],
                'switches_per_hour': timing_data['focus_metrics']['switches_per_hour'],
                'hyperfocus_score': timing_data['focus_metrics']['hyperfocus_score'],
                'interpretation': timing_data['focus_metrics']['interpretation']
            }
        
        return {
            'comparison': comparison,
            'total_hours': round(total_hours, 1),
            'uncategorized_hours': round(misc_hours, 1),
            'uncategorized_percent': round(uncategorized_percent, 1),
            'adhd_insights': adhd_insights
        }
    
    def generate_report(self, timing_data: Dict, todoist_data: Dict, alignment: Dict) -> str:
        """Generate a formatted daily alignment report
        
        Args:
            timing_data: Yesterday's timing data
            todoist_data: Today's priorities
            alignment: Alignment analysis
        
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("📊 GTD-TIMING DAILY ALIGNMENT REPORT")
        lines.append("=" * 60)
        lines.append(f"📅 {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
        
        # Yesterday's Reality
        lines.append(f"\n📈 Yesterday's Reality ({alignment['total_hours']}h tracked):")
        lines.append("-" * 40)
        
        if timing_data['projects']:
            for project in timing_data['projects'][:5]:
                emoji = "✅" if project['time_spent'] > 1 else "⚠️" if project['time_spent'] > 0.5 else "❌"
                lines.append(f"  {emoji} {project['name']}: {project['time_spent']}h")
        else:
            lines.append("  No time data available")
        
        # Uncategorized time warning
        if alignment['uncategorized_percent'] > 20:
            lines.append(f"\n  ⚠️  {alignment['uncategorized_percent']}% uncategorized time!")
            lines.append("     Action: Review gray blocks in Timing app")
        
        # ADHD Insights
        if alignment['adhd_insights']:
            lines.append(f"\n🧠 Focus Analysis:")
            lines.append("-" * 40)
            insights = alignment['adhd_insights']
            lines.append(f"  • Focus Score: {insights['focus_score']}/100")
            lines.append(f"  • Context Switches: {insights['switches_per_hour']}/hour")
            lines.append(f"  • {insights['interpretation']}")
        
        # Today's Priorities
        if todoist_data['priorities']:
            lines.append(f"\n🎯 Today's GTD Priorities:")
            lines.append("-" * 40)
            for i, task in enumerate(todoist_data['priorities'], 1):
                priority_emoji = "🔴" if task.get('priority', 1) == 4 else "🟡" if task.get('priority', 1) == 3 else "⚪"
                lines.append(f"  {i}. {priority_emoji} {task['content']}")
        
        # Alignment Analysis
        if alignment['comparison']['alignment_score'] > 0:
            lines.append(f"\n📊 Alignment Score: {alignment['comparison']['alignment_score']}/100")
            lines.append("-" * 40)
            
            if alignment['comparison']['aligned_projects']:
                lines.append("  ✅ Aligned (time matches priority):")
                for item in alignment['comparison']['aligned_projects'][:3]:
                    lines.append(f"     • {item['priority']}: {item['time_spent']}h")
            
            if alignment['comparison']['untracked_priorities']:
                lines.append("  ⚠️  Untracked priorities:")
                for item in alignment['comparison']['untracked_priorities'][:3]:
                    content = item.get('task', item.get('content', 'Unknown'))
                    lines.append(f"     • {content}")
        
        # Recommendations
        if alignment['comparison'].get('recommendations'):
            lines.append(f"\n💡 Recommendations:")
            lines.append("-" * 40)
            for rec in alignment['comparison']['recommendations'][:3]:
                lines.append(f"  → {rec}")
        else:
            # Generic recommendations based on data
            lines.append(f"\n💡 Quick Tips:")
            lines.append("-" * 40)
            
            if alignment['uncategorized_percent'] > 30:
                lines.append("  → Spend 2 minutes categorizing yesterday's time")
            elif alignment['total_hours'] < 4:
                lines.append("  → Check that Timing is running during work")
            elif todoist_data['priorities']:
                lines.append("  → Focus on your top priority first thing")
            else:
                lines.append("  → Great tracking! Keep up the momentum")
        
        lines.append("\n" + "=" * 60 + "\n")
        
        return "\n".join(lines)
    
    async def save_to_memory(self, timing_data: Dict, todoist_data: Dict, alignment: Dict):
        """Save daily alignment data to Graphiti memory
        
        Args:
            timing_data: Yesterday's timing data
            todoist_data: Today's priorities
            alignment: Alignment analysis
        """
        if not self.memory:
            return
        
        try:
            # Create episode data
            episode_data = {
                "date": datetime.now().isoformat(),
                "yesterday": {
                    "total_hours": alignment['total_hours'],
                    "uncategorized_percent": alignment['uncategorized_percent'],
                    "top_projects": [p['name'] for p in timing_data['projects'][:3]] if timing_data['projects'] else [],
                    "focus_metrics": alignment['adhd_insights']
                },
                "today": {
                    "priorities": [p['content'] for p in todoist_data['priorities']],
                    "active_projects": todoist_data.get('total_active', 0)
                },
                "alignment": {
                    "score": alignment['comparison']['alignment_score'],
                    "aligned_count": len(alignment['comparison']['aligned_projects']),
                    "untracked_count": len(alignment['comparison']['untracked_priorities'])
                }
            }
            
            # Add to Graphiti
            await self.memory.add_alignment_episode(
                episode_data,
                f"Daily alignment for {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            self.logger.info("Saved alignment data to Graphiti memory")
            
        except Exception as e:
            self.logger.error(f"Failed to save to memory: {e}")
    
    def save_to_file(self, timing_data: Dict, todoist_data: Dict, alignment: Dict):
        """Save alignment data to JSON file for later analysis
        
        Args:
            timing_data: Yesterday's timing data
            todoist_data: Today's priorities
            alignment: Alignment analysis
        """
        try:
            # Prepare data for serialization
            save_data = {
                'timestamp': datetime.now().isoformat(),
                'yesterday': {
                    'total_hours': alignment['total_hours'],
                    'uncategorized_percent': alignment['uncategorized_percent'],
                    'projects': timing_data['projects'][:10] if timing_data['projects'] else [],
                    'focus_metrics': alignment['adhd_insights']
                },
                'today': {
                    'priorities': todoist_data['priorities'],
                    'active_projects': todoist_data.get('total_active', 0)
                },
                'alignment': {
                    'score': alignment['comparison']['alignment_score'],
                    'comparison': alignment['comparison']
                }
            }
            
            # Save to daily file
            filename = self.data_dir / f"alignment_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            # Also save to latest file for easy access
            latest_file = self.data_dir / "latest_alignment.json"
            with open(latest_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved alignment data to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save to file: {e}")
    
    @deprecate_daily_alignment
    async def run(self, notify: bool = False, email: bool = False) -> Dict:
        """Run the daily alignment check
        
        Args:
            notify: Whether to show macOS notification
            email: Whether to send email report
        
        Returns:
            Alignment results
        """
        print("\n⏳ Running daily alignment check...")
        
        # Check API configurations
        timing_configured = self.timing.is_configured()
        todoist_configured = self.todoist.is_configured()
        
        if not timing_configured:
            print("❌ Timing API not configured")
            return {}
        
        # Fetch data
        timing_data = await self.get_yesterdays_time_data()
        todoist_data = await self.get_todays_priorities() if todoist_configured else {
            'priorities': [],
            'next_actions': [],
            'active_projects': []
        }
        
        # Analyze alignment
        alignment = self.analyze_alignment(timing_data, todoist_data)
        
        # Generate report
        report = self.generate_report(timing_data, todoist_data, alignment)
        print(report)
        
        # Save data
        self.save_to_file(timing_data, todoist_data, alignment)
        
        # Save to memory if configured
        if self.memory:
            await self.save_to_memory(timing_data, todoist_data, alignment)
        
        # Send notifications if requested
        if notify and sys.platform == "darwin":
            self.send_notification(alignment)
        
        if email:
            self.send_email_report(report)
        
        return {
            'timing_data': timing_data,
            'todoist_data': todoist_data,
            'alignment': alignment
        }
    
    def send_notification(self, alignment: Dict):
        """Send macOS notification with alignment summary
        
        Args:
            alignment: Alignment analysis
        """
        try:
            import subprocess
            
            title = "GTD Daily Alignment"
            
            if alignment['uncategorized_percent'] > 30:
                message = f"⚠️ {alignment['uncategorized_percent']}% uncategorized time yesterday"
            elif alignment['comparison']['alignment_score'] > 70:
                message = f"✅ Great alignment! Score: {alignment['comparison']['alignment_score']}/100"
            else:
                message = f"📊 Alignment score: {alignment['comparison']['alignment_score']}/100"
            
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ])
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def send_email_report(self, report: str):
        """Send email report (placeholder for future implementation)
        
        Args:
            report: Report text
        """
        # TODO: Implement email sending
        self.logger.info("Email report feature not yet implemented")


def main():
    """Main entry point for daily alignment command"""
    import argparse
    from dotenv import load_dotenv
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Daily GTD-Timing alignment check")
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Show macOS notification"
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send email report"
    )
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run alignment check
    checker = DailyAlignmentChecker()
    asyncio.run(checker.run(notify=args.notify, email=args.email))


if __name__ == "__main__":
    main()