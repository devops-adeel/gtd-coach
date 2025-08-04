#!/usr/bin/env python3
"""
Graphiti Memory Integration for GTD Coach
Handles async communication with Graphiti MCP server for memory persistence
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Handle Docker vs local paths
def get_base_dir():
    if os.environ.get("IN_DOCKER"):
        return Path("/app")
    else:
        return Path.home() / "gtd-coach"


class GraphitiMemory:
    """Manages memory operations with Graphiti MCP server"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_group_id = f"gtd_review_{session_id}"
        self.pending_episodes: List[Dict[str, Any]] = []
        self.phase_start_times: Dict[str, datetime] = {}
        self.interaction_count = 0
        
    async def queue_episode(self, episode_data: Dict[str, Any]) -> None:
        """
        Queue an episode for batch processing
        
        Args:
            episode_data: Dictionary containing episode information
        """
        episode_data['session_id'] = self.session_id
        episode_data['group_id'] = self.session_group_id
        episode_data['timestamp'] = datetime.now().isoformat()
        self.pending_episodes.append(episode_data)
        logger.debug(f"Queued episode: {episode_data.get('type', 'unknown')}")
        
    async def add_interaction(self, role: str, content: str, phase: str, 
                            metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a coach-user interaction to memory
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            phase: Current phase name
            metrics: Optional metrics about the interaction
        """
        self.interaction_count += 1
        
        episode_data = {
            "type": "interaction",
            "phase": phase,
            "data": {
                "role": role,
                "content": content,
                "interaction_number": self.interaction_count,
                "metrics": metrics or {}
            }
        }
        
        await self.queue_episode(episode_data)
        
    async def add_phase_transition(self, phase_name: str, action: str, 
                                 duration_seconds: Optional[float] = None) -> None:
        """
        Record a phase transition event
        
        Args:
            phase_name: Name of the phase
            action: 'start' or 'end'
            duration_seconds: Duration if ending a phase
        """
        episode_data = {
            "type": "phase_transition",
            "phase": phase_name,
            "data": {
                "action": action,
                "duration_seconds": duration_seconds
            }
        }
        
        if action == "start":
            self.phase_start_times[phase_name] = datetime.now()
        
        await self.queue_episode(episode_data)
        
    async def add_behavior_pattern(self, pattern_type: str, phase: str,
                                 pattern_data: Dict[str, Any]) -> None:
        """
        Record an ADHD behavior pattern
        
        Args:
            pattern_type: Type of pattern (task_switch, focus_event, etc.)
            phase: Current phase
            pattern_data: Pattern-specific data
        """
        episode_data = {
            "type": "behavior_pattern",
            "phase": phase,
            "data": {
                "pattern_type": pattern_type,
                **pattern_data
            }
        }
        
        await self.queue_episode(episode_data)
        
    async def add_mindsweep_batch(self, items: List[str], phase_metrics: Dict[str, Any]) -> None:
        """
        Add a batch of mindsweep items with analysis
        
        Args:
            items: List of captured items
            phase_metrics: Metrics about the capture phase
        """
        episode_data = {
            "type": "mindsweep_capture",
            "phase": "MIND_SWEEP",
            "data": {
                "items": items,
                "item_count": len(items),
                "phase_metrics": phase_metrics
            }
        }
        
        await self.queue_episode(episode_data)
        
    async def flush_episodes(self) -> int:
        """
        Send all pending episodes to Graphiti
        
        Returns:
            Number of episodes sent
        """
        if not self.pending_episodes:
            return 0
            
        episodes_to_send = self.pending_episodes.copy()
        self.pending_episodes.clear()
        
        # Note: In actual implementation, this would use the MCP tools
        # For now, we'll save to a temporary file that can be processed
        temp_file = get_base_dir() / "data" / f"graphiti_batch_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(temp_file, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "group_id": self.session_group_id,
                    "episodes": episodes_to_send
                }, f, indent=2)
            
            logger.info(f"Flushed {len(episodes_to_send)} episodes to {temp_file.name}")
            
            # TODO: When MCP integration is ready, replace with:
            # for episode in episodes_to_send:
            #     await mcp_add_episode(
            #         name=f"{episode['type']}_{episode['timestamp']}",
            #         episode_body=json.dumps(episode['data']),
            #         source="json",
            #         source_description=f"GTD Review - {episode['phase']}",
            #         group_id=self.session_group_id
            #     )
            
            return len(episodes_to_send)
            
        except Exception as e:
            logger.error(f"Failed to flush episodes: {e}")
            # Re-queue episodes on failure
            self.pending_episodes = episodes_to_send + self.pending_episodes
            return 0
            
    async def create_session_summary(self, review_data: Dict[str, Any]) -> None:
        """
        Create a summary episode for the entire session
        
        Args:
            review_data: Complete review data including metrics
        """
        summary_data = {
            "type": "session_summary",
            "phase": "COMPLETE",
            "data": {
                "review_metrics": review_data,
                "total_interactions": self.interaction_count,
                "phases_completed": list(self.phase_start_times.keys())
            }
        }
        
        await self.queue_episode(summary_data)
        await self.flush_episodes()


class GraphitiRetriever:
    """Handles retrieval of data from Graphiti for analysis"""
    
    @staticmethod
    async def get_recent_sessions(days: int = 7) -> List[Dict[str, Any]]:
        """
        Retrieve recent review sessions
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of session data
        """
        # TODO: Implement using MCP search tools
        # For now, return empty list
        return []
        
    @staticmethod
    async def search_patterns(pattern_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Search for specific behavior patterns
        
        Args:
            pattern_type: Type of pattern to search for
            days: Number of days to look back
            
        Returns:
            List of pattern occurrences
        """
        # TODO: Implement using MCP search tools
        return []
        
    @staticmethod
    async def get_mindsweep_trends(days: int = 30) -> Dict[str, Any]:
        """
        Analyze mindsweep trends over time
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary of trend data
        """
        # TODO: Implement using MCP search tools
        return {
            "average_items": 0,
            "common_themes": [],
            "completion_times": []
        }