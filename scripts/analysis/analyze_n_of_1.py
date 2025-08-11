#!/usr/bin/env python3
"""
N-of-1 Analysis Tools for GTD Coach
Analyzes single-subject experiment results with ABAB design
"""

import os
import sys
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("Warning: Langfuse not installed. Install with: pip install langfuse")

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


class NOf1Analyzer:
    """Analyze single-subject experiment results"""
    
    def __init__(self, week: Optional[str] = None):
        """
        Initialize analyzer for specific week
        
        Args:
            week: ISO week format (e.g., "2025-W32") or None for current week
        """
        if not week:
            week = datetime.now().strftime("%G-W%V")
        
        self.week = week
        self.traces = []
        self.metrics_by_condition = defaultdict(lambda: defaultdict(list))
        
        # Initialize Langfuse if available
        self.langfuse = None
        if LANGFUSE_AVAILABLE:
            try:
                self.langfuse = Langfuse()
            except Exception as e:
                print(f"Warning: Could not initialize Langfuse: {e}")
    
    def fetch_week_traces(self) -> List[Dict[str, Any]]:
        """
        Fetch traces for the specified week from Langfuse
        
        Returns:
            List of trace dictionaries
        """
        if not self.langfuse:
            return self._load_local_traces()
        
        try:
            # In real implementation, use Langfuse API to fetch traces
            # For now, return mock data or local files
            print(f"{BLUE}Fetching traces for week {self.week}...{RESET}")
            return self._load_local_traces()
            
        except Exception as e:
            print(f"{RED}Error fetching traces from Langfuse: {e}{RESET}")
            return self._load_local_traces()
    
    def _load_local_traces(self) -> List[Dict[str, Any]]:
        """Load traces from local JSON files"""
        traces = []
        data_dir = Path.home() / "gtd-coach" / "data"
        
        # Load North Star metrics files for the week
        for metrics_file in data_dir.glob("north_star_metrics_*.json"):
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    
                    # Check if it's from the current week
                    session_date = datetime.fromisoformat(data.get('session_start', ''))
                    session_week = session_date.strftime("%G-W%V")
                    
                    if session_week == self.week:
                        traces.append(data)
                        
            except Exception as e:
                print(f"Warning: Could not load {metrics_file}: {e}")
        
        print(f"Loaded {len(traces)} traces for week {self.week}")
        return traces
    
    def analyze_within_condition_variance(self, traces: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Analyze variance within each experimental condition
        
        Args:
            traces: List of trace data
            
        Returns:
            Dictionary of variance metrics per condition
        """
        condition_metrics = defaultdict(lambda: defaultdict(list))
        
        for trace in traces:
            # Get experimental condition from metadata
            metadata = trace.get('metadata', {}) if 'metadata' in trace else trace
            condition = metadata.get('experiment_value', 'unknown')
            
            # Extract North Star metrics
            metrics = trace.get('metrics', {})
            for metric_name, value in metrics.items():
                if value is not None:
                    condition_metrics[condition][metric_name].append(value)
        
        # Calculate variance statistics
        variance_stats = {}
        for condition, metrics in condition_metrics.items():
            variance_stats[condition] = {}
            
            for metric_name, values in metrics.items():
                if len(values) > 1:
                    variance_stats[condition][metric_name] = {
                        'mean': statistics.mean(values),
                        'stdev': statistics.stdev(values),
                        'cv': statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 0,
                        'n': len(values)
                    }
                elif len(values) == 1:
                    variance_stats[condition][metric_name] = {
                        'mean': values[0],
                        'stdev': 0,
                        'cv': 0,
                        'n': 1
                    }
        
        return variance_stats
    
    def detect_order_effects(self, traces: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Check if performance differs based on ABAB order
        
        Args:
            traces: List of trace data
            
        Returns:
            Dictionary of order effect metrics
        """
        # Group by session position in ABAB pattern
        ab_first = defaultdict(list)  # Condition A in positions 1,3
        ab_second = defaultdict(list)  # Condition A in positions 2,4
        
        for trace in traces:
            metadata = trace.get('metadata', {}) if 'metadata' in trace else trace
            session_position = metadata.get('session_in_pattern', 0)
            condition = metadata.get('experiment_value', 'unknown')
            
            metrics = trace.get('metrics', {})
            
            # Group by whether this is first or second appearance
            if session_position in [1, 3]:  # First A or first B
                ab_first[condition].append(metrics)
            elif session_position in [2, 4]:  # Second A or second B
                ab_second[condition].append(metrics)
        
        # Calculate order effects
        order_effects = {}
        
        for condition in set(list(ab_first.keys()) + list(ab_second.keys())):
            first_values = ab_first.get(condition, [])
            second_values = ab_second.get(condition, [])
            
            if first_values and second_values:
                # Compare key metrics between first and second appearance
                for metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
                    first_metric = [m.get(metric_name) for m in first_values if m.get(metric_name) is not None]
                    second_metric = [m.get(metric_name) for m in second_values if m.get(metric_name) is not None]
                    
                    if first_metric and second_metric:
                        first_mean = statistics.mean(first_metric)
                        second_mean = statistics.mean(second_metric)
                        
                        # Calculate percentage change
                        if first_mean != 0:
                            change = ((second_mean - first_mean) / abs(first_mean)) * 100
                            order_effects[f"{condition}_{metric_name}_order_effect"] = change
        
        return order_effects
    
    def calculate_personal_effect_size(self, traces: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate personal response to each experimental variable
        
        Args:
            traces: List of trace data
            
        Returns:
            Dictionary of effect sizes per variable
        """
        # Group metrics by condition
        condition_metrics = defaultdict(lambda: defaultdict(list))
        
        for trace in traces:
            metadata = trace.get('metadata', {}) if 'metadata' in trace else trace
            condition = metadata.get('experiment_value', 'unknown')
            variable = metadata.get('experiment_variable', 'unknown')
            
            metrics = trace.get('metrics', {})
            for metric_name, value in metrics.items():
                if value is not None:
                    condition_metrics[condition][metric_name].append(value)
        
        # Calculate effect sizes between conditions
        effect_sizes = {}
        conditions = list(condition_metrics.keys())
        
        if len(conditions) >= 2:
            # Compare first two unique conditions (A vs B in ABAB)
            unique_conditions = list(set(conditions))[:2]
            cond_a, cond_b = unique_conditions[0], unique_conditions[1] if len(unique_conditions) > 1 else unique_conditions[0]
            
            effect_sizes[f"{cond_a}_vs_{cond_b}"] = {}
            
            for metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
                a_values = condition_metrics[cond_a].get(metric_name, [])
                b_values = condition_metrics[cond_b].get(metric_name, [])
                
                if a_values and b_values:
                    # Calculate Cohen's d for single-subject
                    mean_a = statistics.mean(a_values)
                    mean_b = statistics.mean(b_values)
                    
                    # Pooled standard deviation
                    if len(a_values) > 1 and len(b_values) > 1:
                        pooled_std = ((statistics.stdev(a_values) + statistics.stdev(b_values)) / 2)
                        if pooled_std > 0:
                            cohens_d = (mean_b - mean_a) / pooled_std
                        else:
                            cohens_d = 0
                    else:
                        # Use mean difference as effect size when std not available
                        cohens_d = mean_b - mean_a
                    
                    effect_sizes[f"{cond_a}_vs_{cond_b}"][metric_name] = {
                        'effect_size': cohens_d,
                        'mean_difference': mean_b - mean_a,
                        'percent_change': ((mean_b - mean_a) / abs(mean_a) * 100) if mean_a != 0 else 0
                    }
        
        return effect_sizes
    
    def generate_weekly_report(self) -> str:
        """
        Generate comprehensive weekly experiment report
        
        Returns:
            Formatted report string
        """
        # Fetch traces for the week
        traces = self.fetch_week_traces()
        
        if not traces:
            return f"{YELLOW}No data available for week {self.week}{RESET}"
        
        # Perform analyses
        variance = self.analyze_within_condition_variance(traces)
        order_effects = self.detect_order_effects(traces)
        effect_sizes = self.calculate_personal_effect_size(traces)
        
        # Build report
        report = []
        report.append(f"\n{BLUE}{'='*60}{RESET}")
        report.append(f"{BLUE}N-OF-1 EXPERIMENT REPORT - WEEK {self.week}{RESET}")
        report.append(f"{BLUE}{'='*60}{RESET}\n")
        
        # Session count
        report.append(f"{CYAN}Sessions Analyzed:{RESET} {len(traces)}")
        
        # Get experiment info from first trace
        if traces:
            first_trace = traces[0]
            metadata = first_trace.get('metadata', {}) if 'metadata' in first_trace else first_trace
            report.append(f"{CYAN}Experiment:{RESET} {metadata.get('experiment_name', 'Unknown')}")
            report.append(f"{CYAN}Variable:{RESET} {metadata.get('experiment_variable', 'Unknown')}\n")
        
        # Within-condition variance
        report.append(f"{CYAN}WITHIN-CONDITION STABILITY:{RESET}")
        for condition, metrics in variance.items():
            report.append(f"\n  {GREEN}{condition}:{RESET}")
            for metric_name, stats in metrics.items():
                if metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
                    cv_indicator = "✓" if stats['cv'] < 0.3 else "⚠" if stats['cv'] < 0.5 else "✗"
                    report.append(f"    {metric_name}: μ={stats['mean']:.2f} (CV={stats['cv']:.2f}) {cv_indicator}")
        
        # Order effects
        if order_effects:
            report.append(f"\n{CYAN}ORDER EFFECTS (AB vs BA):{RESET}")
            for effect_name, change in order_effects.items():
                direction = "↑" if change > 0 else "↓"
                color = GREEN if abs(change) < 10 else YELLOW if abs(change) < 20 else RED
                report.append(f"  {effect_name}: {color}{change:+.1f}%{RESET} {direction}")
        
        # Effect sizes
        report.append(f"\n{CYAN}PERSONAL EFFECT SIZES:{RESET}")
        for comparison, metrics in effect_sizes.items():
            report.append(f"\n  {GREEN}{comparison}:{RESET}")
            for metric_name, effects in metrics.items():
                # Interpret effect size
                d = effects['effect_size']
                if abs(d) < 0.2:
                    interpretation = "negligible"
                elif abs(d) < 0.5:
                    interpretation = "small"
                elif abs(d) < 0.8:
                    interpretation = "medium"
                else:
                    interpretation = "large"
                
                direction = "improvement" if (
                    (metric_name == "memory_relevance_score" and d > 0) or
                    (metric_name == "time_to_first_capture" and d < 0) or
                    (metric_name == "task_followthrough_rate" and d > 0)
                ) else "decline"
                
                report.append(f"    {metric_name}:")
                report.append(f"      Effect size: {d:.2f} ({interpretation} {direction})")
                report.append(f"      Change: {effects['percent_change']:+.1f}%")
        
        # Recommendations
        report.append(f"\n{CYAN}RECOMMENDATIONS:{RESET}")
        
        # Find best performing condition
        best_conditions = self._identify_best_conditions(variance, effect_sizes)
        if best_conditions:
            report.append(f"\n  {GREEN}Optimal Settings:{RESET}")
            for metric, condition in best_conditions.items():
                report.append(f"    For {metric}: Use {condition}")
        
        # Stability check
        stable_conditions = [c for c, m in variance.items() 
                           if all(s.get('cv', 1) < 0.3 for s in m.values())]
        if stable_conditions:
            report.append(f"\n  {GREEN}Most Stable:{RESET} {', '.join(stable_conditions)}")
        
        report.append(f"\n{BLUE}{'='*60}{RESET}")
        
        return '\n'.join(report)
    
    def _identify_best_conditions(self, variance: Dict, effect_sizes: Dict) -> Dict[str, str]:
        """Identify best performing conditions for each metric"""
        best = {}
        
        # Analyze each North Star metric
        for metric_name in ['memory_relevance_score', 'time_to_first_capture', 'task_followthrough_rate']:
            best_value = None
            best_condition = None
            
            for condition, metrics in variance.items():
                if metric_name in metrics:
                    value = metrics[metric_name]['mean']
                    
                    # Higher is better for relevance and followthrough
                    # Lower is better for time_to_first_capture
                    if metric_name == 'time_to_first_capture':
                        if best_value is None or value < best_value:
                            best_value = value
                            best_condition = condition
                    else:
                        if best_value is None or value > best_value:
                            best_value = value
                            best_condition = condition
            
            if best_condition:
                best[metric_name] = best_condition
        
        return best
    
    def export_results(self, output_path: Optional[Path] = None) -> None:
        """
        Export analysis results to JSON
        
        Args:
            output_path: Path to save results
        """
        if not output_path:
            output_path = Path.home() / "gtd-coach" / "analysis" / f"n_of_1_report_{self.week}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Fetch and analyze
        traces = self.fetch_week_traces()
        
        results = {
            "week": self.week,
            "analysis_date": datetime.now().isoformat(),
            "session_count": len(traces),
            "variance": self.analyze_within_condition_variance(traces),
            "order_effects": self.detect_order_effects(traces),
            "effect_sizes": self.calculate_personal_effect_size(traces),
            "raw_traces": traces
        }
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"{GREEN}Results exported to: {output_path}{RESET}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze N-of-1 experiment results")
    parser.add_argument("--week", help="ISO week to analyze (e.g., 2025-W32)")
    parser.add_argument("--export", action="store_true", help="Export results to JSON")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = NOf1Analyzer(week=args.week)
    
    # Generate and print report
    report = analyzer.generate_weekly_report()
    print(report)
    
    # Export if requested
    if args.export:
        analyzer.export_results()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())