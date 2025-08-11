#!/usr/bin/env python3
"""
Pattern Aggregation and Statistical Analysis
Combines evaluation scores over time with simple, proven algorithms
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from collections import deque
import glob

logger = logging.getLogger(__name__)


class EvaluationAggregator:
    """Aggregates and analyzes evaluation patterns over time"""
    
    def __init__(self, data_dir: Path = None, window_size: int = 7):
        """
        Initialize the evaluation aggregator
        
        Args:
            data_dir: Directory containing evaluation data
            window_size: Number of sessions for rolling calculations
        """
        self.data_dir = data_dir or Path.home() / "gtd-coach" / "data"
        self.eval_dir = self.data_dir / "evaluations"
        self.window_size = window_size
        self.cache = {}
        
    def get_recent_evaluations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent evaluation files
        
        Args:
            limit: Maximum number of evaluations to retrieve
            
        Returns:
            List of evaluation data dictionaries
        """
        eval_files = sorted(glob.glob(str(self.eval_dir / "eval_*.json")))[-limit:]
        evaluations = []
        
        for file_path in eval_files:
            try:
                with open(file_path) as f:
                    eval_data = json.load(f)
                    evaluations.append(eval_data)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
        
        return evaluations
    
    def calculate_rolling_average(self, metric_name: str, 
                                 evaluations: Optional[List[Dict]] = None) -> Dict[str, float]:
        """
        Calculate rolling average for a specific metric
        
        Args:
            metric_name: Name of the metric (e.g., 'task_extraction', 'coaching_quality')
            evaluations: Optional list of evaluations, otherwise fetch recent
            
        Returns:
            Dictionary with rolling average statistics
        """
        if evaluations is None:
            evaluations = self.get_recent_evaluations(self.window_size)
        
        if not evaluations:
            return {'mean': None, 'std': None, 'trend': None}
        
        # Extract metric values
        values = []
        for eval_data in evaluations:
            summary = eval_data.get('summary', {})
            avg_scores = summary.get('average_scores', {})
            
            if metric_name in avg_scores:
                values.append(avg_scores[metric_name])
        
        if not values:
            return {'mean': None, 'std': None, 'trend': None}
        
        # Calculate statistics
        rolling_mean = np.mean(values)
        rolling_std = np.std(values) if len(values) > 1 else 0
        
        # Calculate trend using linear regression
        trend = None
        if len(values) >= 3:
            x = np.arange(len(values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
            
            # Classify trend
            if abs(slope) < 0.01:
                trend = 'stable'
            elif slope > 0:
                trend = 'improving'
            else:
                trend = 'declining'
        
        return {
            'mean': rolling_mean,
            'std': rolling_std,
            'trend': trend,
            'values': values,
            'window_size': len(values)
        }
    
    def detect_anomalies(self, metric_name: str, 
                        threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect anomalies using standard deviation method
        
        Args:
            metric_name: Name of the metric to analyze
            threshold_multiplier: Number of standard deviations for anomaly threshold
            
        Returns:
            List of anomaly detections
        """
        evaluations = self.get_recent_evaluations(limit=30)  # More data for baseline
        
        if len(evaluations) < 5:
            logger.warning("Insufficient data for anomaly detection")
            return []
        
        # Calculate baseline statistics
        baseline_evals = evaluations[:-5]  # Use older data for baseline
        recent_evals = evaluations[-5:]    # Check recent for anomalies
        
        baseline_stats = self.calculate_rolling_average(metric_name, baseline_evals)
        
        if baseline_stats['mean'] is None:
            return []
        
        mean = baseline_stats['mean']
        std = baseline_stats['std']
        
        # Detect anomalies in recent evaluations
        anomalies = []
        upper_threshold = mean + (threshold_multiplier * std)
        lower_threshold = mean - (threshold_multiplier * std)
        
        for eval_data in recent_evals:
            session_id = eval_data.get('session_id', 'unknown')
            summary = eval_data.get('summary', {})
            avg_scores = summary.get('average_scores', {})
            
            if metric_name in avg_scores:
                value = avg_scores[metric_name]
                
                if value > upper_threshold:
                    anomalies.append({
                        'session_id': session_id,
                        'metric': metric_name,
                        'value': value,
                        'type': 'high',
                        'threshold': upper_threshold,
                        'deviation': (value - mean) / std if std > 0 else 0
                    })
                elif value < lower_threshold:
                    anomalies.append({
                        'session_id': session_id,
                        'metric': metric_name,
                        'value': value,
                        'type': 'low',
                        'threshold': lower_threshold,
                        'deviation': (mean - value) / std if std > 0 else 0
                    })
        
        return anomalies
    
    def cluster_sessions(self, n_clusters: int = 3) -> Dict[str, Any]:
        """
        Group similar sessions using simple clustering
        
        Args:
            n_clusters: Number of clusters to create
            
        Returns:
            Clustering results
        """
        evaluations = self.get_recent_evaluations(limit=30)
        
        if len(evaluations) < n_clusters:
            logger.warning("Insufficient data for clustering")
            return {}
        
        # Create feature vectors for each session
        features = []
        session_ids = []
        
        for eval_data in evaluations:
            session_id = eval_data.get('session_id', 'unknown')
            summary = eval_data.get('summary', {})
            avg_scores = summary.get('average_scores', {})
            
            # Create feature vector [task_extraction, memory_relevance, coaching_quality]
            feature_vector = [
                avg_scores.get('task_extraction', 0.5),
                avg_scores.get('memory_relevance', 0.5),
                avg_scores.get('coaching_quality', 0.5)
            ]
            
            features.append(feature_vector)
            session_ids.append(session_id)
        
        if not features:
            return {}
        
        # Simple clustering using K-means logic (without sklearn dependency)
        features_array = np.array(features)
        
        # Initialize cluster centers randomly
        np.random.seed(42)  # For reproducibility
        indices = np.random.choice(len(features), n_clusters, replace=False)
        centers = features_array[indices]
        
        # Simple K-means iteration (max 10 iterations)
        for _ in range(10):
            # Assign points to nearest center
            distances = np.array([[np.linalg.norm(point - center) for center in centers] 
                                 for point in features_array])
            labels = np.argmin(distances, axis=1)
            
            # Update centers
            new_centers = []
            for i in range(n_clusters):
                cluster_points = features_array[labels == i]
                if len(cluster_points) > 0:
                    new_centers.append(np.mean(cluster_points, axis=0))
                else:
                    new_centers.append(centers[i])
            
            centers = np.array(new_centers)
        
        # Classify clusters
        cluster_names = []
        for center in centers:
            avg_score = np.mean(center)
            if avg_score > 0.7:
                cluster_names.append('high_performance')
            elif avg_score > 0.5:
                cluster_names.append('moderate_performance')
            else:
                cluster_names.append('needs_improvement')
        
        # Group sessions by cluster
        clusters = {}
        for session_id, label in zip(session_ids, labels):
            cluster_name = cluster_names[label]
            if cluster_name not in clusters:
                clusters[cluster_name] = []
            clusters[cluster_name].append(session_id)
        
        return {
            'clusters': clusters,
            'centers': centers.tolist(),
            'cluster_names': cluster_names,
            'feature_names': ['task_extraction', 'memory_relevance', 'coaching_quality']
        }
    
    def calculate_personal_baseline(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate personalized baseline metrics
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Personal baseline statistics
        """
        # Get more historical data for baseline
        evaluations = self.get_recent_evaluations(limit=20)
        
        if len(evaluations) < 5:
            logger.warning("Insufficient data for personal baseline")
            return {}
        
        # Calculate baseline for each metric
        metrics = ['task_extraction', 'memory_relevance', 'coaching_quality']
        baseline = {}
        
        for metric in metrics:
            stats = self.calculate_rolling_average(metric, evaluations)
            
            if stats['mean'] is not None:
                # Personal baseline is mean ± 1 std dev
                baseline[metric] = {
                    'mean': stats['mean'],
                    'std': stats['std'],
                    'lower_bound': max(0, stats['mean'] - stats['std']),
                    'upper_bound': min(1, stats['mean'] + stats['std']),
                    'confidence_interval': (
                        max(0, stats['mean'] - 1.96 * stats['std'] / np.sqrt(len(stats['values']))),
                        min(1, stats['mean'] + 1.96 * stats['std'] / np.sqrt(len(stats['values'])))
                    ) if len(stats['values']) > 1 else (stats['mean'], stats['mean'])
                }
        
        # Calculate overall performance level
        overall_mean = np.mean([baseline[m]['mean'] for m in metrics if m in baseline])
        
        if overall_mean > 0.7:
            performance_level = 'high'
        elif overall_mean > 0.5:
            performance_level = 'moderate'
        else:
            performance_level = 'developing'
        
        return {
            'metrics': baseline,
            'overall_performance': performance_level,
            'sample_size': len(evaluations),
            'confidence': 'high' if len(evaluations) >= 10 else 'moderate' if len(evaluations) >= 5 else 'low'
        }
    
    def detect_degradation(self, baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect performance degradation from personal baseline
        
        Args:
            baseline: Personal baseline statistics
            
        Returns:
            List of degradation alerts
        """
        recent_evals = self.get_recent_evaluations(limit=3)
        alerts = []
        
        if not recent_evals or not baseline.get('metrics'):
            return alerts
        
        for eval_data in recent_evals:
            session_id = eval_data.get('session_id', 'unknown')
            summary = eval_data.get('summary', {})
            avg_scores = summary.get('average_scores', {})
            
            for metric, baseline_stats in baseline['metrics'].items():
                if metric in avg_scores:
                    value = avg_scores[metric]
                    
                    # Check if below personal baseline
                    if value < baseline_stats['lower_bound']:
                        severity = 'high' if value < baseline_stats['mean'] - 2 * baseline_stats['std'] else 'moderate'
                        
                        alerts.append({
                            'session_id': session_id,
                            'metric': metric,
                            'value': value,
                            'baseline': baseline_stats['mean'],
                            'deviation': baseline_stats['mean'] - value,
                            'severity': severity,
                            'message': f"{metric.replace('_', ' ').title()} below personal baseline"
                        })
        
        return alerts
    
    def generate_statistical_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive statistical summary
        
        Returns:
            Statistical summary of all metrics
        """
        metrics = ['task_extraction', 'memory_relevance', 'coaching_quality']
        summary = {}
        
        for metric in metrics:
            stats = self.calculate_rolling_average(metric)
            anomalies = self.detect_anomalies(metric)
            
            summary[metric] = {
                'statistics': stats,
                'anomaly_count': len(anomalies),
                'anomalies': anomalies[:3]  # Top 3 anomalies
            }
        
        # Add clustering results
        clustering = self.cluster_sessions()
        
        # Add personal baseline
        baseline = self.calculate_personal_baseline()
        
        # Detect degradation
        degradation_alerts = self.detect_degradation(baseline) if baseline else []
        
        return {
            'metrics': summary,
            'clustering': clustering,
            'baseline': baseline,
            'degradation_alerts': degradation_alerts,
            'generated_at': datetime.now().isoformat()
        }