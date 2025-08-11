#!/usr/bin/env python3
"""
User State Monitor for Real-time Adaptation
Monitors user state from interaction patterns and signals
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UserStateMonitor:
    """Monitors and assesses user state from existing signals"""
    
    def __init__(self):
        """Initialize state monitor with default values"""
        # Core state indicators
        self.energy_level = "normal"  # low/normal/high
        self.confusion_level = 0.0    # 0-1 scale
        self.engagement_level = 1.0   # 0-1 scale
        self.stress_indicators = 0    # count of stress signals
        
        # Tracking variables
        self.recent_response_times = []  # Last 5 response times
        self.confusion_markers_count = 0
        self.short_response_count = 0
        self.context_switches = 0
        self.last_update_time = datetime.now()
        
        # Thresholds for state detection
        self.thresholds = {
            'slow_response': 10.0,      # seconds
            'fast_response': 2.0,       # seconds (too quick)
            'short_response_length': 5,  # words
            'confusion_threshold': 0.5,
            'fatigue_threshold': 3,     # consecutive slow/short responses
            'stress_threshold': 2       # stress indicators before flagging
        }
        
        # History for pattern detection
        self.state_history = []
        self.adaptation_history = []
    
    def update_from_interaction(self, 
                               response_time: float,
                               content: str,
                               pattern_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update user state based on interaction data
        
        Args:
            response_time: Time taken to respond in seconds
            content: User's response content
            pattern_data: Pattern detection data from ADHDPatternDetector
            
        Returns:
            Dictionary of state changes detected
        """
        state_changes = {}
        
        # Track response time
        self.recent_response_times.append(response_time)
        if len(self.recent_response_times) > 5:
            self.recent_response_times.pop(0)
        
        # Detect fatigue from slow responses
        if response_time > self.thresholds['slow_response']:
            if self._check_fatigue_pattern():
                old_energy = self.energy_level
                self.energy_level = "low"
                if old_energy != "low":
                    state_changes['energy'] = "low"
                    logger.info("Fatigue detected: switching to low energy mode")
        
        # Detect disengagement from very quick responses
        elif response_time < self.thresholds['fast_response']:
            word_count = len(content.split())
            if word_count < self.thresholds['short_response_length']:
                self.short_response_count += 1
                if self.short_response_count >= 3:
                    old_engagement = self.engagement_level
                    self.engagement_level = max(0.3, self.engagement_level - 0.2)
                    if old_engagement - self.engagement_level > 0.1:
                        state_changes['engagement'] = "decreased"
                        logger.info(f"Engagement decreased to {self.engagement_level:.1f}")
        else:
            # Normal response - gradually restore energy
            if self.energy_level == "low" and len(self.recent_response_times) >= 3:
                avg_recent = sum(self.recent_response_times[-3:]) / 3
                if avg_recent < self.thresholds['slow_response']:
                    self.energy_level = "normal"
                    state_changes['energy'] = "recovered"
        
        # Check for confusion markers
        confusion_phrases = [
            "i don't understand", "confused", "not sure", 
            "what do you mean", "can you explain", "lost",
            "don't get it", "huh", "wait what"
        ]
        
        content_lower = content.lower()
        for phrase in confusion_phrases:
            if phrase in content_lower:
                self.confusion_markers_count += 1
                break
        
        # Update confusion level
        if self.confusion_markers_count > 0:
            old_confusion = self.confusion_level
            self.confusion_level = min(1.0, self.confusion_markers_count * 0.25)
            if self.confusion_level > self.thresholds['confusion_threshold'] and \
               old_confusion <= self.thresholds['confusion_threshold']:
                state_changes['confusion'] = "high"
                logger.info(f"High confusion detected: {self.confusion_level:.2f}")
        
        # Process pattern detection data if provided
        if pattern_data:
            if pattern_data.get('topic_switches', 0) > 2:
                self.context_switches = pattern_data['topic_switches']
                self.stress_indicators += 1
                if self.stress_indicators >= self.thresholds['stress_threshold']:
                    state_changes['stress'] = "elevated"
                    logger.info("Elevated stress from context switching")
            
            # Reset stress if coherence improves
            if pattern_data.get('coherence_score', 0) > 0.7:
                if self.stress_indicators > 0:
                    self.stress_indicators = max(0, self.stress_indicators - 1)
        
        # Record state snapshot
        self.state_history.append({
            'timestamp': datetime.now(),
            'energy': self.energy_level,
            'confusion': self.confusion_level,
            'engagement': self.engagement_level,
            'stress': self.stress_indicators,
            'changes': state_changes
        })
        
        # Keep only last 20 states
        if len(self.state_history) > 20:
            self.state_history.pop(0)
        
        self.last_update_time = datetime.now()
        return state_changes
    
    def _check_fatigue_pattern(self) -> bool:
        """
        Check if recent interactions show fatigue pattern
        
        Returns:
            True if fatigue pattern detected
        """
        if len(self.recent_response_times) < 3:
            return False
        
        # Check for consistently slow responses
        slow_count = sum(1 for t in self.recent_response_times[-3:] 
                        if t > self.thresholds['slow_response'])
        
        return slow_count >= 2
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current user state
        
        Returns:
            Dictionary of current state values
        """
        return {
            'energy_level': self.energy_level,
            'confusion_level': self.confusion_level,
            'engagement_level': self.engagement_level,
            'stress_indicators': self.stress_indicators,
            'context_switches': self.context_switches,
            'needs_break': self.energy_level == "low" and self.stress_indicators > 0
        }
    
    def get_adaptation_needs(self) -> Dict[str, Any]:
        """
        Determine needed adaptations based on current state
        
        Returns:
            Dictionary of adaptation recommendations
        """
        adaptations = {}
        
        # Low energy adaptations
        if self.energy_level == "low":
            adaptations.update({
                'prompt_length': 'shorter',
                'pace': 'slower',
                'encouragement': 'high',
                'max_tokens': 100
            })
        
        # High confusion adaptations
        if self.confusion_level > self.thresholds['confusion_threshold']:
            adaptations.update({
                'language': 'simpler',
                'structure': 'more',
                'examples': True,
                'step_by_step': True
            })
        
        # Low engagement adaptations
        if self.engagement_level < 0.6:
            adaptations.update({
                'energy': 'higher',
                'variety': True,
                'celebration': True,
                'personalization': 'high'
            })
        
        # High stress adaptations
        if self.stress_indicators >= self.thresholds['stress_threshold']:
            adaptations.update({
                'tone': 'calming',
                'pace': 'slower',
                'breaks': 'suggest',
                'grounding': True
            })
        
        # Record what adaptations were recommended
        if adaptations:
            self.adaptation_history.append({
                'timestamp': datetime.now(),
                'state': self.get_state(),
                'adaptations': adaptations
            })
        
        return adaptations
    
    def reset_phase(self):
        """Reset temporary counters at phase boundaries"""
        self.confusion_markers_count = 0
        self.short_response_count = 0
        self.context_switches = 0
        logger.debug("Phase state counters reset")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about state monitoring
        
        Returns:
            Dictionary of monitoring metrics
        """
        return {
            'total_states_tracked': len(self.state_history),
            'adaptations_triggered': len(self.adaptation_history),
            'current_state': self.get_state(),
            'avg_response_time': sum(self.recent_response_times) / len(self.recent_response_times) 
                                if self.recent_response_times else 0,
            'time_since_last_update': (datetime.now() - self.last_update_time).total_seconds()
        }