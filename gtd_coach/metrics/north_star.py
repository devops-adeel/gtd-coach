#!/usr/bin/env python3
"""
North Star Metrics for GTD Coach
Tracks the three metrics that matter most for ADHD user success
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class NorthStarMetrics:
    """Track and calculate the three North Star metrics for GTD Coach"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_start_time = datetime.now()
        self.first_capture_time: Optional[datetime] = None
        self.shown_memories: Set[str] = set()
        self.used_memories: Set[str] = set()
        self.planned_tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        
        # Track metrics as they're calculated
        self.metrics = {
            "memory_relevance_score": 0.0,
            "time_to_first_capture": None,
            "task_followthrough_rate": 0.0,
            "pre_capture_hesitation": 0,
            "context_switches_per_minute": 0.0,
            "hyperfocus_periods": 0,
            "scatter_periods": 0
        }
    
    def calculate_memory_relevance(self, retrieved_items: List[Any], 
                                  used_items: List[Any]) -> float:
        """
        Calculate relevance score for retrieved memories
        
        Args:
            retrieved_items: List of memory items shown to user
            used_items: List of items user actually referenced/used
            
        Returns:
            Score from 0.0 to 1.0 indicating relevance
        """
        if not retrieved_items:
            return 0.0
        
        # Track shown memories
        for item in retrieved_items:
            if hasattr(item, 'id'):
                self.shown_memories.add(str(item.id))
            elif isinstance(item, dict) and 'id' in item:
                self.shown_memories.add(str(item['id']))
        
        # Track used memories
        for item in used_items:
            if hasattr(item, 'id'):
                self.used_memories.add(str(item.id))
            elif isinstance(item, dict) and 'id' in item:
                self.used_memories.add(str(item['id']))
        
        # Calculate relevance as ratio of used to shown
        if len(self.shown_memories) == 0:
            relevance = 0.0
        else:
            relevance = len(self.used_memories.intersection(self.shown_memories)) / len(self.shown_memories)
        
        self.metrics["memory_relevance_score"] = relevance
        logger.info(f"Memory relevance: {relevance:.2f} ({len(self.used_memories)}/{len(self.shown_memories)} used)")
        
        return relevance
    
    def mark_memory_used(self, memory_id: str) -> None:
        """
        Mark a specific memory as having been used/referenced
        
        Args:
            memory_id: ID of the memory that was used
        """
        self.used_memories.add(str(memory_id))
        
        # Recalculate relevance
        if self.shown_memories:
            self.metrics["memory_relevance_score"] = len(
                self.used_memories.intersection(self.shown_memories)
            ) / len(self.shown_memories)
    
    def track_task_followthrough(self, planned_tasks: List[Dict[str, Any]], 
                                completed_tasks: List[Dict[str, Any]]) -> float:
        """
        Compare planned tasks from last session with completed tasks
        
        Args:
            planned_tasks: Tasks planned in previous session
            completed_tasks: Tasks actually completed since then
            
        Returns:
            Follow-through rate from 0.0 to 1.0
        """
        self.planned_tasks = planned_tasks
        self.completed_tasks = completed_tasks
        
        if not planned_tasks:
            return 1.0  # No tasks planned = 100% completion
        
        # Simple matching: count how many planned tasks appear in completed
        # This could be enhanced with fuzzy matching or semantic similarity
        planned_set = {self._normalize_task(t) for t in planned_tasks}
        completed_set = {self._normalize_task(t) for t in completed_tasks}
        
        matches = planned_set.intersection(completed_set)
        followthrough = len(matches) / len(planned_set)
        
        self.metrics["task_followthrough_rate"] = followthrough
        logger.info(f"Task follow-through: {followthrough:.2f} ({len(matches)}/{len(planned_set)} completed)")
        
        return followthrough
    
    def _normalize_task(self, task: Dict[str, Any]) -> str:
        """Normalize task for comparison"""
        if isinstance(task, dict):
            # Extract task description or content
            task_text = task.get('task', task.get('content', task.get('description', '')))
        else:
            task_text = str(task)
        
        # Basic normalization
        return task_text.lower().strip()
    
    def measure_time_to_insight(self, first_capture_time: Optional[datetime] = None) -> Optional[int]:
        """
        Measure seconds from session start to first meaningful capture
        
        Args:
            first_capture_time: Time of first capture (uses stored time if not provided)
            
        Returns:
            Seconds to first capture, or None if not captured yet
        """
        if first_capture_time:
            self.first_capture_time = first_capture_time
        elif not self.first_capture_time:
            # If no time provided and none stored, use current time
            self.first_capture_time = datetime.now()
        
        if not self.first_capture_time:
            return None
        
        time_to_insight = int((self.first_capture_time - self.session_start_time).total_seconds())
        # Ensure it's at least 1 second if called immediately after init
        if time_to_insight <= 0:
            time_to_insight = 1
        
        self.metrics["time_to_first_capture"] = time_to_insight
        
        logger.info(f"Time to first capture: {time_to_insight} seconds")
        return time_to_insight
    
    def track_pre_capture_hesitation(self, hesitation_seconds: int) -> None:
        """
        Track hesitation time before first input
        
        Args:
            hesitation_seconds: Seconds of hesitation/silence before first input
        """
        self.metrics["pre_capture_hesitation"] = hesitation_seconds
        logger.debug(f"Pre-capture hesitation: {hesitation_seconds} seconds")
    
    def update_adhd_metrics(self, context_switches: int, duration_minutes: float,
                           hyperfocus_periods: int = 0, scatter_periods: int = 0) -> None:
        """
        Update ADHD-specific behavioral metrics
        
        Args:
            context_switches: Number of context switches detected
            duration_minutes: Duration of phase/session in minutes
            hyperfocus_periods: Number of hyperfocus periods detected
            scatter_periods: Number of scatter periods detected
        """
        if duration_minutes > 0:
            self.metrics["context_switches_per_minute"] = context_switches / duration_minutes
        
        self.metrics["hyperfocus_periods"] = hyperfocus_periods
        self.metrics["scatter_periods"] = scatter_periods
        
        logger.debug(f"ADHD metrics updated: {context_switches} switches in {duration_minutes:.1f} min")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all current metric values
        
        Returns:
            Dictionary of all metric values
        """
        return self.metrics.copy()
    
    def save_metrics(self, data_dir: Optional[Path] = None) -> None:
        """
        Save metrics to JSON file for later analysis
        
        Args:
            data_dir: Directory to save metrics (defaults to ~/gtd-coach/data)
        """
        if not data_dir:
            data_dir = Path.home() / "gtd-coach" / "data"
        
        data_dir.mkdir(parents=True, exist_ok=True)
        
        metrics_file = data_dir / f"north_star_metrics_{self.session_id}.json"
        
        try:
            with open(metrics_file, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "session_start": self.session_start_time.isoformat(),
                    "metrics": self.metrics,
                    "details": {
                        "shown_memories": list(self.shown_memories),
                        "used_memories": list(self.used_memories),
                        "planned_tasks": self.planned_tasks,
                        "completed_tasks": self.completed_tasks
                    }
                }, f, indent=2)
            
            logger.info(f"North Star metrics saved to {metrics_file.name}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    @classmethod
    def load_previous_metrics(cls, session_id: str, data_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Load metrics from a previous session
        
        Args:
            session_id: Session ID to load
            data_dir: Directory containing metrics files
            
        Returns:
            Metrics dictionary or None if not found
        """
        if not data_dir:
            data_dir = Path.home() / "gtd-coach" / "data"
        
        metrics_file = data_dir / f"north_star_metrics_{session_id}.json"
        
        if not metrics_file.exists():
            return None
        
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Failed to load metrics from {metrics_file}: {e}")
            return None
    
    def compare_with_previous(self, previous_metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Compare current metrics with previous session
        
        Args:
            previous_metrics: Metrics from previous session
            
        Returns:
            Dictionary of metric changes (positive = improvement)
        """
        changes = {}
        
        prev = previous_metrics.get('metrics', {})
        curr = self.metrics
        
        # Memory relevance (higher is better)
        if 'memory_relevance_score' in prev and curr['memory_relevance_score'] is not None:
            changes['memory_relevance_change'] = curr['memory_relevance_score'] - prev['memory_relevance_score']
        
        # Time to insight (lower is better, so negate)
        if 'time_to_first_capture' in prev and curr['time_to_first_capture'] is not None:
            changes['time_to_insight_change'] = prev['time_to_first_capture'] - curr['time_to_first_capture']
        
        # Task follow-through (higher is better)
        if 'task_followthrough_rate' in prev and curr['task_followthrough_rate'] is not None:
            changes['followthrough_change'] = curr['task_followthrough_rate'] - prev['task_followthrough_rate']
        
        # Context switches (lower is better, so negate)
        if 'context_switches_per_minute' in prev:
            changes['focus_improvement'] = prev['context_switches_per_minute'] - curr['context_switches_per_minute']
        
        return changes