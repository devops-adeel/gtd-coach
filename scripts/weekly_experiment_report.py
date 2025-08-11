#!/usr/bin/env python3
"""
Weekly Experiment Report Generator for GTD Coach
Automatically analyzes the week's experiments and generates actionable insights
"""

import os
import sys
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.analysis.analyze_n_of_1 import NOf1Analyzer
from gtd_coach.experiments.n_of_1 import NOf1Experimenter

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
BOLD = '\033[1m'


class WeeklyExperimentReporter:
    """Generate comprehensive weekly experiment reports with recommendations"""
    
    def __init__(self, week: Optional[str] = None):
        """
        Initialize reporter for specific week
        
        Args:
            week: ISO week format (e.g., "2025-W32") or None for current week
        """
        if not week:
            week = datetime.now().strftime("%G-W%V")
        
        self.week = week
        self.analyzer = NOf1Analyzer(week)
        self.experimenter = NOf1Experimenter()
        self.traces = []
        self.recommendations = []
    
    def generate_full_report(self) -> str:
        """
        Generate comprehensive weekly report with visualizations
        
        Returns:
            Formatted report string
        """
        report = []
        
        # Header
        report.append(self._generate_header())
        
        # Executive Summary
        report.append(self._generate_executive_summary())
        
        # North Star Metrics Performance
        report.append(self._generate_metrics_section())
        
        # Experiment Results
        report.append(self._generate_experiment_results())
        
        # ADHD Pattern Analysis
        report.append(self._generate_adhd_analysis())
        
        # Recommendations
        report.append(self._generate_recommendations())
        
        # Next Week Preview
        report.append(self._generate_next_week_preview())
        
        # Footer
        report.append(self._generate_footer())
        
        return '\n'.join(report)
    
    def _generate_header(self) -> str:
        """Generate report header"""
        return f"""
{BLUE}{'='*70}{RESET}
{BOLD}{BLUE}GTD COACH WEEKLY EXPERIMENT REPORT{RESET}
{BLUE}Week: {self.week}{RESET}
{BLUE}Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}
{BLUE}{'='*70}{RESET}
"""
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary of week's performance"""
        self.traces = self.analyzer.fetch_week_traces()
        
        if not self.traces:
            return f"\n{YELLOW}No sessions recorded this week.{RESET}\n"
        
        # Calculate summary statistics
        total_sessions = len(self.traces)
        
        # Average North Star metrics
        metrics_summary = self._calculate_metrics_summary()
        
        # Get current experiment info
        current_exp = self.experimenter.get_current_experiment()
        exp_name = current_exp.get('name', 'Unknown') if current_exp else 'None'
        
        summary = f"""
{CYAN}{BOLD}EXECUTIVE SUMMARY{RESET}
{'-'*40}
📊 Sessions Completed: {total_sessions}
🧪 Experiment: {exp_name}
"""
        
        # North Star metrics summary with visual indicators
        if metrics_summary:
            summary += f"""
{BOLD}North Star Metrics:{RESET}
  📍 Memory Relevance: {self._format_metric_with_indicator(
      metrics_summary.get('memory_relevance_score', 0), 
      target=0.8, higher_better=True)}
  ⏱️  Time to Insight: {self._format_metric_with_indicator(
      metrics_summary.get('time_to_first_capture', 999), 
      target=30, higher_better=False)} seconds
  ✅ Task Follow-through: {self._format_metric_with_indicator(
      metrics_summary.get('task_followthrough_rate', 0), 
      target=0.6, higher_better=True)}
"""
        
        return summary
    
    def _generate_metrics_section(self) -> str:
        """Generate detailed metrics analysis section"""
        if not self.traces:
            return ""
        
        section = f"""
{CYAN}{BOLD}NORTH STAR METRICS ANALYSIS{RESET}
{'-'*40}
"""
        
        # Analyze trends for each metric
        metrics_trends = self._analyze_metric_trends()
        
        for metric_name, trend_data in metrics_trends.items():
            section += f"\n{BOLD}{self._get_metric_display_name(metric_name)}:{RESET}\n"
            
            # Trend visualization
            section += f"  Trend: {self._visualize_trend(trend_data['values'])}\n"
            
            # Statistics
            if trend_data['values']:
                section += f"  Range: {trend_data['min']:.2f} - {trend_data['max']:.2f}\n"
                section += f"  Improvement: {trend_data['improvement']:+.1f}%\n"
                
                # Success criteria check
                success = self._check_success_criteria(metric_name, trend_data['current'])
                section += f"  Status: {success}\n"
        
        return section
    
    def _generate_experiment_results(self) -> str:
        """Generate experiment-specific results"""
        if not self.traces:
            return ""
        
        section = f"""
{CYAN}{BOLD}EXPERIMENT RESULTS{RESET}
{'-'*40}
"""
        
        # Get detailed analysis from analyzer
        variance = self.analyzer.analyze_within_condition_variance(self.traces)
        effect_sizes = self.analyzer.calculate_personal_effect_size(self.traces)
        order_effects = self.analyzer.detect_order_effects(self.traces)
        
        # Display conditions tested
        conditions = list(variance.keys())
        if conditions:
            section += f"\n{BOLD}Conditions Tested:{RESET}\n"
            for i, condition in enumerate(conditions, 1):
                section += f"  {i}. {condition}\n"
        
        # Display effect sizes
        if effect_sizes:
            section += f"\n{BOLD}Effect Sizes:{RESET}\n"
            for comparison, metrics in effect_sizes.items():
                section += f"\n  {comparison}:\n"
                for metric, effects in metrics.items():
                    effect_interpretation = self._interpret_effect_size(effects['effect_size'])
                    section += f"    • {self._get_metric_display_name(metric)}: "
                    section += f"{effect_interpretation} ({effects['percent_change']:+.1f}%)\n"
        
        # Check for order effects
        if order_effects:
            significant_order_effects = {k: v for k, v in order_effects.items() if abs(v) > 15}
            if significant_order_effects:
                section += f"\n{YELLOW}⚠️  Order Effects Detected:{RESET}\n"
                for effect, value in significant_order_effects.items():
                    section += f"  • {effect}: {value:+.1f}%\n"
        
        return section
    
    def _generate_adhd_analysis(self) -> str:
        """Generate ADHD-specific pattern analysis"""
        if not self.traces:
            return ""
        
        section = f"""
{CYAN}{BOLD}ADHD PATTERN ANALYSIS{RESET}
{'-'*40}
"""
        
        # Analyze ADHD-specific metrics
        adhd_metrics = self._analyze_adhd_patterns()
        
        if adhd_metrics:
            # Context switching analysis
            section += f"\n{BOLD}Focus Patterns:{RESET}\n"
            section += f"  • Context Switches/Min: {adhd_metrics['avg_switches']:.2f} "
            section += f"({self._classify_focus_level(adhd_metrics['avg_switches'])})\n"
            
            # Hyperfocus vs scatter
            section += f"  • Hyperfocus Periods: {adhd_metrics['hyperfocus_total']}\n"
            section += f"  • Scatter Periods: {adhd_metrics['scatter_total']}\n"
            
            # Pre-capture hesitation
            if adhd_metrics.get('avg_hesitation'):
                section += f"  • Avg Start Hesitation: {adhd_metrics['avg_hesitation']:.0f}s\n"
            
            # Recommendations based on patterns
            if adhd_metrics['avg_switches'] > 3:
                self.recommendations.append("Consider shorter phase durations to match attention span")
            if adhd_metrics['scatter_total'] > adhd_metrics['hyperfocus_total']:
                self.recommendations.append("Try more structured prompts to reduce scatter periods")
        
        return section
    
    def _generate_recommendations(self) -> str:
        """Generate actionable recommendations"""
        section = f"""
{CYAN}{BOLD}RECOMMENDATIONS{RESET}
{'-'*40}
"""
        
        # Analyze all data to generate recommendations
        self._build_recommendations()
        
        if self.recommendations:
            section += f"\n{GREEN}Based on this week's data:{RESET}\n\n"
            for i, rec in enumerate(self.recommendations, 1):
                section += f"  {i}. {rec}\n"
        else:
            section += f"\n{GREEN}Continue with current settings - performance is optimal!{RESET}\n"
        
        # Add specific optimization suggestions
        optimal_settings = self._determine_optimal_settings()
        if optimal_settings:
            section += f"\n{BOLD}Suggested Settings for Next Week:{RESET}\n"
            for setting, value in optimal_settings.items():
                section += f"  • {setting}: {value}\n"
        
        return section
    
    def _generate_next_week_preview(self) -> str:
        """Preview next week's experiment"""
        # Get next week's experiment
        next_week = (datetime.strptime(self.week + "-1", "%G-W%V-%w") + timedelta(weeks=1)).strftime("%G-W%V")
        next_week_num = int(next_week.split("-W")[1])
        
        # Find next experiment in schedule
        if self.experimenter.experiments:
            next_exp_index = (next_week_num - 1) % len(self.experimenter.experiments)
            next_exp = self.experimenter.experiments[next_exp_index]
            
            section = f"""
{CYAN}{BOLD}NEXT WEEK'S EXPERIMENT{RESET}
{'-'*40}

📅 Week: {next_week}
🧪 Experiment: {next_exp.get('name', 'Unknown')}
🎯 Variable: {next_exp.get('variable', 'Unknown')}

{BOLD}Focus Metrics:{RESET}
"""
            for metric in next_exp.get('metrics_focus', []):
                section += f"  • {self._get_metric_display_name(metric)}\n"
            
            return section
        
        return ""
    
    def _generate_footer(self) -> str:
        """Generate report footer"""
        return f"""
{BLUE}{'='*70}{RESET}
{BLUE}End of Weekly Report - Keep experimenting! 🚀{RESET}
{BLUE}{'='*70}{RESET}
"""
    
    # Helper methods
    
    def _calculate_metrics_summary(self) -> Dict[str, float]:
        """Calculate average metrics for the week"""
        if not self.traces:
            return {}
        
        metrics_sum = defaultdict(list)
        
        for trace in self.traces:
            metrics = trace.get('metrics', {})
            for name, value in metrics.items():
                if value is not None:
                    metrics_sum[name].append(value)
        
        return {
            name: statistics.mean(values) if values else 0
            for name, values in metrics_sum.items()
        }
    
    def _format_metric_with_indicator(self, value: float, target: float, higher_better: bool) -> str:
        """Format metric with visual indicator"""
        if higher_better:
            if value >= target:
                return f"{GREEN}{value:.2f} ✓{RESET}"
            elif value >= target * 0.8:
                return f"{YELLOW}{value:.2f} ⚠{RESET}"
            else:
                return f"{RED}{value:.2f} ✗{RESET}"
        else:
            if value <= target:
                return f"{GREEN}{value:.0f} ✓{RESET}"
            elif value <= target * 1.2:
                return f"{YELLOW}{value:.0f} ⚠{RESET}"
            else:
                return f"{RED}{value:.0f} ✗{RESET}"
    
    def _visualize_trend(self, values: List[float]) -> str:
        """Create simple ASCII trend visualization"""
        if not values or len(values) < 2:
            return "━━━━━"
        
        # Calculate trend direction
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])
        
        if second_half > first_half * 1.1:
            return f"{GREEN}↗↗↗{RESET}"  # Strong upward
        elif second_half > first_half:
            return f"{GREEN}↗━━{RESET}"  # Slight upward
        elif second_half < first_half * 0.9:
            return f"{RED}↘↘↘{RESET}"  # Strong downward
        elif second_half < first_half:
            return f"{YELLOW}↘━━{RESET}"  # Slight downward
        else:
            return "━━━━━"  # Stable
    
    def _analyze_metric_trends(self) -> Dict[str, Dict[str, Any]]:
        """Analyze trends for each North Star metric"""
        trends = {}
        
        for metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
            values = []
            for trace in self.traces:
                value = trace.get('metrics', {}).get(metric_name)
                if value is not None:
                    values.append(value)
            
            if values:
                trends[metric_name] = {
                    'values': values,
                    'min': min(values),
                    'max': max(values),
                    'current': values[-1] if values else 0,
                    'improvement': ((values[-1] - values[0]) / abs(values[0]) * 100) if len(values) > 1 and values[0] != 0 else 0
                }
        
        return trends
    
    def _get_metric_display_name(self, metric_name: str) -> str:
        """Get human-readable metric name"""
        display_names = {
            'memory_relevance_score': 'Memory Relevance',
            'time_to_first_capture': 'Time to First Capture',
            'task_followthrough_rate': 'Task Follow-through',
            'context_switches_per_minute': 'Context Switches/Min',
            'hyperfocus_periods': 'Hyperfocus Periods',
            'scatter_periods': 'Scatter Periods',
            'pre_capture_hesitation': 'Pre-capture Hesitation'
        }
        return display_names.get(metric_name, metric_name)
    
    def _check_success_criteria(self, metric_name: str, value: float) -> str:
        """Check if metric meets success criteria"""
        criteria = self.experimenter.get_success_criteria(metric_name)
        target = criteria.get('target')
        
        if target is None:
            return "No target set"
        
        if metric_name == 'time_to_first_capture':
            # Lower is better
            if value <= target:
                return f"{GREEN}✓ Exceeds target ({target}){RESET}"
            else:
                return f"{YELLOW}⚠ Below target ({target}){RESET}"
        else:
            # Higher is better
            if value >= target:
                return f"{GREEN}✓ Exceeds target ({target}){RESET}"
            else:
                return f"{YELLOW}⚠ Below target ({target}){RESET}"
    
    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(effect_size)
        
        if abs_d < 0.2:
            magnitude = "Negligible"
            color = ""
        elif abs_d < 0.5:
            magnitude = "Small"
            color = YELLOW
        elif abs_d < 0.8:
            magnitude = "Medium"
            color = GREEN
        else:
            magnitude = "Large"
            color = f"{BOLD}{GREEN}"
        
        direction = "improvement" if effect_size > 0 else "decline"
        return f"{color}{magnitude} {direction}{RESET}"
    
    def _analyze_adhd_patterns(self) -> Dict[str, Any]:
        """Analyze ADHD-specific patterns"""
        if not self.traces:
            return {}
        
        switches = []
        hyperfocus = []
        scatter = []
        hesitation = []
        
        for trace in self.traces:
            metrics = trace.get('metrics', {})
            
            if 'context_switches_per_minute' in metrics:
                switches.append(metrics['context_switches_per_minute'])
            if 'hyperfocus_periods' in metrics:
                hyperfocus.append(metrics['hyperfocus_periods'])
            if 'scatter_periods' in metrics:
                scatter.append(metrics['scatter_periods'])
            if 'pre_capture_hesitation' in metrics:
                hesitation.append(metrics['pre_capture_hesitation'])
        
        return {
            'avg_switches': statistics.mean(switches) if switches else 0,
            'hyperfocus_total': sum(hyperfocus),
            'scatter_total': sum(scatter),
            'avg_hesitation': statistics.mean(hesitation) if hesitation else 0
        }
    
    def _classify_focus_level(self, switches_per_min: float) -> str:
        """Classify focus level based on context switches"""
        if switches_per_min < 1:
            return f"{GREEN}Excellent focus{RESET}"
        elif switches_per_min < 3:
            return f"{GREEN}Good focus{RESET}"
        elif switches_per_min < 5:
            return f"{YELLOW}Moderate focus{RESET}"
        else:
            return f"{RED}High distractibility{RESET}"
    
    def _build_recommendations(self) -> None:
        """Build list of recommendations based on analysis"""
        if not self.traces:
            return
        
        # Clear existing recommendations
        self.recommendations = []
        
        # Analyze metrics performance
        metrics_summary = self._calculate_metrics_summary()
        
        # Memory relevance recommendations
        if metrics_summary.get('memory_relevance_score', 0) < 0.5:
            self.recommendations.append("Memory retrieval needs improvement - try different retrieval strategy")
        
        # Time to insight recommendations
        if metrics_summary.get('time_to_first_capture', 999) > 60:
            self.recommendations.append("Slow start detected - consider more engaging opening prompts")
        
        # Task follow-through recommendations
        if metrics_summary.get('task_followthrough_rate', 0) < 0.4:
            self.recommendations.append("Low task completion - break down tasks into smaller steps")
        
        # Check for high variance
        variance = self.analyzer.analyze_within_condition_variance(self.traces)
        for condition, metrics in variance.items():
            for metric_name, stats in metrics.items():
                if stats.get('cv', 0) > 0.5:
                    self.recommendations.append(f"High variability in {condition} - needs stabilization")
                    break
    
    def _determine_optimal_settings(self) -> Dict[str, str]:
        """Determine optimal settings based on week's data"""
        if not self.traces:
            return {}
        
        # Get best performing conditions
        variance = self.analyzer.analyze_within_condition_variance(self.traces)
        
        optimal = {}
        for metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
            best_value = None
            best_condition = None
            
            for condition, metrics in variance.items():
                if metric_name in metrics:
                    value = metrics[metric_name].get('mean', 0)
                    
                    if metric_name == 'time_to_first_capture':
                        # Lower is better
                        if best_value is None or value < best_value:
                            best_value = value
                            best_condition = condition
                    else:
                        # Higher is better
                        if best_value is None or value > best_value:
                            best_value = value
                            best_condition = condition
            
            if best_condition:
                optimal[self._get_metric_display_name(metric_name)] = best_condition
        
        return optimal
    
    def save_report(self, output_path: Optional[Path] = None) -> None:
        """
        Save report to file
        
        Args:
            output_path: Path to save report
        """
        if not output_path:
            output_path = Path.home() / "gtd-coach" / "reports" / f"weekly_report_{self.week}.txt"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate report without color codes for file
        report = self.generate_full_report()
        
        # Strip ANSI color codes
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_report = ansi_escape.sub('', report)
        
        with open(output_path, 'w') as f:
            f.write(clean_report)
        
        print(f"\n{GREEN}Report saved to: {output_path}{RESET}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate weekly experiment report")
    parser.add_argument("--week", help="ISO week to analyze (e.g., 2025-W32)")
    parser.add_argument("--save", action="store_true", help="Save report to file")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()
    
    # Disable colors if requested
    if args.no_color:
        globals().update({
            'GREEN': '', 'RED': '', 'YELLOW': '', 'BLUE': '',
            'CYAN': '', 'MAGENTA': '', 'RESET': '', 'BOLD': ''
        })
    
    # Generate report
    reporter = WeeklyExperimentReporter(week=args.week)
    report = reporter.generate_full_report()
    print(report)
    
    # Save if requested
    if args.save:
        reporter.save_report()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())