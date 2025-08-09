#!/usr/bin/env python3
"""
ADHD Pattern Detection for GTD Coach
Analyzes linguistic markers and behavioral patterns based on research
"""

import re
import time
import logging
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class ADHDPatternDetector:
    """Detects ADHD-related patterns in user interactions"""
    
    def __init__(self):
        # Common confusion expressions from research
        self.confusion_markers = [
            r"i don'?t know",
            r"not sure",
            r"maybe",
            r"confused",
            r"forgot",
            r"can'?t remember",
            r"what was",
            r"um+",
            r"uh+",
            r"hmm+"
        ]
        
        # Topic categories for detecting switches
        self.topic_keywords = {
            'work': ['project', 'task', 'meeting', 'deadline', 'boss', 'client', 'email', 'report'],
            'personal': ['home', 'family', 'friend', 'personal', 'hobby', 'exercise', 'health'],
            'financial': ['money', 'pay', 'bill', 'budget', 'expense', 'save', 'cost'],
            'learning': ['learn', 'study', 'course', 'book', 'skill', 'practice', 'read'],
            'admin': ['appointment', 'schedule', 'calendar', 'plan', 'organize', 'clean'],
            'tech': ['computer', 'software', 'app', 'phone', 'website', 'code', 'system']
        }
        
    def analyze_mindsweep_coherence(self, items: List[str]) -> Dict[str, any]:
        """
        Analyze coherence and patterns in mindsweep items
        
        Args:
            items: List of mindsweep items
            
        Returns:
            Dictionary of analysis metrics
        """
        if not items:
            return {
                'coherence_score': 0,
                'topic_switches': 0,
                'lexical_diversity': 0,
                'fragmentation_indicators': []
            }
        
        # Analyze topic switches
        topic_sequence = []
        for item in items:
            topic = self._categorize_topic(item.lower())
            topic_sequence.append(topic)
        
        topic_switches = self._count_topic_switches(topic_sequence)
        
        # Calculate lexical diversity
        all_words = ' '.join(items).lower().split()
        unique_words = set(all_words)
        lexical_diversity = len(unique_words) / len(all_words) if all_words else 0
        
        # Detect fragmentation
        fragmentation_indicators = []
        for i, item in enumerate(items):
            if len(item.split()) < 3:  # Very short items
                fragmentation_indicators.append({
                    'index': i,
                    'type': 'short_fragment',
                    'content': item
                })
            
            # Check for confusion markers
            for marker in self.confusion_markers:
                if re.search(marker, item.lower()):
                    fragmentation_indicators.append({
                        'index': i,
                        'type': 'confusion_expression',
                        'marker': marker,
                        'content': item
                    })
                    break
        
        # Calculate coherence score (0-1)
        coherence_score = self._calculate_coherence_score(
            items, topic_switches, lexical_diversity, fragmentation_indicators
        )
        
        return {
            'coherence_score': coherence_score,
            'topic_switches': topic_switches,
            'topic_sequence': topic_sequence,
            'lexical_diversity': round(lexical_diversity, 3),
            'fragmentation_indicators': fragmentation_indicators,
            'average_item_length': sum(len(item.split()) for item in items) / len(items)
        }
    
    def calculate_focus_score(self, phase_data: Dict[str, any]) -> Dict[str, float]:
        """
        Calculate focus quality score for a phase
        
        Args:
            phase_data: Data about the phase including timing and interactions
            
        Returns:
            Dictionary with focus metrics
        """
        focus_metrics = {
            'overall_score': 1.0,
            'time_efficiency': 1.0,
            'response_consistency': 1.0,
            'task_completion': 1.0
        }
        
        # Time efficiency (did they use allocated time well?)
        if 'duration_seconds' in phase_data and 'expected_duration' in phase_data:
            actual = phase_data['duration_seconds']
            expected = phase_data['expected_duration']
            # Score higher if they used 70-100% of time, lower if rushed or overtime
            if actual < expected * 0.7:
                focus_metrics['time_efficiency'] = actual / (expected * 0.7)
            elif actual > expected * 1.2:
                focus_metrics['time_efficiency'] = max(0.5, 1 - (actual - expected) / expected)
        
        # Response consistency
        if 'interactions' in phase_data:
            response_times = []
            for interaction in phase_data['interactions']:
                if 'response_time' in interaction:
                    response_times.append(interaction['response_time'])
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                variance = sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
                # Lower variance = more consistent = better focus
                focus_metrics['response_consistency'] = max(0.3, 1 - (variance ** 0.5) / avg_time)
        
        # Task completion
        if 'completed_items' in phase_data and 'total_items' in phase_data:
            focus_metrics['task_completion'] = phase_data['completed_items'] / phase_data['total_items']
        
        # Calculate overall score
        focus_metrics['overall_score'] = sum(focus_metrics.values()) / len(focus_metrics)
        
        return focus_metrics
    
    def detect_task_switching(self, current_item: str, previous_item: Optional[str],
                            time_between: Optional[float] = None) -> Optional[Dict[str, any]]:
        """
        Detect if a task switch occurred between two items
        
        Args:
            current_item: Current mindsweep item
            previous_item: Previous mindsweep item
            time_between: Time in seconds between items
            
        Returns:
            Task switch data if detected, None otherwise
        """
        if not previous_item:
            return None
        
        current_topic = self._categorize_topic(current_item.lower())
        previous_topic = self._categorize_topic(previous_item.lower())
        
        if current_topic != previous_topic:
            switch_data = {
                'from_topic': previous_topic,
                'to_topic': current_topic,
                'from_item': previous_item,
                'to_item': current_item,
                'abrupt': time_between < 2.0 if time_between else False
            }
            
            # Check if the switch seems fragmented
            if any(re.search(marker, current_item.lower()) for marker in self.confusion_markers):
                switch_data['includes_confusion'] = True
            
            return switch_data
        
        return None
    
    def analyze_interaction_patterns(self, interactions: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Analyze patterns across multiple interactions
        
        Args:
            interactions: List of interaction data
            
        Returns:
            Pattern analysis results
        """
        clarification_requests = 0
        off_topic_count = 0
        response_lengths = []
        
        for interaction in interactions:
            content = interaction.get('content', '').lower()
            
            # Count clarification requests
            if any(phrase in content for phrase in ['what do you mean', 'can you explain', 
                                                   'not sure what', "don't understand"]):
                clarification_requests += 1
            
            # Detect potential off-topic responses
            if interaction.get('role') == 'user' and 'expected_topic' in interaction:
                actual_topic = self._categorize_topic(content)
                if actual_topic != interaction['expected_topic']:
                    off_topic_count += 1
            
            # Track response length
            response_lengths.append(len(content.split()))
        
        avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0
        
        return {
            'clarification_rate': clarification_requests / len(interactions) if interactions else 0,
            'off_topic_rate': off_topic_count / len(interactions) if interactions else 0,
            'average_response_length': avg_response_length,
            'response_length_variance': self._calculate_variance(response_lengths),
            'total_interactions': len(interactions)
        }
    
    def _categorize_topic(self, text: str) -> str:
        """Categorize text into a topic based on keywords"""
        topic_scores = Counter()
        
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    topic_scores[topic] += 1
        
        if topic_scores:
            return topic_scores.most_common(1)[0][0]
        return 'other'
    
    def _count_topic_switches(self, topic_sequence: List[str]) -> int:
        """Count the number of topic switches in a sequence"""
        if len(topic_sequence) < 2:
            return 0
        
        switches = 0
        for i in range(1, len(topic_sequence)):
            if topic_sequence[i] != topic_sequence[i-1]:
                switches += 1
        
        return switches
    
    def _calculate_coherence_score(self, items: List[str], topic_switches: int,
                                 lexical_diversity: float, 
                                 fragmentation_indicators: List[Dict]) -> float:
        """
        Calculate overall coherence score (0-1)
        Higher score = more coherent
        """
        # Base score
        score = 1.0
        
        # Penalize for topic switches (normalized by number of items)
        switch_penalty = (topic_switches / max(len(items) - 1, 1)) * 0.3
        score -= switch_penalty
        
        # Penalize for low lexical diversity (indicates repetition)
        if lexical_diversity < 0.3:
            score -= 0.2
        elif lexical_diversity > 0.8:
            score -= 0.1  # Too high might indicate disconnected thoughts
        
        # Penalize for fragmentation
        fragmentation_penalty = (len(fragmentation_indicators) / len(items)) * 0.4
        score -= fragmentation_penalty
        
        return max(0, min(1, score))
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def analyze_timing_switches(self, timing_data: Dict) -> Dict:
        """Analyze timing data for ADHD-specific patterns
        
        Args:
            timing_data: Data from TimingAPI.analyze_timing_patterns_async()
        
        Returns:
            Dictionary with ADHD pattern analysis
        """
        if not timing_data or timing_data.get('data_type') != 'detailed':
            return {
                'patterns_detected': False,
                'adhd_indicators': [],
                'recommendations': []
            }
        
        focus_metrics = timing_data.get('focus_metrics', {})
        switch_analysis = timing_data.get('switch_analysis', {})
        
        adhd_indicators = []
        recommendations = []
        
        # Analyze focus score
        focus_score = focus_metrics.get('focus_score', 100)
        if focus_score < 40:
            adhd_indicators.append({
                'type': 'low_focus',
                'severity': 'high',
                'value': focus_score,
                'message': f'Focus score of {focus_score} indicates severe attention fragmentation'
            })
            recommendations.append('Consider time-blocking with 25-minute Pomodoros')
        elif focus_score < 60:
            adhd_indicators.append({
                'type': 'moderate_focus',
                'severity': 'medium',
                'value': focus_score,
                'message': f'Focus score of {focus_score} shows frequent context switching'
            })
            recommendations.append('Try batching similar tasks together')
        
        # Analyze switch patterns
        switches_per_hour = focus_metrics.get('switches_per_hour', 0)
        if switches_per_hour > 8:
            adhd_indicators.append({
                'type': 'excessive_switching',
                'severity': 'high',
                'value': switches_per_hour,
                'message': f'{switches_per_hour:.1f} switches/hour is well above typical'
            })
            recommendations.append('Use app blockers during focus time')
        
        # Analyze scatter periods
        scatter_count = focus_metrics.get('scatter_periods_count', 0)
        if scatter_count > 2:
            adhd_indicators.append({
                'type': 'scatter_episodes',
                'severity': 'medium',
                'value': scatter_count,
                'message': f'{scatter_count} scatter periods detected'
            })
            recommendations.append('Schedule breaks to prevent overwhelm')
        
        # Analyze hyperfocus
        hyperfocus_score = focus_metrics.get('hyperfocus_score', 0)
        if hyperfocus_score > 80:
            adhd_indicators.append({
                'type': 'hyperfocus',
                'severity': 'info',
                'value': hyperfocus_score,
                'message': 'Strong hyperfocus periods detected - leverage these times'
            })
            recommendations.append('Schedule important work during hyperfocus windows')
        
        # Check for app-hopping patterns
        if switch_analysis.get('switch_patterns'):
            app_patterns = [p for p in switch_analysis['switch_patterns'] 
                           if any(app in p[0] for app in ['Safari', 'Chrome', 'Mail', 'Slack'])]
            if len(app_patterns) >= 3:
                adhd_indicators.append({
                    'type': 'app_hopping',
                    'severity': 'medium',
                    'value': len(app_patterns),
                    'message': 'Frequent switching between communication/browser apps'
                })
                recommendations.append('Set specific times for email/chat checking')
        
        return {
            'patterns_detected': len(adhd_indicators) > 0,
            'adhd_indicators': adhd_indicators,
            'recommendations': recommendations,
            'focus_profile': self._determine_focus_profile(focus_metrics)
        }
    
    def _determine_focus_profile(self, focus_metrics: Dict) -> str:
        """Determine user's focus profile based on metrics"""
        focus_score = focus_metrics.get('focus_score', 50)
        hyperfocus_score = focus_metrics.get('hyperfocus_score', 0)
        focus_periods = focus_metrics.get('focus_periods_count', 0)
        scatter_periods = focus_metrics.get('scatter_periods_count', 0)
        
        if hyperfocus_score > 70 and focus_score > 60:
            return "Hyperfocus-capable: Strong focus when engaged"
        elif focus_score > 70:
            return "Steady focus: Consistent attention management"
        elif scatter_periods > focus_periods:
            return "Scattered: Frequent attention shifts dominate"
        elif focus_periods > 0 and focus_score < 50:
            return "Mixed: Alternates between focus and distraction"
        else:
            return "Variable: Inconsistent focus patterns"
    
    def correlate_timing_with_mindsweep(self, timing_data: Dict, 
                                       mindsweep_analysis: Dict) -> Dict:
        """Correlate timing patterns with mindsweep coherence
        
        Args:
            timing_data: Timing analysis results
            mindsweep_analysis: Mindsweep coherence analysis
        
        Returns:
            Correlation insights
        """
        correlations = []
        
        # Check if low focus correlates with fragmented mindsweep
        if timing_data.get('focus_metrics'):
            focus_score = timing_data['focus_metrics'].get('focus_score', 100)
            coherence_score = mindsweep_analysis.get('coherence_score', 1) * 100
            
            if focus_score < 50 and coherence_score < 50:
                correlations.append({
                    'type': 'double_fragmentation',
                    'message': 'Both work patterns and thought capture show fragmentation',
                    'insight': 'Consider environmental changes to reduce distractions'
                })
            elif focus_score > 70 and coherence_score > 70:
                correlations.append({
                    'type': 'strong_alignment',
                    'message': 'Good focus aligns with organized thinking',
                    'insight': 'Current strategies are working well'
                })
            elif abs(focus_score - coherence_score) > 30:
                correlations.append({
                    'type': 'mismatch',
                    'message': f'Focus ({focus_score}) and coherence ({coherence_score:.0f}) diverge',
                    'insight': 'Different factors may affect work vs. planning'
                })
        
        # Check if many switches correlate with many topics
        if timing_data.get('switch_analysis') and mindsweep_analysis.get('topic_switches'):
            work_switches = timing_data['switch_analysis'].get('switches_per_hour', 0)
            thought_switches = mindsweep_analysis.get('topic_switches', 0)
            
            if work_switches > 5 and thought_switches > 5:
                correlations.append({
                    'type': 'high_switching',
                    'message': 'High context switching in both work and planning',
                    'insight': 'May benefit from mindfulness or focus exercises'
                })
        
        return {
            'correlations': correlations,
            'overall_pattern': self._determine_overall_pattern(correlations)
        }
    
    def _determine_overall_pattern(self, correlations: List[Dict]) -> str:
        """Determine overall ADHD pattern from correlations"""
        if not correlations:
            return "No clear pattern detected"
        
        types = [c['type'] for c in correlations]
        
        if 'double_fragmentation' in types:
            return "Significant ADHD symptoms - comprehensive support needed"
        elif 'strong_alignment' in types:
            return "Well-managed ADHD - current strategies effective"
        elif 'high_switching' in types:
            return "Classic ADHD switching pattern - focus on reduction strategies"
        elif 'mismatch' in types:
            return "Complex pattern - may need targeted interventions"
        else:
            return "Mixed indicators - monitor patterns over time"