#!/usr/bin/env python3
"""
Pattern Evolution Tracking for ADHD Patterns
Tracks how patterns change over time without deleting history
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class EvolutionType(Enum):
    """Types of pattern evolution"""
    IMPROVED = "improved"           # Pattern severity decreased
    WORSENED = "worsened"          # Pattern severity increased  
    TRANSFORMED = "transformed"     # Pattern changed to different type
    RESOLVED = "resolved"          # Pattern no longer appears
    EMERGED = "emerged"            # New pattern appeared


class PatternEvolution:
    """
    Tracks pattern evolution without deleting history
    Implements supersession chains inspired by graphiti-claude-code-mcp
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize pattern evolution tracker
        
        Args:
            data_dir: Directory for storing evolution data
        """
        if data_dir is None:
            self.data_dir = Path.home() / '.gtd_coach' / 'evolution'
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.evolution_file = self.data_dir / 'pattern_evolution.json'
        self.chains_file = self.data_dir / 'evolution_chains.json'
        
        # Load existing evolution data
        self.evolution_history = self._load_evolution_history()
        self.evolution_chains = self._load_evolution_chains()
    
    def track_evolution(self, old_pattern: Dict[str, any], 
                       new_pattern: Dict[str, any],
                       intervention: Optional[str] = None) -> str:
        """
        Track evolution from one pattern to another
        Never deletes old patterns, only marks as superseded
        
        Args:
            old_pattern: Previous pattern state
            new_pattern: Current pattern state
            intervention: Intervention that may have caused the change
        
        Returns:
            Evolution ID for reference
        """
        evolution_id = f"evo_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        # Determine evolution type
        evolution_type = self._determine_evolution_type(old_pattern, new_pattern)
        
        # Create evolution record
        evolution_record = {
            'id': evolution_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': evolution_type.value,
            'old_pattern': old_pattern,
            'new_pattern': new_pattern,
            'intervention': intervention,
            'supersedes': old_pattern.get('id'),
            'improvement_score': self._calculate_improvement(old_pattern, new_pattern)
        }
        
        # Add to history (append-only)
        self.evolution_history.append(evolution_record)
        
        # Update chains
        self._update_evolution_chain(old_pattern.get('id', 'unknown'), evolution_record)
        
        # Save to disk
        self._save_evolution_history()
        self._save_evolution_chains()
        
        logger.info(f"Tracked evolution {evolution_id}: {evolution_type.value}")
        return evolution_id
    
    def get_improvement_story(self, pattern_type: str) -> Optional[str]:
        """
        Generate a narrative of how a pattern has improved
        
        Args:
            pattern_type: Type of pattern to analyze
        
        Returns:
            Improvement narrative or None
        """
        # Look for evolution records with this pattern type
        relevant_evolutions = []
        for record in self.evolution_history:
            old = record.get('old_pattern', {})
            new = record.get('new_pattern', {})
            if old.get('type') == pattern_type or new.get('type') == pattern_type:
                relevant_evolutions.append(record)
        
        if not relevant_evolutions:
            return None
        
        # Sort by timestamp
        relevant_evolutions.sort(key=lambda x: x.get('timestamp', ''))
        
        # Find improvements
        improvements = []
        first_severity = None
        last_severity = None
        
        for evo in relevant_evolutions:
            if first_severity is None:
                first_severity = evo.get('old_pattern', {}).get('severity', 'medium')
            last_severity = evo.get('new_pattern', {}).get('severity', 'medium')
            
            if evo.get('improvement_score', 0) > 0:
                intervention = evo.get('intervention', 'changes')
                if intervention not in improvements:
                    improvements.append(intervention)
        
        if not improvements:
            return None
        
        severity_change = self._compare_severity(first_severity, last_severity)
        
        if severity_change > 0:
            story = f"Your {pattern_type} pattern has improved from "
            story += f"{first_severity} to {last_severity}. "
            story += f"Key interventions: {', '.join(improvements[:2])}"
            return story
        elif severity_change == 0:
            return f"Your {pattern_type} pattern remains stable. Tried: {', '.join(improvements[:2])}"
        else:
            return None  # Don't highlight worsening
    
    def get_pattern_lineage(self, pattern_id: str) -> List[Dict[str, any]]:
        """
        Get complete lineage of a pattern (all evolutions)
        
        Args:
            pattern_id: Pattern identifier
        
        Returns:
            List of evolution records
        """
        if pattern_id not in self.evolution_chains:
            return []
        
        return self.evolution_chains[pattern_id]
    
    def find_successful_interventions(self, pattern_type: str) -> List[Tuple[str, float]]:
        """
        Find interventions that successfully improved a pattern type
        
        Args:
            pattern_type: Type of pattern
        
        Returns:
            List of (intervention, success_rate) tuples
        """
        intervention_scores = {}
        intervention_counts = {}
        
        for record in self.evolution_history:
            old = record.get('old_pattern', {})
            if old.get('type') != pattern_type:
                continue
            
            intervention = record.get('intervention')
            if not intervention:
                continue
            
            score = record.get('improvement_score', 0)
            
            if intervention not in intervention_scores:
                intervention_scores[intervention] = 0
                intervention_counts[intervention] = 0
            
            intervention_scores[intervention] += score
            intervention_counts[intervention] += 1
        
        # Calculate success rates
        results = []
        for intervention, total_score in intervention_scores.items():
            count = intervention_counts[intervention]
            if count > 0:
                avg_score = total_score / count
                if avg_score > 0:  # Only include successful ones
                    results.append((intervention, avg_score))
        
        # Sort by effectiveness
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def get_recent_evolutions(self, days: int = 30) -> List[Dict[str, any]]:
        """
        Get recent pattern evolutions
        
        Args:
            days: Number of days to look back
        
        Returns:
            Recent evolution records
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        recent = []
        
        for record in self.evolution_history:
            timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
            if timestamp.timestamp() > cutoff:
                recent.append(record)
        
        return recent
    
    def _determine_evolution_type(self, old_pattern: Dict, new_pattern: Dict) -> EvolutionType:
        """Determine the type of evolution between patterns"""
        if not new_pattern or new_pattern.get('severity') == 'none':
            return EvolutionType.RESOLVED
        
        if not old_pattern or old_pattern.get('severity') == 'none':
            return EvolutionType.EMERGED
        
        old_type = old_pattern.get('type')
        new_type = new_pattern.get('type')
        
        if old_type != new_type:
            return EvolutionType.TRANSFORMED
        
        severity_change = self._compare_severity(
            old_pattern.get('severity', 'medium'),
            new_pattern.get('severity', 'medium')
        )
        
        if severity_change > 0:
            return EvolutionType.IMPROVED
        elif severity_change < 0:
            return EvolutionType.WORSENED
        else:
            return EvolutionType.TRANSFORMED
    
    def _compare_severity(self, old_severity: str, new_severity: str) -> int:
        """
        Compare pattern severities
        Returns: positive if improved, negative if worsened, 0 if same
        """
        severity_levels = {
            'none': 0,
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        
        old_level = severity_levels.get(old_severity, 2)
        new_level = severity_levels.get(new_severity, 2)
        
        return old_level - new_level  # Positive means improvement
    
    def _calculate_improvement(self, old_pattern: Dict, new_pattern: Dict) -> float:
        """
        Calculate improvement score between patterns
        
        Returns:
            Score from -1 (worsened) to 1 (improved)
        """
        if not old_pattern or not new_pattern:
            return 0.0
        
        # Compare severity
        severity_change = self._compare_severity(
            old_pattern.get('severity', 'medium'),
            new_pattern.get('severity', 'medium')
        )
        
        # Normalize to -1 to 1
        improvement = severity_change * 0.33  # Max change is 3 levels
        
        # Consider other factors
        if new_pattern.get('frequency', 0) < old_pattern.get('frequency', 0):
            improvement += 0.2
        
        if new_pattern.get('duration', 0) < old_pattern.get('duration', 0):
            improvement += 0.2
        
        return max(-1.0, min(1.0, improvement))
    
    def _update_evolution_chain(self, pattern_id: str, evolution_record: Dict) -> None:
        """Update the evolution chain for a pattern"""
        if pattern_id not in self.evolution_chains:
            self.evolution_chains[pattern_id] = []
        
        self.evolution_chains[pattern_id].append({
            'evolution_id': evolution_record['id'],
            'timestamp': evolution_record['timestamp'],
            'type': evolution_record['type'],
            'intervention': evolution_record.get('intervention'),
            'improvement_score': evolution_record.get('improvement_score', 0),
            'new_pattern': evolution_record.get('new_pattern')
        })
    
    def _find_pattern_chain(self, pattern_type: str) -> Optional[List[Dict]]:
        """Find the evolution chain for a pattern type"""
        for pattern_id, chain in self.evolution_chains.items():
            if chain and chain[0].get('new_pattern', {}).get('type') == pattern_type:
                return chain
        return None
    
    def _load_evolution_history(self) -> List[Dict]:
        """Load evolution history from disk"""
        if self.evolution_file.exists():
            try:
                with open(self.evolution_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load evolution history: {e}")
        return []
    
    def _save_evolution_history(self) -> None:
        """Save evolution history to disk"""
        try:
            with open(self.evolution_file, 'w') as f:
                json.dump(self.evolution_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save evolution history: {e}")
    
    def _load_evolution_chains(self) -> Dict[str, List]:
        """Load evolution chains from disk"""
        if self.chains_file.exists():
            try:
                with open(self.chains_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load evolution chains: {e}")
        return {}
    
    def _save_evolution_chains(self) -> None:
        """Save evolution chains to disk"""
        try:
            with open(self.chains_file, 'w') as f:
                json.dump(self.evolution_chains, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save evolution chains: {e}")