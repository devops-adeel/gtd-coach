#!/usr/bin/env python3
"""
Memory Enhancement Module for GTD Coach
Bridges lightweight pattern detection with Graphiti memory
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from pattern_detector import PatternDetector

logger = logging.getLogger(__name__)

class MemoryEnhancer:
    """
    Enhances GTD Coach with memory capabilities.
    Coordinates between lightweight pattern detection and Graphiti.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize memory enhancer
        
        Args:
            session_id: Current session identifier
        """
        self.session_id = session_id
        self.pattern_detector = PatternDetector()
        self.graphiti_memory = None  # Set by GTDCoach if available
        
    def set_graphiti_memory(self, graphiti_memory):
        """
        Connect to Graphiti memory instance
        
        Args:
            graphiti_memory: GraphitiMemory instance from GTDCoach
        """
        self.graphiti_memory = graphiti_memory
        
    async def get_startup_context(self) -> Optional[Dict[str, Any]]:
        """
        Get context for startup phase (zero-friction, instant)
        
        Returns:
            Pre-computed context with patterns and insights
        """
        try:
            # Load pre-computed context instantly
            context = self.pattern_detector.load_context()
            
            # If we have Graphiti, we could enhance with additional data
            # (but keep it fast - no blocking operations at startup)
            if self.graphiti_memory and context:
                # Could add user-specific enhancements here
                pass
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to load startup context: {e}")
            return None
    
    async def prepare_next_session_context(self, mindsweep_items: List[str]) -> Dict[str, Any]:
        """
        Prepare context for the next session (runs in background)
        
        Args:
            mindsweep_items: Items captured in current mindsweep
            
        Returns:
            Context dictionary to save for next session
        """
        try:
            # Find recurring patterns
            patterns = self.pattern_detector.find_recurring_patterns(weeks_back=4)
            
            # Generate insights from current session
            insights = self.pattern_detector.get_simple_insights(mindsweep_items)
            
            # Build context
            context = {
                'patterns': patterns,
                'last_session': self.session_id,
                'last_insights': insights,
                'timestamp': datetime.now().isoformat()
            }
            
            # If Graphiti is available, could add more sophisticated analysis
            if self.graphiti_memory:
                # Could query Graphiti for deeper patterns
                # But keep this lightweight to avoid delays
                pass
            
            # Save for next session
            self.pattern_detector.save_context(context)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to prepare next session context: {e}")
            return {}
    
    def format_startup_display(self, context: Dict[str, Any]) -> str:
        """
        Format context for display at startup
        
        Args:
            context: Context dictionary with patterns
            
        Returns:
            Formatted string for display
        """
        if not context or not context.get('patterns'):
            return ""
        
        lines = ["\n💭 On your mind lately:"]
        
        for pattern in context['patterns'][:3]:
            lines.append(f"   • {pattern['pattern']} (seen {pattern['weeks_seen']} weeks)")
        
        return "\n".join(lines)
    
    async def search_related_items(self, query: str) -> List[str]:
        """
        Search for related items from past sessions
        
        Args:
            query: Search query
            
        Returns:
            List of related items
        """
        related = []
        
        # Use Graphiti if available for sophisticated search
        if self.graphiti_memory:
            try:
                results = await self.graphiti_memory.search_with_context(query, num_results=5)
                # Extract relevant items from results
                for result in results:
                    if hasattr(result, 'content'):
                        related.append(result.content)
            except Exception as e:
                logger.warning(f"Graphiti search failed: {e}")
        
        # Fallback to simple pattern matching
        if not related:
            # Could implement simple file-based search here
            pass
        
        return related[:5]  # Limit to 5 items
    
    def get_focus_recommendations(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """
        Generate focus recommendations based on patterns
        
        Args:
            patterns: List of recurring patterns
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for pattern in patterns[:3]:
            if pattern['weeks_seen'] >= 3:
                recommendations.append(
                    f"'{pattern['pattern']}' has appeared for {pattern['weeks_seen']} weeks - "
                    f"consider scheduling dedicated time or delegating"
                )
        
        return recommendations


# Convenience functions for direct use

async def enhance_startup_with_memory(session_id: str) -> str:
    """
    Get memory-enhanced startup message
    
    Args:
        session_id: Current session ID
        
    Returns:
        Formatted startup context or empty string
    """
    enhancer = MemoryEnhancer(session_id)
    context = await enhancer.get_startup_context()
    return enhancer.format_startup_display(context) if context else ""

async def save_session_patterns(session_id: str, mindsweep_items: List[str]) -> None:
    """
    Save patterns from current session for next time
    
    Args:
        session_id: Current session ID
        mindsweep_items: Items from mindsweep
    """
    enhancer = MemoryEnhancer(session_id)
    await enhancer.prepare_next_session_context(mindsweep_items)