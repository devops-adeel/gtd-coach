#!/usr/bin/env python3
"""
Generate Weekly Summary from Graphiti Memory
Analyzes GTD review patterns and provides ADHD insights
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict

from graphiti_integration import GraphitiRetriever
from adhd_patterns import ADHDPatternDetector

logger = logging.getLogger(__name__)


class WeeklySummaryGenerator:
    """Generates weekly insights from Graphiti memory"""
    
    def __init__(self):
        self.retriever = GraphitiRetriever()
        self.pattern_detector = ADHDPatternDetector()
        self.summary_data = {
            "period": {
                "start": None,
                "end": None,
                "days": 7
            },
            "sessions": [],
            "patterns": {
                "task_switches": [],
                "coherence_scores": [],
                "focus_events": []
            },
            "mindsweep_analysis": {
                "total_items": 0,
                "items_by_topic": Counter(),
                "average_per_session": 0,
                "common_themes": []
            },
            "productivity_metrics": {
                "completion_rate": 0,
                "average_session_duration": 0,
                "phase_efficiency": {}
            },
            "adhd_insights": []
        }
    
    async def generate_summary(self, days: int = 7) -> str:
        """
        Generate a weekly summary report
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Markdown-formatted summary report
        """
        self.summary_data["period"]["days"] = days
        self.summary_data["period"]["end"] = datetime.now()
        self.summary_data["period"]["start"] = datetime.now() - timedelta(days=days)
        
        # Gather data from Graphiti
        await self._gather_session_data(days)
        await self._analyze_patterns(days)
        await self._analyze_mindsweep_trends(days)
        await self._calculate_productivity_metrics()
        await self._generate_adhd_insights()
        
        # Generate markdown report
        return self._format_markdown_report()
    
    async def _gather_session_data(self, days: int) -> None:
        """Gather session data from file system (temporary until MCP integration)"""
        # TODO: Replace with GraphitiRetriever.get_recent_sessions() when MCP is ready
        
        data_dir = Path.home() / "gtd-coach" / "data"
        logs_dir = Path.home() / "gtd-coach" / "logs"
        
        # Get recent review logs
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for log_file in sorted(logs_dir.glob("review_*.json"), reverse=True):
            try:
                with open(log_file, 'r') as f:
                    session_data = json.load(f)
                
                # Parse timestamp from filename
                timestamp_str = log_file.stem.split('_', 1)[1]
                session_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if session_date >= cutoff_date:
                    self.summary_data["sessions"].append({
                        "date": session_date,
                        "data": session_data
                    })
            except Exception as e:
                logger.error(f"Failed to load session {log_file}: {e}")
    
    async def _analyze_patterns(self, days: int) -> None:
        """Analyze behavioral patterns from Graphiti batch files"""
        # TODO: Replace with GraphitiRetriever.search_patterns() when MCP is ready
        
        data_dir = Path.home() / "gtd-coach" / "data"
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Load Graphiti batch files
        for batch_file in data_dir.glob("graphiti_batch_*.json"):
            try:
                with open(batch_file, 'r') as f:
                    batch_data = json.load(f)
                
                for episode in batch_data.get("episodes", []):
                    if episode["type"] == "behavior_pattern":
                        pattern_data = episode["data"]
                        
                        if pattern_data["pattern_type"] == "task_switch":
                            self.summary_data["patterns"]["task_switches"].append(pattern_data)
                        elif pattern_data["pattern_type"] == "low_coherence":
                            self.summary_data["patterns"]["coherence_scores"].append(
                                pattern_data["score"]
                            )
                        elif pattern_data["pattern_type"] == "focus_event":
                            self.summary_data["patterns"]["focus_events"].append(pattern_data)
                            
            except Exception as e:
                logger.error(f"Failed to load batch file {batch_file}: {e}")
    
    async def _analyze_mindsweep_trends(self, days: int) -> None:
        """Analyze mindsweep trends from saved data"""
        # TODO: Replace with GraphitiRetriever.get_mindsweep_trends() when MCP is ready
        
        data_dir = Path.home() / "gtd-coach" / "data"
        cutoff_date = datetime.now() - timedelta(days=days)
        
        all_items = []
        session_counts = []
        
        for mindsweep_file in sorted(data_dir.glob("mindsweep_*.json"), reverse=True):
            try:
                # Parse timestamp
                timestamp_str = mindsweep_file.stem.split('_', 1)[1]
                file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if file_date >= cutoff_date:
                    with open(mindsweep_file, 'r') as f:
                        data = json.load(f)
                    
                    items = data.get("items", [])
                    all_items.extend(items)
                    session_counts.append(len(items))
                    
                    # Categorize items by topic
                    for item in items:
                        topic = self.pattern_detector._categorize_topic(item.lower())
                        self.summary_data["mindsweep_analysis"]["items_by_topic"][topic] += 1
                        
            except Exception as e:
                logger.error(f"Failed to load mindsweep file {mindsweep_file}: {e}")
        
        if session_counts:
            self.summary_data["mindsweep_analysis"]["total_items"] = sum(session_counts)
            self.summary_data["mindsweep_analysis"]["average_per_session"] = (
                sum(session_counts) / len(session_counts)
            )
        
        # Find common themes (most frequent words)
        if all_items:
            word_freq = Counter()
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            
            for item in all_items:
                words = item.lower().split()
                word_freq.update(w for w in words if w not in stop_words and len(w) > 3)
            
            self.summary_data["mindsweep_analysis"]["common_themes"] = [
                word for word, _ in word_freq.most_common(10)
            ]
    
    async def _calculate_productivity_metrics(self) -> None:
        """Calculate productivity metrics from session data"""
        if not self.summary_data["sessions"]:
            return
        
        total_duration = 0
        phase_durations = defaultdict(list)
        completed_sessions = 0
        
        for session in self.summary_data["sessions"]:
            review_data = session["data"].get("review_data", {})
            
            # Session completion
            if review_data.get("phase_durations", {}).get("Wrap-up"):
                completed_sessions += 1
            
            # Phase durations
            for phase, duration in review_data.get("phase_durations", {}).items():
                phase_durations[phase].append(duration)
                total_duration += duration
        
        # Calculate metrics
        num_sessions = len(self.summary_data["sessions"])
        
        self.summary_data["productivity_metrics"]["completion_rate"] = (
            (completed_sessions / num_sessions * 100) if num_sessions > 0 else 0
        )
        
        self.summary_data["productivity_metrics"]["average_session_duration"] = (
            (total_duration / 60 / num_sessions) if num_sessions > 0 else 0
        )
        
        # Phase efficiency
        for phase, durations in phase_durations.items():
            if durations:
                avg_duration = sum(durations) / len(durations) / 60  # Convert to minutes
                self.summary_data["productivity_metrics"]["phase_efficiency"][phase] = {
                    "average_minutes": round(avg_duration, 1),
                    "sessions": len(durations)
                }
    
    async def _generate_adhd_insights(self) -> None:
        """Generate ADHD-specific insights from patterns"""
        insights = []
        
        # Task switching analysis
        switch_count = len(self.summary_data["patterns"]["task_switches"])
        if switch_count > 0:
            sessions_with_data = len([s for s in self.summary_data["sessions"] 
                                    if s["data"].get("review_data", {}).get("items_captured", 0) > 0])
            
            if sessions_with_data > 0:
                avg_switches = switch_count / sessions_with_data
                
                if avg_switches > 5:
                    insights.append({
                        "type": "high_task_switching",
                        "message": f"You averaged {avg_switches:.1f} topic switches per mind sweep. Consider grouping related items together.",
                        "severity": "medium"
                    })
                else:
                    insights.append({
                        "type": "good_focus",
                        "message": f"Great focus! Only {avg_switches:.1f} topic switches per session on average.",
                        "severity": "positive"
                    })
        
        # Coherence analysis
        coherence_scores = self.summary_data["patterns"]["coherence_scores"]
        if coherence_scores:
            avg_coherence = sum(coherence_scores) / len(coherence_scores)
            
            if avg_coherence < 0.5:
                insights.append({
                    "type": "low_coherence",
                    "message": "Your mind sweeps show fragmented thinking patterns. Try categorizing thoughts before capture.",
                    "severity": "high"
                })
        
        # Completion rate
        completion_rate = self.summary_data["productivity_metrics"]["completion_rate"]
        if completion_rate < 80:
            insights.append({
                "type": "incomplete_sessions",
                "message": f"Only {completion_rate:.0f}% of reviews were completed. Set stronger boundaries around your review time.",
                "severity": "medium"
            })
        elif completion_rate == 100:
            insights.append({
                "type": "perfect_completion",
                "message": "Perfect completion rate! Your time-boxing discipline is excellent.",
                "severity": "positive"
            })
        
        # Item capture trends
        avg_items = self.summary_data["mindsweep_analysis"]["average_per_session"]
        if avg_items > 20:
            insights.append({
                "type": "high_capture_volume",
                "message": f"Averaging {avg_items:.0f} items per mind sweep. Consider more frequent brain dumps throughout the week.",
                "severity": "low"
            })
        
        self.summary_data["adhd_insights"] = insights
    
    def _format_markdown_report(self) -> str:
        """Format the summary data as a markdown report"""
        report = []
        
        # Header
        report.append("# GTD Weekly Review Summary")
        report.append(f"\n**Period**: {self.summary_data['period']['start'].strftime('%Y-%m-%d')} to {self.summary_data['period']['end'].strftime('%Y-%m-%d')}")
        report.append(f"**Sessions**: {len(self.summary_data['sessions'])}\n")
        
        # Productivity Metrics
        report.append("## 📊 Productivity Metrics\n")
        metrics = self.summary_data["productivity_metrics"]
        report.append(f"- **Completion Rate**: {metrics['completion_rate']:.0f}%")
        report.append(f"- **Average Session Duration**: {metrics['average_session_duration']:.1f} minutes")
        
        if metrics["phase_efficiency"]:
            report.append("\n### Phase Efficiency")
            for phase, data in metrics["phase_efficiency"].items():
                report.append(f"- **{phase}**: {data['average_minutes']} min average")
        
        # Mind Sweep Analysis
        report.append("\n## 🧠 Mind Sweep Analysis\n")
        analysis = self.summary_data["mindsweep_analysis"]
        report.append(f"- **Total Items Captured**: {analysis['total_items']}")
        report.append(f"- **Average per Session**: {analysis['average_per_session']:.1f}")
        
        if analysis["items_by_topic"]:
            report.append("\n### Topics Distribution")
            for topic, count in analysis["items_by_topic"].most_common():
                percentage = (count / analysis['total_items'] * 100) if analysis['total_items'] > 0 else 0
                report.append(f"- **{topic.title()}**: {count} items ({percentage:.0f}%)")
        
        if analysis["common_themes"]:
            report.append("\n### Common Themes")
            report.append(", ".join(analysis["common_themes"][:5]))
        
        # ADHD Patterns
        report.append("\n## 🎯 ADHD Pattern Analysis\n")
        
        # Task switching
        switches = self.summary_data["patterns"]["task_switches"]
        if switches:
            report.append(f"### Task Switching")
            report.append(f"- **Total Switches**: {len(switches)}")
            
            # Most common switch patterns
            switch_patterns = Counter()
            for switch in switches:
                pattern = f"{switch.get('from_topic', 'unknown')} → {switch.get('to_topic', 'unknown')}"
                switch_patterns[pattern] += 1
            
            report.append("- **Common Patterns**:")
            for pattern, count in switch_patterns.most_common(3):
                report.append(f"  - {pattern}: {count} times")
        
        # Coherence scores
        coherence_scores = self.summary_data["patterns"]["coherence_scores"]
        if coherence_scores:
            avg_coherence = sum(coherence_scores) / len(coherence_scores)
            report.append(f"\n### Coherence Score")
            report.append(f"- **Average**: {avg_coherence:.2f}/1.0")
        
        # Insights and Recommendations
        report.append("\n## 💡 Insights & Recommendations\n")
        
        insights_by_severity = defaultdict(list)
        for insight in self.summary_data["adhd_insights"]:
            insights_by_severity[insight["severity"]].append(insight["message"])
        
        # Positive insights first
        if insights_by_severity["positive"]:
            report.append("### ✅ What's Working Well")
            for message in insights_by_severity["positive"]:
                report.append(f"- {message}")
        
        # Areas for improvement
        if insights_by_severity["high"] or insights_by_severity["medium"]:
            report.append("\n### ⚠️ Areas for Improvement")
            for message in insights_by_severity["high"]:
                report.append(f"- **High Priority**: {message}")
            for message in insights_by_severity["medium"]:
                report.append(f"- {message}")
        
        # Low priority suggestions
        if insights_by_severity["low"]:
            report.append("\n### 💭 Suggestions")
            for message in insights_by_severity["low"]:
                report.append(f"- {message}")
        
        # Footer
        report.append("\n---")
        report.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(report)


async def main():
    """Generate and save weekly summary"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 Generating GTD Weekly Summary...")
    
    generator = WeeklySummaryGenerator()
    
    # Generate summary for last 7 days
    summary = await generator.generate_summary(days=7)
    
    # Save to file
    output_dir = Path.home() / "gtd-coach" / "summaries"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"weekly_summary_{timestamp}.md"
    
    with open(output_file, 'w') as f:
        f.write(summary)
    
    print(f"\n✅ Summary saved to: {output_file}")
    print("\n" + "="*50)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())