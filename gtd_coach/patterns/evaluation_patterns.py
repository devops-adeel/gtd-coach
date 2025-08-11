#!/usr/bin/env python3
"""
ADHD-Specific Pattern Analysis from Evaluation Data
Detects time blindness, task switching, and executive function patterns
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)


class ADHDPatternAnalyzer:
    """Analyzes ADHD-specific patterns from evaluation data"""
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize the ADHD pattern analyzer
        
        Args:
            data_dir: Directory containing evaluation data
        """
        self.data_dir = data_dir or Path.home() / "gtd-coach" / "data"
        self.eval_dir = self.data_dir / "evaluations"
        self.patterns_cache = {}
        
    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze a single session for ADHD patterns
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary of detected patterns
        """
        eval_file = self.eval_dir / f"eval_{session_id}.json"
        
        if not eval_file.exists():
            logger.warning(f"Evaluation file not found: {eval_file}")
            return {}
        
        try:
            with open(eval_file) as f:
                eval_data = json.load(f)
            
            patterns = {
                'session_id': session_id,
                'timestamp': eval_data.get('timestamp'),
                'time_blindness': self._calculate_time_blindness_score(eval_data),
                'task_switching': self._analyze_task_switching(eval_data),
                'executive_function': self._assess_executive_function(eval_data),
                'fatigue_indicators': self._detect_fatigue_patterns(eval_data)
            }
            
            # Cache the patterns
            self.patterns_cache[session_id] = patterns
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze session {session_id}: {e}")
            return {}
    
    def _calculate_time_blindness_score(self, eval_data: Dict) -> Dict[str, Any]:
        """
        Calculate time blindness indicators
        
        Time blindness manifests as:
        - Poor time estimation
        - Rush patterns in final minutes
        - Inconsistent pacing
        """
        evaluations = eval_data.get('evaluations', [])
        
        if not evaluations:
            return {'score': None, 'indicators': []}
        
        indicators = []
        scores = []
        
        # Analyze time-related patterns
        for eval_item in evaluations:
            phase = eval_item.get('phase', '')
            
            # Check for time awareness in coaching quality
            if 'coaching_quality' in eval_item:
                quality = eval_item['coaching_quality']
                if isinstance(quality, dict):
                    time_aware = quality.get('time_aware', False)
                    if not time_aware:
                        indicators.append(f"Lack of time awareness in {phase}")
                    scores.append(1.0 if time_aware else 0.0)
            
            # Check for rush patterns (would need timing data)
            # This is a placeholder for when we have more detailed timing
            if eval_item.get('time_remaining', 0) < 2:
                indicators.append(f"Rush pattern detected in {phase}")
        
        # Calculate overall score (1.0 = good time awareness, 0.0 = poor)
        time_blindness_score = np.mean(scores) if scores else 0.5
        
        return {
            'score': time_blindness_score,
            'indicators': indicators,
            'severity': self._classify_severity(1 - time_blindness_score)
        }
    
    def _analyze_task_switching(self, eval_data: Dict) -> Dict[str, Any]:
        """
        Analyze task switching patterns
        
        Task switching difficulties manifest as:
        - Frequent topic changes
        - Incomplete thoughts
        - Returning to previous topics (looping)
        """
        evaluations = eval_data.get('evaluations', [])
        
        task_switches = []
        incomplete_patterns = []
        
        for i, eval_item in enumerate(evaluations):
            # Analyze user input for topic changes
            user_input = eval_item.get('user_input', '')
            
            # Simple heuristic: count sentence fragments and topic markers
            if user_input:
                # Count incomplete sentences (ending with "...")
                if '...' in user_input or user_input.count(',') > 3:
                    incomplete_patterns.append(eval_item.get('phase', f'interaction_{i}'))
                
                # Count topic switches (simplified - would need NLP for accuracy)
                sentences = user_input.split('.')
                if len(sentences) > 2:
                    task_switches.append(len(sentences))
        
        # Calculate switching frequency
        switch_frequency = np.mean(task_switches) if task_switches else 0
        
        return {
            'switch_frequency': switch_frequency,
            'incomplete_thoughts': len(incomplete_patterns),
            'affected_phases': incomplete_patterns,
            'severity': self._classify_severity(switch_frequency / 5.0)  # Normalize to 0-1
        }
    
    def _assess_executive_function(self, eval_data: Dict) -> Dict[str, Any]:
        """
        Assess executive function support effectiveness
        
        Executive function indicators:
        - Task extraction accuracy
        - Memory utilization
        - Structure adherence
        """
        evaluations = eval_data.get('evaluations', [])
        summary = eval_data.get('summary', {})
        
        # Get average scores from summary
        avg_scores = summary.get('average_scores', {})
        
        task_extraction = avg_scores.get('task_extraction', 0.5)
        memory_relevance = avg_scores.get('memory_relevance', 0.5)
        coaching_quality = avg_scores.get('coaching_quality', 0.5)
        
        # Check for executive support in individual evaluations
        exec_support_scores = []
        
        for eval_item in evaluations:
            if 'coaching_quality' in eval_item:
                quality = eval_item['coaching_quality']
                if isinstance(quality, dict):
                    exec_support = quality.get('executive_support', False)
                    structure = quality.get('structure', False)
                    
                    # Combined executive function score
                    score = (1.0 if exec_support else 0.0) * 0.5 + (1.0 if structure else 0.0) * 0.5
                    exec_support_scores.append(score)
        
        exec_function_score = np.mean(exec_support_scores) if exec_support_scores else 0.5
        
        return {
            'overall_score': exec_function_score,
            'task_extraction_accuracy': task_extraction,
            'memory_utilization': memory_relevance,
            'structure_support': coaching_quality,
            'needs_improvement': exec_function_score < 0.6
        }
    
    def _detect_fatigue_patterns(self, eval_data: Dict) -> Dict[str, Any]:
        """
        Detect fatigue and engagement drop-off patterns
        
        Fatigue indicators:
        - Declining scores over time
        - Shorter responses
        - Reduced quality in later phases
        """
        evaluations = eval_data.get('evaluations', [])
        
        if not evaluations:
            return {'detected': False, 'indicators': []}
        
        # Track scores by phase order
        phase_scores = []
        phase_order = ['STARTUP', 'MIND_SWEEP', 'PROJECT_REVIEW', 'PRIORITIZATION', 'WRAP_UP']
        
        for phase in phase_order:
            phase_evals = [e for e in evaluations if e.get('phase') == phase]
            if phase_evals:
                # Get coaching quality scores for this phase
                scores = []
                for eval_item in phase_evals:
                    if 'coaching_quality' in eval_item:
                        quality = eval_item['coaching_quality']
                        if isinstance(quality, dict) and 'score' in quality:
                            scores.append(quality['score'])
                
                if scores:
                    phase_scores.append(np.mean(scores))
        
        # Detect declining pattern
        fatigue_detected = False
        fatigue_indicators = []
        
        if len(phase_scores) >= 3:
            # Check if scores decline (negative slope)
            x = list(range(len(phase_scores)))
            slope = np.polyfit(x, phase_scores, 1)[0] if phase_scores else 0
            
            if slope < -0.1:  # Significant negative slope
                fatigue_detected = True
                fatigue_indicators.append("Declining performance across phases")
            
            # Check for sharp drop in final phases
            if phase_scores[-1] < phase_scores[0] * 0.7:
                fatigue_detected = True
                fatigue_indicators.append("Sharp performance drop in final phase")
        
        return {
            'detected': fatigue_detected,
            'indicators': fatigue_indicators,
            'phase_scores': phase_scores,
            'severity': self._classify_severity(abs(slope) if 'slope' in locals() else 0)
        }
    
    def _classify_severity(self, score: float) -> str:
        """
        Classify pattern severity
        
        Args:
            score: Normalized score (0-1)
            
        Returns:
            Severity classification
        """
        if score < 0.3:
            return 'low'
        elif score < 0.7:
            return 'moderate'
        else:
            return 'high'
    
    def aggregate_patterns(self, session_ids: List[str]) -> Dict[str, Any]:
        """
        Aggregate patterns across multiple sessions
        
        Args:
            session_ids: List of session IDs to analyze
            
        Returns:
            Aggregated pattern analysis
        """
        all_patterns = []
        
        for session_id in session_ids:
            patterns = self.analyze_session(session_id)
            if patterns:
                all_patterns.append(patterns)
        
        if not all_patterns:
            return {}
        
        # Aggregate scores
        time_blindness_scores = [p['time_blindness']['score'] 
                                for p in all_patterns 
                                if p.get('time_blindness', {}).get('score') is not None]
        
        switch_frequencies = [p['task_switching']['switch_frequency'] 
                             for p in all_patterns 
                             if 'task_switching' in p]
        
        exec_scores = [p['executive_function']['overall_score'] 
                      for p in all_patterns 
                      if 'executive_function' in p]
        
        fatigue_count = sum(1 for p in all_patterns 
                          if p.get('fatigue_indicators', {}).get('detected', False))
        
        return {
            'session_count': len(all_patterns),
            'time_blindness': {
                'mean_score': np.mean(time_blindness_scores) if time_blindness_scores else None,
                'std_dev': np.std(time_blindness_scores) if len(time_blindness_scores) > 1 else None,
                'trend': self._calculate_trend(time_blindness_scores)
            },
            'task_switching': {
                'mean_frequency': np.mean(switch_frequencies) if switch_frequencies else None,
                'std_dev': np.std(switch_frequencies) if len(switch_frequencies) > 1 else None,
                'trend': self._calculate_trend(switch_frequencies)
            },
            'executive_function': {
                'mean_score': np.mean(exec_scores) if exec_scores else None,
                'std_dev': np.std(exec_scores) if len(exec_scores) > 1 else None,
                'trend': self._calculate_trend(exec_scores)
            },
            'fatigue': {
                'occurrence_rate': fatigue_count / len(all_patterns) if all_patterns else 0,
                'sessions_affected': fatigue_count
            }
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate trend direction
        
        Args:
            values: List of values over time
            
        Returns:
            Trend classification
        """
        if not values or len(values) < 3:
            return 'insufficient_data'
        
        # Simple linear regression
        x = list(range(len(values)))
        slope = np.polyfit(x, values, 1)[0]
        
        if abs(slope) < 0.01:
            return 'stable'
        elif slope > 0:
            return 'improving'
        else:
            return 'declining'
    
    def generate_insights(self, aggregated_patterns: Dict[str, Any]) -> List[str]:
        """
        Generate actionable insights from patterns
        
        Args:
            aggregated_patterns: Aggregated pattern analysis
            
        Returns:
            List of insight strings
        """
        insights = []
        
        # Time blindness insights
        time_data = aggregated_patterns.get('time_blindness', {})
        if time_data.get('mean_score') is not None:
            score = time_data['mean_score']
            if score < 0.5:
                insights.append("⏰ Time awareness is challenging - consider using visual timers and more frequent time callouts")
            elif time_data.get('trend') == 'declining':
                insights.append("📉 Time awareness has been declining - may need to refresh time management strategies")
        
        # Task switching insights
        switch_data = aggregated_patterns.get('task_switching', {})
        if switch_data.get('mean_frequency', 0) > 3:
            insights.append("🔄 High task switching detected - try grouping similar items and using transition cues")
        
        # Executive function insights
        exec_data = aggregated_patterns.get('executive_function', {})
        if exec_data.get('mean_score', 0) < 0.6:
            insights.append("🧠 Executive function support could be stronger - consider more structured prompts")
        elif exec_data.get('trend') == 'improving':
            insights.append("✨ Executive function support is improving - current strategies are working!")
        
        # Fatigue insights
        fatigue_data = aggregated_patterns.get('fatigue', {})
        if fatigue_data.get('occurrence_rate', 0) > 0.5:
            insights.append("😴 Fatigue detected in >50% of sessions - consider shorter phases or more breaks")
        
        return insights