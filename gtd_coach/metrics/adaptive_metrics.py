#!/usr/bin/env python3
"""
Adaptive Thresholds and Personalized Metrics
Adjusts evaluation thresholds based on individual user patterns
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class AdaptiveThresholds:
    """Manages personalized thresholds based on user history"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize adaptive thresholds
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or Path.home() / "gtd-coach" / "config" / "adaptive_thresholds.json"
        self.data_dir = Path.home() / "gtd-coach" / "data"
        self.thresholds = self._load_thresholds()
        self.adjustment_rate = 0.1  # Gradual adjustment factor
        self.min_data_points = 5    # Minimum sessions before personalization
        
    def _load_thresholds(self) -> Dict[str, Any]:
        """
        Load existing thresholds or create defaults
        
        Returns:
            Dictionary of threshold values
        """
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load thresholds: {e}")
        
        # Default thresholds (from Phase 1)
        return {
            'task_extraction': {
                'current': 0.7,
                'baseline': 0.7,
                'min': 0.5,
                'max': 0.9,
                'personal_mean': None,
                'personal_std': None,
                'last_updated': None,
                'session_count': 0
            },
            'memory_relevance': {
                'current': 0.5,
                'baseline': 0.5,
                'min': 0.3,
                'max': 0.8,
                'personal_mean': None,
                'personal_std': None,
                'last_updated': None,
                'session_count': 0
            },
            'coaching_quality': {
                'current': 0.6,
                'baseline': 0.6,
                'min': 0.4,
                'max': 0.85,
                'personal_mean': None,
                'personal_std': None,
                'last_updated': None,
                'session_count': 0
            },
            'adhd_patterns': {
                'time_blindness_threshold': 0.5,
                'task_switching_threshold': 3.0,
                'fatigue_threshold': 0.5,
                'executive_function_threshold': 0.6
            }
        }
    
    def save_thresholds(self):
        """Save current thresholds to configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.thresholds, f, indent=2, default=str)
            logger.info(f"Thresholds saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save thresholds: {e}")
    
    def calculate_baseline(self, metric_name: str, values: List[float]) -> Dict[str, float]:
        """
        Calculate personal baseline for a metric
        
        Args:
            metric_name: Name of the metric
            values: Historical values for the metric
            
        Returns:
            Baseline statistics
        """
        if not values or len(values) < self.min_data_points:
            logger.warning(f"Insufficient data for {metric_name} baseline")
            return {}
        
        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values) if len(values) > 1 else 0
        median = np.median(values)
        
        # Calculate percentiles for robust estimates
        p25 = np.percentile(values, 25)
        p75 = np.percentile(values, 75)
        iqr = p75 - p25
        
        # Robust threshold: median ± 1.5 * IQR
        robust_lower = max(0, median - 1.5 * iqr)
        robust_upper = min(1, median + 1.5 * iqr)
        
        return {
            'mean': mean,
            'std': std,
            'median': median,
            'iqr': iqr,
            'robust_lower': robust_lower,
            'robust_upper': robust_upper,
            'sample_size': len(values)
        }
    
    def update_threshold(self, metric_name: str, recent_values: List[float]) -> bool:
        """
        Update threshold based on recent performance
        
        Args:
            metric_name: Name of the metric
            recent_values: Recent metric values
            
        Returns:
            True if threshold was updated
        """
        if metric_name not in self.thresholds:
            logger.warning(f"Unknown metric: {metric_name}")
            return False
        
        if not recent_values or len(recent_values) < self.min_data_points:
            return False
        
        metric_config = self.thresholds[metric_name]
        
        # Calculate new baseline
        baseline = self.calculate_baseline(metric_name, recent_values)
        
        if not baseline:
            return False
        
        # Update personal statistics
        metric_config['personal_mean'] = baseline['mean']
        metric_config['personal_std'] = baseline['std']
        metric_config['session_count'] = len(recent_values)
        
        # Calculate new threshold using gradual adjustment
        current_threshold = metric_config['current']
        
        # Target threshold is personal mean minus one standard deviation
        # (We want to detect when performance drops below normal)
        target_threshold = max(
            metric_config['min'],
            min(metric_config['max'], baseline['mean'] - baseline['std'])
        )
        
        # Apply gradual adjustment
        new_threshold = current_threshold + self.adjustment_rate * (target_threshold - current_threshold)
        
        # Ensure within bounds
        new_threshold = max(metric_config['min'], min(metric_config['max'], new_threshold))
        
        # Check if significant change
        if abs(new_threshold - current_threshold) > 0.01:
            metric_config['current'] = new_threshold
            metric_config['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"Updated {metric_name} threshold: {current_threshold:.3f} -> {new_threshold:.3f}")
            return True
        
        return False
    
    def detect_degradation(self, metric_name: str, current_value: float) -> Optional[Dict[str, Any]]:
        """
        Detect if current value indicates performance degradation
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            
        Returns:
            Degradation alert if detected, None otherwise
        """
        if metric_name not in self.thresholds:
            return None
        
        metric_config = self.thresholds[metric_name]
        threshold = metric_config['current']
        
        # Check if below threshold
        if current_value < threshold:
            # Calculate severity based on personal statistics
            if metric_config['personal_std'] and metric_config['personal_mean']:
                z_score = (metric_config['personal_mean'] - current_value) / metric_config['personal_std']
                
                if z_score > 2:
                    severity = 'high'
                elif z_score > 1:
                    severity = 'moderate'
                else:
                    severity = 'low'
            else:
                # Fallback to simple percentage
                deviation_pct = (threshold - current_value) / threshold
                if deviation_pct > 0.3:
                    severity = 'high'
                elif deviation_pct > 0.15:
                    severity = 'moderate'
                else:
                    severity = 'low'
            
            return {
                'metric': metric_name,
                'current_value': current_value,
                'threshold': threshold,
                'personal_mean': metric_config.get('personal_mean'),
                'severity': severity,
                'message': f"{metric_name.replace('_', ' ').title()} below threshold",
                'recommendation': self._get_intervention_recommendation(metric_name, severity)
            }
        
        return None
    
    def _get_intervention_recommendation(self, metric_name: str, severity: str) -> str:
        """
        Get intervention recommendation based on metric and severity
        
        Args:
            metric_name: Name of the metric
            severity: Severity level
            
        Returns:
            Recommendation string
        """
        recommendations = {
            'task_extraction': {
                'low': "Consider clearer prompts for task capture",
                'moderate': "Add structured task extraction prompts",
                'high': "Implement immediate task clarification"
            },
            'memory_relevance': {
                'low': "Review memory retrieval strategy",
                'moderate': "Enhance context for memory queries",
                'high': "Rebuild memory index or clear irrelevant data"
            },
            'coaching_quality': {
                'low': "Refresh coaching prompts",
                'moderate': "Adjust tone or add more structure",
                'high': "Consider switching to more supportive mode"
            }
        }
        
        return recommendations.get(metric_name, {}).get(severity, "Monitor and reassess")
    
    def suggest_intervention(self, evaluation_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest interventions based on evaluation results
        
        Args:
            evaluation_summary: Summary of evaluation scores
            
        Returns:
            List of intervention suggestions
        """
        interventions = []
        
        avg_scores = evaluation_summary.get('average_scores', {})
        
        for metric_name, value in avg_scores.items():
            if metric_name in self.thresholds:
                degradation = self.detect_degradation(metric_name, value)
                
                if degradation:
                    interventions.append(degradation)
        
        # Check ADHD-specific patterns
        adhd_thresholds = self.thresholds.get('adhd_patterns', {})
        
        # Add ADHD-specific intervention triggers
        # (These would be populated by the ADHDPatternAnalyzer)
        
        # Sort by severity
        severity_order = {'high': 0, 'moderate': 1, 'low': 2}
        interventions.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 3))
        
        return interventions
    
    def get_adaptive_config(self) -> Dict[str, Any]:
        """
        Get current adaptive configuration for use in evaluation
        
        Returns:
            Configuration dictionary
        """
        config = {
            'thresholds': {},
            'personalized': False,
            'confidence': 'low'
        }
        
        # Check if we have enough data for personalization
        total_sessions = sum(
            m.get('session_count', 0) 
            for m in self.thresholds.values() 
            if isinstance(m, dict) and 'session_count' in m
        )
        
        if total_sessions >= self.min_data_points:
            config['personalized'] = True
            
            if total_sessions >= 10:
                config['confidence'] = 'high'
            elif total_sessions >= 7:
                config['confidence'] = 'moderate'
        
        # Extract current thresholds
        for metric_name in ['task_extraction', 'memory_relevance', 'coaching_quality']:
            if metric_name in self.thresholds:
                config['thresholds'][metric_name] = self.thresholds[metric_name]['current']
        
        # Add ADHD thresholds
        config['adhd_thresholds'] = self.thresholds.get('adhd_patterns', {})
        
        return config
    
    def update_from_aggregated_data(self, aggregated_data: Dict[str, Any]) -> bool:
        """
        Update thresholds from aggregated pattern data
        
        Args:
            aggregated_data: Aggregated statistics from pattern analysis
            
        Returns:
            True if any thresholds were updated
        """
        updated = False
        
        # Update main metric thresholds
        for metric_name in ['task_extraction', 'memory_relevance', 'coaching_quality']:
            if metric_name in aggregated_data:
                metric_data = aggregated_data[metric_name]
                if 'values' in metric_data and metric_data['values']:
                    if self.update_threshold(metric_name, metric_data['values']):
                        updated = True
        
        # Update ADHD pattern thresholds if needed
        # (This could be extended based on pattern analysis)
        
        if updated:
            self.save_thresholds()
        
        return updated
    
    def reset_to_baseline(self, metric_name: Optional[str] = None):
        """
        Reset thresholds to baseline values
        
        Args:
            metric_name: Specific metric to reset, or None for all
        """
        if metric_name:
            if metric_name in self.thresholds:
                self.thresholds[metric_name]['current'] = self.thresholds[metric_name]['baseline']
                self.thresholds[metric_name]['personal_mean'] = None
                self.thresholds[metric_name]['personal_std'] = None
                self.thresholds[metric_name]['session_count'] = 0
                logger.info(f"Reset {metric_name} to baseline")
        else:
            # Reset all metrics
            for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
                if metric in self.thresholds:
                    self.thresholds[metric]['current'] = self.thresholds[metric]['baseline']
                    self.thresholds[metric]['personal_mean'] = None
                    self.thresholds[metric]['personal_std'] = None
                    self.thresholds[metric]['session_count'] = 0
            logger.info("Reset all thresholds to baseline")
        
        self.save_thresholds()