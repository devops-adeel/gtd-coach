#!/usr/bin/env python3
"""
Evaluation Analytics and Insight Generation
Integrates with Langfuse for metrics and generates actionable insights
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class EvaluationAnalytics:
    """Analyzes evaluation data and generates insights"""
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize evaluation analytics
        
        Args:
            data_dir: Directory containing evaluation data
        """
        self.data_dir = data_dir or Path.home() / "gtd-coach" / "data"
        self.insights_cache = []
        self.langfuse_enabled = self._check_langfuse_config()
        
    def _check_langfuse_config(self) -> bool:
        """Check if Langfuse is configured"""
        return bool(os.environ.get('LANGFUSE_PUBLIC_KEY'))
    
    def fetch_langfuse_scores(self, session_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch scores from Langfuse API
        
        Args:
            session_ids: Optional list of session IDs to fetch
            
        Returns:
            Dictionary of scores by session
        """
        if not self.langfuse_enabled:
            logger.info("Langfuse not configured, using local data only")
            return {}
        
        try:
            from langfuse import Langfuse
            langfuse = Langfuse()
            
            # Note: This is a simplified version
            # In production, you'd use the Langfuse API to fetch scores
            # For now, we'll return a placeholder
            
            logger.info("Langfuse integration available for score fetching")
            return {}
            
        except ImportError:
            logger.warning("Langfuse not installed")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch Langfuse scores: {e}")
            return {}
    
    def calculate_trends(self, values: List[float], window_size: int = 7) -> Dict[str, Any]:
        """
        Calculate trend statistics using simple linear regression
        
        Args:
            values: List of metric values
            window_size: Window for trend calculation
            
        Returns:
            Trend statistics
        """
        if not values or len(values) < 3:
            return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0}
        
        # Use recent window
        recent_values = values[-window_size:] if len(values) > window_size else values
        
        # Linear regression
        x = np.arange(len(recent_values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_values)
        
        # Classify trend
        if abs(slope) < 0.01:
            trend = 'stable'
        elif slope > 0:
            trend = 'improving'
        else:
            trend = 'declining'
        
        # Calculate percentage change
        if recent_values[0] != 0:
            pct_change = ((recent_values[-1] - recent_values[0]) / recent_values[0]) * 100
        else:
            pct_change = 0
        
        return {
            'trend': trend,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'pct_change': pct_change,
            'prediction': intercept + slope * len(recent_values)  # Next value prediction
        }
    
    def generate_insights(self, pattern_data: Dict[str, Any], 
                         aggregated_data: Dict[str, Any]) -> List[str]:
        """
        Generate template-based insights from pattern analysis
        
        Args:
            pattern_data: ADHD pattern analysis results
            aggregated_data: Statistical aggregation results
            
        Returns:
            List of actionable insights
        """
        insights = []
        
        # Time blindness insights
        if 'time_blindness' in pattern_data:
            tb_data = pattern_data['time_blindness']
            if tb_data.get('mean_score'):
                score = tb_data['mean_score']
                trend = tb_data.get('trend', 'stable')
                
                if score < 0.4:
                    insights.append(
                        "⚠️ **Critical Time Awareness Issue**: Your time estimation accuracy is very low. "
                        "Consider using visual timers and setting alerts every 5 minutes during sessions."
                    )
                elif score < 0.6 and trend == 'declining':
                    insights.append(
                        "📉 **Declining Time Awareness**: Your ability to track time is decreasing. "
                        "Try the Pomodoro technique with 25-minute focused blocks."
                    )
                elif score > 0.7 and trend == 'improving':
                    insights.append(
                        "✅ **Time Management Improving**: Your time awareness is getting better! "
                        "Current strategies are working - keep using them."
                    )
        
        # Task switching insights
        if 'task_switching' in pattern_data:
            ts_data = pattern_data['task_switching']
            frequency = ts_data.get('mean_frequency', 0)
            
            if frequency > 4:
                insights.append(
                    "🔄 **High Task Switching**: You're jumping between topics frequently. "
                    "Try grouping similar items together and complete one category before moving to the next."
                )
            elif frequency > 2.5:
                insights.append(
                    "💡 **Moderate Task Switching**: Some topic jumping detected. "
                    "Consider using transition phrases like 'Moving on to...' to help your brain switch gears."
                )
        
        # Executive function insights
        if 'executive_function' in pattern_data:
            ef_data = pattern_data['executive_function']
            score = ef_data.get('mean_score', 0.5)
            trend = ef_data.get('trend', 'stable')
            
            if score < 0.5:
                insights.append(
                    "🧠 **Executive Function Support Needed**: Task organization is challenging. "
                    "Break tasks into smaller steps and use numbered lists for clarity."
                )
            elif score > 0.7 and trend == 'improving':
                insights.append(
                    "🌟 **Strong Executive Function**: Your organizational skills are excellent! "
                    "You're effectively managing task complexity."
                )
        
        # Fatigue insights
        if 'fatigue' in pattern_data:
            fatigue_data = pattern_data['fatigue']
            occurrence = fatigue_data.get('occurrence_rate', 0)
            
            if occurrence > 0.6:
                insights.append(
                    "😴 **Frequent Fatigue Detected**: Energy drops in most sessions. "
                    "Consider shorter 20-minute sessions or add a 5-minute break mid-session."
                )
            elif occurrence > 0.3:
                insights.append(
                    "⚡ **Occasional Fatigue**: Some energy dips noticed. "
                    "Try doing reviews at your peak energy time of day."
                )
        
        # Performance clustering insights
        if 'clustering' in aggregated_data:
            clusters = aggregated_data['clustering'].get('clusters', {})
            
            if 'needs_improvement' in clusters:
                count = len(clusters['needs_improvement'])
                total = sum(len(sessions) for sessions in clusters.values())
                
                if count > total * 0.5:
                    insights.append(
                        "📊 **Performance Pattern**: Over half of sessions need improvement. "
                        "Consider adjusting your review schedule or environment for better focus."
                    )
        
        # Degradation alerts
        if 'degradation_alerts' in aggregated_data:
            alerts = aggregated_data['degradation_alerts']
            
            if alerts:
                metrics_affected = set(a['metric'] for a in alerts)
                if len(metrics_affected) >= 2:
                    insights.append(
                        "⚠️ **Multiple Metrics Declining**: Several areas showing degradation. "
                        "This might indicate overall fatigue or need for a break from reviews."
                    )
        
        # Timing validation insights
        if 'timing_validation' in pattern_data:
            timing_data = pattern_data['timing_validation']
            
            if timing_data.get('data_available'):
                pattern = timing_data.get('discrepancy_pattern')
                invisible_ratio = timing_data.get('invisible_work_ratio', 0)
                
                # Discrepancy pattern insights
                if pattern == 'time_blindness':
                    insights.append(
                        "🕐 **Time Blindness Pattern Detected**: Your brain naturally focuses on memorable work "
                        "and filters out routine tasks. This is typical ADHD time blindness - not a character flaw. "
                        "Consider asking yourself 'What took up time today?' as a daily reflection prompt."
                    )
                elif pattern == 'selective_awareness':
                    insights.append(
                        "🎯 **Selective Time Awareness**: You accurately track high-focus work but lose track of "
                        "task-switching time. This executive function pattern is common in ADHD. "
                        "Try time-blocking for both focused AND transition time."
                    )
                elif pattern == 'high_awareness':
                    insights.append(
                        "✨ **Strong Time Awareness**: You have good awareness of where your time goes! "
                        "This is an excellent foundation for productivity."
                    )
                
                # Invisible work insights
                if invisible_ratio > 0.6:
                    pct = int(invisible_ratio * 100)
                    insights.append(
                        f"👻 **High Invisible Work Ratio ({pct}%)**: About {pct}% of your work happens 'invisibly' - "
                        "not captured in reviews. This reactive work is real and valid. "
                        "Consider explicitly scheduling 'buffer time' for unexpected tasks."
                    )
                elif invisible_ratio > 0.4:
                    pct = int(invisible_ratio * 100)
                    insights.append(
                        f"📋 **Moderate Invisible Work ({pct}%)**: Some routine work isn't making it into your reviews. "
                        "This is normal - not everything needs to be tracked, but awareness helps planning."
                    )
        
        return insights
    
    def create_weekly_summary(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Create comprehensive weekly summary with insights
        
        Args:
            week_start: Start of the week to analyze
            
        Returns:
            Weekly summary dictionary
        """
        if not week_start:
            week_start = datetime.now() - timedelta(days=7)
        
        # Import pattern analyzers
        from gtd_coach.patterns.evaluation_patterns import ADHDPatternAnalyzer
        from gtd_coach.patterns.pattern_aggregator import EvaluationAggregator
        from gtd_coach.metrics.adaptive_metrics import AdaptiveThresholds
        
        # Initialize analyzers
        adhd_analyzer = ADHDPatternAnalyzer(self.data_dir)
        aggregator = EvaluationAggregator(self.data_dir)
        thresholds = AdaptiveThresholds()
        
        # Get recent evaluations
        evaluations = aggregator.get_recent_evaluations(limit=10)
        
        # Filter to week's sessions
        week_sessions = []
        for eval_data in evaluations:
            timestamp_str = eval_data.get('timestamp', '')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp >= week_start:
                        week_sessions.append(eval_data.get('session_id', 'unknown'))
                except:
                    pass
        
        # Analyze patterns
        pattern_results = adhd_analyzer.aggregate_patterns(week_sessions)
        
        # Get statistical summary
        stats_summary = aggregator.generate_statistical_summary()
        
        # Generate insights
        insights = self.generate_insights(pattern_results, stats_summary)
        
        # Get adaptive configuration
        adaptive_config = thresholds.get_adaptive_config()
        
        # Create summary
        summary = {
            'week_start': week_start.isoformat(),
            'week_end': datetime.now().isoformat(),
            'session_count': len(week_sessions),
            'adhd_patterns': pattern_results,
            'statistics': stats_summary,
            'insights': insights,
            'adaptive_thresholds': adaptive_config,
            'recommendations': self._generate_recommendations(pattern_results, insights)
        }
        
        return summary
    
    def _generate_recommendations(self, patterns: Dict[str, Any], 
                                 insights: List[str]) -> List[str]:
        """
        Generate specific recommendations based on patterns
        
        Args:
            patterns: ADHD pattern analysis
            insights: Generated insights
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Time management recommendations
        if patterns.get('time_blindness', {}).get('mean_score', 1) < 0.5:
            recommendations.append(
                "**Time Management Tool**: Install a Time Timer app or use analog clock "
                "to make time passage visible during reviews."
            )
        
        # Task switching recommendations
        if patterns.get('task_switching', {}).get('mean_frequency', 0) > 3:
            recommendations.append(
                "**Batch Similar Tasks**: Group all email-related items together, "
                "all project items together, etc., before starting your review."
            )
        
        # Executive function recommendations
        if patterns.get('executive_function', {}).get('mean_score', 1) < 0.6:
            recommendations.append(
                "**Use Templates**: Create a standard template for common task types "
                "to reduce cognitive load during capture."
            )
        
        # Fatigue recommendations
        if patterns.get('fatigue', {}).get('occurrence_rate', 0) > 0.5:
            recommendations.append(
                "**Energy Management**: Schedule reviews for your peak energy time, "
                "typically 2-3 hours after waking or after light exercise."
            )
        
        # General recommendations based on insights
        if len(insights) > 5:
            recommendations.append(
                "**Simplify Process**: Many areas need attention. Focus on one improvement "
                "at a time, starting with time management."
            )
        elif len(insights) < 2:
            recommendations.append(
                "**Maintain Momentum**: System is working well! Consider slightly longer "
                "sessions to capture more detail."
            )
        
        return recommendations
    
    def export_insights_markdown(self, summary: Dict[str, Any]) -> str:
        """
        Export insights as formatted markdown
        
        Args:
            summary: Weekly summary data
            
        Returns:
            Markdown formatted string
        """
        md_lines = [
            "# GTD Coach Weekly Insights",
            f"\n📅 Week of {summary['week_start'][:10]}",
            f"\n## Summary",
            f"- **Sessions Completed**: {summary['session_count']}",
        ]
        
        # Add ADHD pattern summary
        patterns = summary.get('adhd_patterns', {})
        
        if patterns.get('time_blindness'):
            score = patterns['time_blindness'].get('mean_score', 0)
            if score is not None:
                md_lines.append(f"- **Time Awareness Score**: {score:.1%}")
        
        if patterns.get('task_switching'):
            freq = patterns['task_switching'].get('mean_frequency', 0)
            if freq:
                md_lines.append(f"- **Task Switching Frequency**: {freq:.1f} switches/session")
        
        if patterns.get('executive_function'):
            score = patterns['executive_function'].get('mean_score', 0)
            if score:
                md_lines.append(f"- **Executive Function Score**: {score:.1%}")
        
        # Add insights
        insights = summary.get('insights', [])
        if insights:
            md_lines.append("\n## Key Insights")
            for insight in insights:
                md_lines.append(f"\n{insight}")
        
        # Add recommendations
        recommendations = summary.get('recommendations', [])
        if recommendations:
            md_lines.append("\n## Recommendations")
            for i, rec in enumerate(recommendations, 1):
                md_lines.append(f"\n{i}. {rec}")
        
        # Add performance trends
        stats = summary.get('statistics', {})
        if stats.get('metrics'):
            md_lines.append("\n## Performance Trends")
            
            for metric, data in stats['metrics'].items():
                if data.get('statistics', {}).get('trend'):
                    trend = data['statistics']['trend']
                    icon = "📈" if trend == 'improving' else "📉" if trend == 'declining' else "➡️"
                    md_lines.append(f"- {metric.replace('_', ' ').title()}: {icon} {trend}")
        
        # Add adaptive threshold status
        adaptive = summary.get('adaptive_thresholds', {})
        if adaptive.get('personalized'):
            md_lines.append(f"\n## Personalization Status")
            md_lines.append(f"- **Adaptive Thresholds**: Active")
            md_lines.append(f"- **Confidence Level**: {adaptive.get('confidence', 'low').title()}")
        
        return "\n".join(md_lines)