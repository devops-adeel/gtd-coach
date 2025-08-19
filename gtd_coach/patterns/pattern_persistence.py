#!/usr/bin/env python3
"""
Pattern Persistence for ADHD Pattern Detection
Provides lightweight cross-session tracking of ADHD patterns
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternPersistence:
    """
    Lightweight JSON-based persistence for ADHD patterns
    Tracks patterns across sessions without complex database dependencies
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize pattern persistence
        
        Args:
            data_dir: Directory for storing pattern data (defaults to ~/.gtd_coach/patterns)
        """
        if data_dir is None:
            self.data_dir = Path.home() / '.gtd_coach' / 'patterns'
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.data_dir / 'sessions'
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Cache for current session
        self.current_session_patterns = []
        self.current_interventions = []
    
    def save_session_patterns(self, patterns: List[Dict[str, Any]], 
                             interventions: List[Dict[str, Any]],
                             outcomes: Dict[str, Any]) -> str:
        """
        Save patterns, interventions, and outcomes from a session
        
        Args:
            patterns: List of detected ADHD patterns
            interventions: List of interventions applied
            outcomes: Session outcomes (phase completion, focus scores, etc.)
        
        Returns:
            Session ID for reference
        """
        import uuid
        # Use timestamp plus UUID suffix to ensure uniqueness
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        unique_suffix = str(uuid.uuid4())[:8]
        session_id = f"{timestamp}_{unique_suffix}"
        session_file = self.sessions_dir / f'{session_id}.json'
        
        session_data = {
            'session_id': session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'patterns': patterns,
            'interventions': interventions,
            'outcomes': outcomes,
            'effectiveness': self._calculate_effectiveness(patterns, outcomes)
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"Saved session patterns to {session_file}")
        return session_id
    
    def load_recent_patterns(self, weeks_back: int = 4) -> List[Dict[str, Any]]:
        """
        Load patterns from recent sessions
        
        Args:
            weeks_back: Number of weeks to look back
        
        Returns:
            List of patterns that appeared 3+ times
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
        pattern_counts = defaultdict(int)
        pattern_details = {}
        
        # Scan session files
        for session_file in sorted(self.sessions_dir.glob('*.json'), reverse=True):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Check if session is within time range - handle both string and missing timestamp
                timestamp = session_data.get('timestamp')
                if timestamp:
                    session_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if session_time < cutoff_date:
                        continue
                
                # Count patterns
                for pattern in session_data.get('patterns', []):
                    pattern_key = pattern.get('type', 'unknown')
                    pattern_counts[pattern_key] += 1
                    
                    # Store latest details
                    if pattern_key not in pattern_details:
                        pattern_details[pattern_key] = pattern
                
            except Exception as e:
                logger.debug(f"Failed to load session {session_file}: {e}")
        
        # Find recurring patterns (3+ appearances) OR all patterns if threshold not met
        recurring = []
        min_count = 3 if sum(pattern_counts.values()) >= 9 else 1  # Adaptive threshold
        
        for pattern_type, count in pattern_counts.items():
            if count >= min_count:
                details = pattern_details.get(pattern_type, {})
                recurring.append({
                    'pattern': pattern_type,
                    'frequency': count,
                    'weeks_seen': min(weeks_back, count),  # Approximate
                    'severity': details.get('severity', 'unknown'),
                    'recommendation': self._get_recommendation(pattern_type)
                })
        
        # Sort by frequency
        recurring.sort(key=lambda x: x['frequency'], reverse=True)
        
        return recurring
    
    def track_intervention(self, intervention_type: str, context: Dict[str, Any]) -> None:
        """
        Track an intervention that was applied
        
        Args:
            intervention_type: Type of intervention (e.g., 'timer_alert', 'context_grouping')
            context: Context about when/why intervention was applied
        """
        self.current_interventions.append({
            'type': intervention_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context
        })
    
    def track_pattern(self, pattern: Dict[str, Any]) -> None:
        """
        Track a detected pattern during the session
        
        Args:
            pattern: Pattern data from ADHDPatternDetector
        """
        pattern['detected_at'] = datetime.now(timezone.utc).isoformat()
        self.current_session_patterns.append(pattern)
    
    def get_intervention_history(self, intervention_type: str) -> Dict[str, Any]:
        """
        Get effectiveness history for a specific intervention
        
        Args:
            intervention_type: Type of intervention to query
        
        Returns:
            History with effectiveness metrics
        """
        effectiveness_scores = []
        contexts = []
        
        # Scan recent sessions
        for session_file in sorted(self.sessions_dir.glob('*.json'), reverse=True)[:20]:
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Find interventions of this type
                for intervention in session_data.get('interventions', []):
                    if intervention.get('type') == intervention_type:
                        effectiveness = session_data.get('effectiveness', 0.5)
                        effectiveness_scores.append(effectiveness)
                        contexts.append(intervention.get('context', {}))
                
            except Exception as e:
                logger.warning(f"Failed to analyze session {session_file}: {e}")
        
        if not effectiveness_scores:
            return {'found': False}
        
        return {
            'found': True,
            'average_effectiveness': sum(effectiveness_scores) / len(effectiveness_scores),
            'total_uses': len(effectiveness_scores),
            'recent_contexts': contexts[:3]
        }
    
    def _calculate_effectiveness(self, patterns: List[Dict[str, Any]], 
                                outcomes: Dict[str, Any]) -> float:
        """
        Calculate intervention effectiveness based on outcomes
        
        Args:
            patterns: Detected patterns
            outcomes: Session outcomes
        
        Returns:
            Effectiveness score (0-1)
        """
        score = 0.5  # Base score
        
        # Positive indicators
        if outcomes.get('all_phases_completed'):
            score += 0.2
        if outcomes.get('focus_score', 0) > 60:
            score += 0.1
        if outcomes.get('coherence_score', 0) > 0.6:
            score += 0.1
        
        # Negative indicators
        high_severity_patterns = [p for p in patterns if p.get('severity') == 'high']
        if len(high_severity_patterns) > 2:
            score -= 0.1
        
        # Context switches
        if outcomes.get('context_switches', 0) > 10:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_recommendation(self, pattern_type: str) -> str:
        """Get recommendation for a pattern type"""
        recommendations = {
            'fragmented_capture': 'Try grouping items by context (@computer, @home)',
            'low_focus': 'Consider shorter review sessions or more frequent breaks',
            'task_switching': 'Batch similar items together before moving on',
            'confusion_expression': 'Break complex thoughts into smaller, concrete actions',
            'rushed_completion': 'Front-load important items in each phase',
            'topic_jumps': 'Use a physical notepad for stray thoughts'
        }
        return recommendations.get(pattern_type, 'Monitor this pattern')
    
    def get_pattern_evolution(self, pattern_type: str, weeks: int = 8) -> List[Dict[str, Any]]:
        """
        Track how a specific pattern has evolved over time
        
        Args:
            pattern_type: Type of pattern to track
            weeks: Number of weeks to analyze
        
        Returns:
            Evolution history
        """
        evolution = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        
        for session_file in sorted(self.sessions_dir.glob('*.json')):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                session_time = datetime.fromisoformat(session_data['timestamp'].replace('Z', '+00:00'))
                if session_time < cutoff_date:
                    continue
                
                # Find this pattern type
                for pattern in session_data.get('patterns', []):
                    if pattern.get('type') == pattern_type:
                        evolution.append({
                            'date': session_time.date().isoformat(),
                            'severity': pattern.get('severity', 'unknown'),
                            'interventions': [i['type'] for i in session_data.get('interventions', [])],
                            'effectiveness': session_data.get('effectiveness', 0.5)
                        })
                        break
                
            except Exception as e:
                logger.warning(f"Failed to analyze evolution from {session_file}: {e}")
        
        return evolution
    
    def clear_current_session(self) -> None:
        """Clear current session cache"""
        self.current_session_patterns = []
        self.current_interventions = []