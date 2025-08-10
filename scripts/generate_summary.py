#!/usr/bin/env python3
"""
Generate Weekly Summary from Graphiti Memory
Analyzes GTD review patterns and provides ADHD insights
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict

from gtd_coach.integrations.graphiti import GraphitiRetriever
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector
from gtd_coach.integrations.timing import TimingAPI
from gtd_coach.integrations.timing_comparison import compare_time_with_priorities, format_comparison_report

logger = logging.getLogger(__name__)

# Handle Docker vs local paths
def get_base_dir():
    if os.environ.get("IN_DOCKER"):
        return Path("/app")
    else:
        return Path.home() / "gtd-coach"


class WeeklySummaryGenerator:
    """Generates weekly insights from Graphiti memory"""
    
    def __init__(self):
        self.retriever = GraphitiRetriever()
        self.pattern_detector = ADHDPatternDetector()
        self.timing_api = TimingAPI()
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
            "timing_analysis": {
                "focus_score": None,
                "switches_per_hour": None,
                "alignment_score": None,
                "time_comparison": None
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
        await self._analyze_timing_data(days)
        await self._calculate_productivity_metrics()
        await self._generate_adhd_insights()
        
        # Generate markdown report
        return self._format_markdown_report()
    
    async def _gather_session_data(self, days: int) -> None:
        """Gather session data from file system (temporary until MCP integration)"""
        # TODO: Replace with GraphitiRetriever.get_recent_sessions() when MCP is ready
        
        data_dir = get_base_dir() / "data"
        logs_dir = get_base_dir() / "logs"
        
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
        
        data_dir = get_base_dir() / "data"
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
        
        data_dir = get_base_dir() / "data"
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
    
    async def _analyze_timing_data(self, days: int) -> None:
        """Analyze timing data and correlations"""
        if not self.timing_api.is_configured():
            return
        
        try:
            # Fetch timing analysis
            timing_data = await self.timing_api.analyze_timing_patterns_async()
            
            if timing_data and timing_data.get('focus_metrics'):
                # Store focus metrics
                self.summary_data["timing_analysis"]["focus_score"] = timing_data['focus_metrics'].get('focus_score')
                self.summary_data["timing_analysis"]["switches_per_hour"] = timing_data['focus_metrics'].get('switches_per_hour')
                
                # Analyze ADHD patterns from timing
                adhd_analysis = self.pattern_detector.analyze_timing_switches(timing_data)
                
                # Store timing-specific patterns
                for indicator in adhd_analysis.get('adhd_indicators', []):
                    if indicator['type'] == 'excessive_switching':
                        self.summary_data["patterns"]["task_switches"].append({
                            'source': 'timing',
                            'severity': indicator['severity'],
                            'value': indicator['value']
                        })
                
                # Get priorities from most recent session for comparison
                if self.summary_data["sessions"]:
                    latest_session = self.summary_data["sessions"][0]
                    priorities = latest_session["data"].get("priorities", [])
                    
                    if priorities and timing_data.get('projects'):
                        # Compare time with priorities
                        comparison = compare_time_with_priorities(
                            timing_data['projects'],
                            priorities,
                            timing_data
                        )
                        self.summary_data["timing_analysis"]["alignment_score"] = comparison['alignment_score']
                        self.summary_data["timing_analysis"]["time_comparison"] = comparison
        
        except Exception as e:
            logger.error(f"Failed to analyze timing data: {e}")
    
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
        
        # Timing-based insights
        timing_analysis = self.summary_data["timing_analysis"]
        if timing_analysis.get("focus_score") is not None:
            focus_score = timing_analysis["focus_score"]
            if focus_score < 40:
                insights.append({
                    "type": "low_timing_focus",
                    "message": f"Timing data shows focus score of {focus_score} - severe context switching detected",
                    "severity": "high"
                })
            elif focus_score > 70:
                insights.append({
                    "type": "good_timing_focus",
                    "message": f"Strong focus score of {focus_score} from Timing data",
                    "severity": "positive"
                })
        
        if timing_analysis.get("alignment_score") is not None:
            alignment = timing_analysis["alignment_score"]
            if alignment < 40:
                insights.append({
                    "type": "poor_alignment",
                    "message": f"Only {alignment:.0f}% of time spent on stated priorities",
                    "severity": "high"
                })
            elif alignment > 70:
                insights.append({
                    "type": "good_alignment",
                    "message": f"Excellent: {alignment:.0f}% of time aligned with priorities",
                    "severity": "positive"
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
        
        # Timing Analysis (if available)
        timing_analysis = self.summary_data["timing_analysis"]
        if timing_analysis.get("focus_score") is not None:
            report.append("\n## ⏱️ Timing App Analysis\n")
            
            # Focus metrics
            report.append("### Focus Metrics")
            focus_score = timing_analysis["focus_score"]
            emoji = "🟢" if focus_score > 70 else "🟡" if focus_score > 40 else "🔴"
            report.append(f"- **Focus Score**: {emoji} {focus_score}/100")
            
            if timing_analysis.get("switches_per_hour") is not None:
                report.append(f"- **Context Switches**: {timing_analysis['switches_per_hour']:.1f}/hour")
            
            # Alignment analysis
            if timing_analysis.get("alignment_score") is not None:
                report.append("\n### Priority Alignment")
                alignment = timing_analysis["alignment_score"]
                emoji = "✅" if alignment > 70 else "⚠️" if alignment > 40 else "❌"
                report.append(f"- **Alignment Score**: {emoji} {alignment:.0f}%")
            
            # Time comparison details
            if timing_analysis.get("time_comparison"):
                comparison = timing_analysis["time_comparison"]
                
                if comparison.get("time_sinks"):
                    report.append("\n### Major Time Sinks")
                    for sink in comparison["time_sinks"][:3]:
                        report.append(f"- {sink['name']}: {sink['time_spent']:.1f}h ({sink.get('category', 'other')})")
                
                if comparison.get("recommendations"):
                    report.append("\n### Time Management Recommendations")
                    for rec in comparison["recommendations"][:3]:
                        report.append(f"- {rec}")
        
        # ADHD Patterns
        report.append("\n## 🎯 ADHD Pattern Analysis\n")
        
        # Task switching
        switches = self.summary_data["patterns"]["task_switches"]
        if switches:
            report.append(f"### Task Switching")
            
            # Separate timing vs mindsweep switches
            timing_switches = [s for s in switches if s.get('source') == 'timing']
            mindsweep_switches = [s for s in switches if s.get('source') != 'timing']
            
            if timing_switches:
                report.append(f"- **From Timing Data**: {len(timing_switches)} patterns detected")
            if mindsweep_switches:
                report.append(f"- **From Mind Sweep**: {len(mindsweep_switches)} switches")
            
            # Most common switch patterns
            switch_patterns = Counter()
            for switch in switches:
                if 'from_topic' in switch:
                    pattern = f"{switch.get('from_topic', 'unknown')} → {switch.get('to_topic', 'unknown')}"
                    switch_patterns[pattern] += 1
            
            if switch_patterns:
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
    output_dir = get_base_dir() / "summaries"
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