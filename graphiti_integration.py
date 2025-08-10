#!/usr/bin/env python3
"""
Graphiti Memory Integration for GTD Coach
Provides dual-mode operation: Real Graphiti + JSON backup
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from graphiti_client import GraphitiClient
    from graphiti_core.nodes import EpisodeType
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Graphiti not available, using JSON-only mode")

logger = logging.getLogger(__name__)

# Handle Docker vs local paths
def get_base_dir():
    if os.environ.get("IN_DOCKER"):
        return Path("/app")
    else:
        return Path.home() / "gtd-coach"


class GraphitiMemory:
    """Manages memory operations with Graphiti and/or JSON backup"""
    
    def __init__(self, session_id: str, enable_json_backup: bool = True):
        self.session_id = session_id
        self.session_group_id = f"gtd_review_{session_id}"
        self.pending_episodes: List[Dict[str, Any]] = []
        self.phase_start_times: Dict[str, datetime] = {}
        self.interaction_count = 0
        self.enable_json_backup = enable_json_backup
        self.graphiti_client = None
        self.current_phase = "UNKNOWN"
        self.user_node_uuid = None  # Store user context for centering searches
        
        # Cost-aware batching configuration
        self.batch_threshold = int(os.getenv('GRAPHITI_BATCH_SIZE', '5'))
        self.skip_trivial = os.getenv('GRAPHITI_SKIP_TRIVIAL', 'true').lower() == 'true'
        self.pending_graphiti_episodes: List[Dict[str, Any]] = []
        
        # Lightweight ADHD detection
        self.recent_interactions: List[Dict[str, Any]] = []
        self.context_switch_count = 0
        self.last_interaction_time = None
        self.rapid_switch_threshold = 3  # switches in 30 seconds
        self.intervention_callback = None  # Set by GTDCoach
        
        # Performance metrics tracking
        self.extraction_metrics: Dict[str, List[float]] = {
            "interaction": [],
            "mindsweep_capture": [],
            "session_summary": [],
            "timing_analysis": [],
            "other": []
        }
        self.entity_type_metrics: Dict[str, float] = {}  # Track avg time per entity type
        
    async def initialize(self):
        """Initialize Graphiti connection if available"""
        if GRAPHITI_AVAILABLE and os.getenv('GRAPHITI_ENABLED', 'true').lower() == 'true':
            try:
                client_instance = GraphitiClient()
                self.graphiti_client = await client_instance.initialize()
                logger.info("✅ Graphiti client initialized for session")
                
                # Create user node for this review session
                await self._create_user_node()
                
            except Exception as e:
                logger.warning(f"⚠️ Graphiti unavailable, using JSON only: {e}")
                self.graphiti_client = None
        else:
            logger.info("Running in JSON-only mode")
            self.graphiti_client = None
    
    async def _create_user_node(self):
        """Create a user node for this review session to center searches"""
        if not self.graphiti_client:
            return
        
        try:
            # Create episode for user session
            user_data = {
                "type": "user",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "description": f"GTD Review Session User {self.session_id}"
            }
            
            await self.graphiti_client.add_episode(
                name=f"user_session_{self.session_id}",
                episode_body=json.dumps(user_data),
                source=EpisodeType.json,
                source_description="User Session Creation",
                group_id=self.session_group_id,
                reference_time=datetime.now(timezone.utc)
            )
            
            # Search for the user node we just created
            # Note: In production, Graphiti should return the node UUID directly
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_EPISODE_MENTIONS
            search_result = await self.graphiti_client._search(
                f"user_session_{self.session_id}",
                NODE_HYBRID_SEARCH_EPISODE_MENTIONS
            )
            
            if search_result and search_result.nodes:
                self.user_node_uuid = search_result.nodes[0].uuid
                logger.info(f"✅ Created user node with UUID: {self.user_node_uuid}")
            else:
                logger.warning("Could not retrieve user node UUID")
                
        except Exception as e:
            logger.warning(f"Failed to create user node: {e}")
            # Continue without user context - not critical
        
    async def queue_episode(self, episode_data: Dict[str, Any]) -> None:
        """
        Queue an episode for batch processing and/or send to Graphiti
        
        Args:
            episode_data: Dictionary containing episode information
        """
        episode_data['session_id'] = self.session_id
        episode_data['group_id'] = self.session_group_id
        episode_data['timestamp'] = datetime.now().isoformat()
        
        # Always queue for JSON backup if enabled
        if self.enable_json_backup:
            self.pending_episodes.append(episode_data)
        
        # Send to Graphiti if available
        if self.graphiti_client:
            await self._send_to_graphiti(episode_data)
        
        logger.debug(f"Processed episode: {episode_data.get('type', 'unknown')}")
        
    async def add_interaction(self, role: str, content: str, phase: str, 
                            metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a coach-user interaction to memory with lightweight ADHD detection
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            phase: Current phase name
            metrics: Optional metrics about the interaction
        """
        self.interaction_count += 1
        current_time = datetime.now()
        
        # Lightweight ADHD pattern detection (only for user messages)
        if role == 'user':
            # Check for rapid context switching
            if await self._detect_rapid_switching(content, current_time):
                await self._trigger_gentle_intervention("Let's take a breath and refocus on one thing at a time.")
            
            # Update interaction tracking
            self.recent_interactions.append({
                'time': current_time,
                'content': content,
                'phase': phase
            })
            
            # Keep only last 10 interactions for memory efficiency
            if len(self.recent_interactions) > 10:
                self.recent_interactions.pop(0)
        
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
            self.current_phase = phase_name
        
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
        
    def _should_send_immediately(self, episode_data: Dict[str, Any]) -> bool:
        """
        Determine if an episode should be sent immediately to Graphiti
        
        Args:
            episode_data: Episode data to evaluate
            
        Returns:
            True if should send immediately, False if can batch
        """
        episode_type = episode_data.get('type', 'unknown')
        
        # Always send immediately for critical episodes
        if episode_type in ['phase_transition', 'session_summary', 'user']:
            return True
        
        # Skip trivial interactions if configured
        if self.skip_trivial and episode_type == 'interaction':
            content = episode_data.get('data', {}).get('content', '').lower()
            trivial_responses = ['ok', 'okay', 'got it', 'yes', 'no', 'sure', 'thanks', 'thank you']
            if any(content.strip() == trivial for trivial in trivial_responses):
                logger.debug(f"Skipping trivial interaction: {content[:20]}")
                return False
        
        # Batch mind sweep items
        if episode_type == 'mindsweep_capture':
            return False
        
        # Send other interactions immediately for now
        return True
    
    async def _send_to_graphiti(self, episode_data: Dict[str, Any]) -> None:
        """
        Send episode to Graphiti with smart batching
        
        Args:
            episode_data: Episode data to send
        """
        if not self.graphiti_client:
            return
        
        # Check if should send immediately or batch
        if self._should_send_immediately(episode_data):
            await self._send_single_episode(episode_data)
        else:
            # Add to batch
            self.pending_graphiti_episodes.append(episode_data)
            
            # Check if batch threshold reached
            if len(self.pending_graphiti_episodes) >= self.batch_threshold:
                await self._flush_graphiti_batch()
    
    async def _send_single_episode(self, episode_data: Dict[str, Any]) -> None:
        """Send a single episode to Graphiti with monitoring, custom entities, and retry logic"""
        if not self.graphiti_client:
            return
        
        import time
        start_time = time.perf_counter()
        success = False
        retry_count = 0
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        # Import entity configuration
        from gtd_entity_config import (
            get_entity_config_for_episode,
            estimate_extraction_cost,
            log_entity_extraction
        )
        
        # Determine source type based on episode type
        episode_type = episode_data.get('type', 'unknown')
        if episode_type == 'interaction':
            source = EpisodeType.message
        elif episode_type in ['timing_analysis', 'session_summary', 'mindsweep_capture', 'user']:
            source = EpisodeType.json
        else:
            source = EpisodeType.text
        
        # Get custom entity configuration for this episode type
        entity_config = get_entity_config_for_episode(episode_type)
        
        # Log decision
        log_entity_extraction(episode_type, entity_config is not None)
        
        # Prepare add_episode parameters
        episode_params = {
            "name": f"{episode_type}_{self.session_id}_{episode_data['timestamp']}",
            "episode_body": json.dumps(episode_data['data']),
            "source": source,
            "source_description": f"GTD Review - {episode_data.get('phase', 'Unknown')}",
            "group_id": self.session_group_id,
            "reference_time": datetime.fromisoformat(episode_data['timestamp']).replace(tzinfo=timezone.utc)
        }
        
        # Add custom entity parameters if applicable
        if entity_config:
            episode_params.update(entity_config)
            logger.debug(f"Using custom GTD entities for {episode_type}")
        
        # Retry loop with exponential backoff
        last_error = None
        while retry_count <= max_retries:
            try:
                # Create episode in Graphiti
                await self.graphiti_client.add_episode(**episode_params)
                
                success = True
                if retry_count > 0:
                    logger.info(f"✅ Successfully sent episode to Graphiti after {retry_count} retries: {episode_type}")
                else:
                    logger.debug(f"Sent episode to Graphiti: {episode_type}")
                
                # Track extraction time for this episode type
                extraction_time = time.perf_counter() - start_time
                metric_key = episode_type if episode_type in self.extraction_metrics else "other"
                self.extraction_metrics[metric_key].append(extraction_time)
                
                # Log if extraction was slow
                if extraction_time > 10.0:
                    logger.warning(f"Slow entity extraction for {episode_type}: {extraction_time:.2f}s (retries: {retry_count})")
                elif extraction_time > 5.0:
                    logger.info(f"Entity extraction for {episode_type}: {extraction_time:.2f}s (retries: {retry_count})")
                
                break  # Success, exit retry loop
                
            except Exception as e:
                last_error = e
                
                # Log error with context
                error_context = {
                    "episode_type": episode_type,
                    "phase": episode_data.get('phase', 'Unknown'),
                    "retry_count": retry_count,
                    "data_size": len(json.dumps(episode_data.get('data', {}))),
                    "has_custom_entities": entity_config is not None
                }
                
                if retry_count < max_retries:
                    delay = retry_delays[retry_count]
                    logger.warning(
                        f"Failed to send episode to Graphiti (attempt {retry_count + 1}/{max_retries + 1}): {e}\n"
                        f"Context: {error_context}\n"
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                    retry_count += 1
                else:
                    # Final failure - log detailed error
                    logger.error(
                        f"❌ Failed to send episode to Graphiti after {max_retries + 1} attempts: {e}\n"
                        f"Context: {error_context}\n"
                        f"Episode will be preserved in JSON backup"
                    )
                    # Continue anyway - JSON backup will preserve the data
                    break
        
        # Track metrics if Langfuse is available (after retry loop completes)
        latency = time.perf_counter() - start_time
        try:
            from langfuse_tracker import score_graphiti_operation
            from gtd_entity_config import estimate_extraction_cost
            
            # Estimate cost based on whether custom entities were used
            episode_body_length = len(json.dumps(episode_data.get('data', {})))
            cost_estimate = estimate_extraction_cost(
                episode_data.get('type', 'unknown'),
                episode_body_length
            )
            score_graphiti_operation(
                operation="add_episode",
                success=success,
                latency=latency,
                episode_count=1,
                cost_estimate=cost_estimate
            )
        except ImportError:
            pass  # Langfuse not configured
    
    async def _flush_graphiti_batch(self) -> None:
        """Flush pending Graphiti episodes as a batch"""
        if not self.pending_graphiti_episodes:
            return
        
        episodes_to_send = self.pending_graphiti_episodes.copy()
        self.pending_graphiti_episodes.clear()
        
        # Combine episodes into a single batch episode
        batch_data = {
            "type": "batch",
            "episodes": episodes_to_send,
            "count": len(episodes_to_send)
        }
        
        batch_episode = {
            "type": "episode_batch",
            "phase": self.current_phase,
            "data": batch_data,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._send_single_episode(batch_episode)
        logger.info(f"Flushed {len(episodes_to_send)} episodes to Graphiti as batch")
    
    async def flush_episodes(self) -> int:
        """
        Flush pending episodes to JSON backup file and Graphiti batches
        
        Returns:
            Number of episodes flushed
        """
        # Flush any pending Graphiti batches first
        if self.graphiti_client:
            await self._flush_graphiti_batch()
        
        if not self.enable_json_backup or not self.pending_episodes:
            return 0
            
        episodes_to_save = self.pending_episodes.copy()
        self.pending_episodes.clear()
        
        # Save to JSON backup file
        temp_file = get_base_dir() / "data" / f"graphiti_batch_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(temp_file, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "group_id": self.session_group_id,
                    "episodes": episodes_to_save
                }, f, indent=2)
            
            logger.info(f"Flushed {len(episodes_to_save)} episodes to JSON backup: {temp_file.name}")
            return len(episodes_to_save)
            
        except Exception as e:
            logger.error(f"Failed to flush episodes to JSON: {e}")
            # Re-queue episodes on failure
            self.pending_episodes = episodes_to_save + self.pending_episodes
            return 0
            
    async def add_timing_analysis(self, timing_data: Dict[str, Any], 
                                 adhd_analysis: Dict[str, Any]) -> None:
        """
        Add timing app analysis to memory
        
        Args:
            timing_data: Analysis from TimingAPI.analyze_timing_patterns_async()
            adhd_analysis: ADHD pattern analysis from timing data
        """
        episode_data = {
            "type": "timing_analysis",
            "phase": self.current_phase,
            "data": {
                "data_type": timing_data.get('data_type'),
                "focus_metrics": timing_data.get('focus_metrics'),
                "switch_summary": {
                    "total_switches": timing_data.get('switch_analysis', {}).get('total_switches', 0),
                    "switches_per_hour": timing_data.get('switch_analysis', {}).get('switches_per_hour', 0),
                    "top_patterns": timing_data.get('switch_analysis', {}).get('switch_patterns', [])[:3]
                },
                "adhd_indicators": adhd_analysis.get('adhd_indicators', []),
                "focus_profile": adhd_analysis.get('focus_profile', 'Unknown')
            }
        }
        
        await self.queue_episode(episode_data)
        
        # Also record significant patterns as behavior patterns
        if adhd_analysis.get('patterns_detected'):
            for indicator in adhd_analysis.get('adhd_indicators', []):
                if indicator['severity'] in ['high', 'medium']:
                    await self.add_behavior_pattern(
                        pattern_type=f"timing_{indicator['type']}",
                        phase=self.current_phase,
                        pattern_data={
                            'severity': indicator['severity'],
                            'value': indicator['value'],
                            'message': indicator['message']
                        }
                    )
    
    async def add_correlation_insights(self, correlation_data: Dict[str, Any]) -> None:
        """
        Add correlation insights between timing and mindsweep
        
        Args:
            correlation_data: Results from correlate_timing_with_mindsweep
        """
        episode_data = {
            "type": "correlation_insight",
            "phase": self.current_phase,
            "data": {
                "correlations": correlation_data.get('correlations', []),
                "overall_pattern": correlation_data.get('overall_pattern', 'Unknown')
            }
        }
        
        await self.queue_episode(episode_data)
    
    async def _detect_rapid_switching(self, content: str, current_time: datetime) -> bool:
        """
        Detect rapid context switching pattern
        
        Args:
            content: User's message content
            current_time: Current timestamp
            
        Returns:
            True if rapid switching detected
        """
        if self.last_interaction_time:
            time_diff = (current_time - self.last_interaction_time).total_seconds()
            
            # Count as context switch if topic change within 30 seconds
            if time_diff < 30:
                # Simple heuristic: significant content difference indicates context switch
                if len(self.recent_interactions) > 0:
                    last_content = self.recent_interactions[-1].get('content', '')
                    
                    # Check for topic change (simple word overlap check)
                    last_words = set(last_content.lower().split())
                    current_words = set(content.lower().split())
                    overlap = len(last_words & current_words) / max(len(last_words), len(current_words), 1)
                    
                    if overlap < 0.3:  # Less than 30% word overlap
                        self.context_switch_count += 1
                        
                        # Check if exceeded threshold
                        if self.context_switch_count >= self.rapid_switch_threshold:
                            logger.info(f"Rapid context switching detected: {self.context_switch_count} switches")
                            self.context_switch_count = 0  # Reset counter
                            return True
            else:
                # Reset counter if more than 30 seconds passed
                self.context_switch_count = 0
        
        self.last_interaction_time = current_time
        return False
    
    async def _trigger_gentle_intervention(self, message: str) -> None:
        """
        Trigger a gentle intervention for ADHD support
        
        Args:
            message: Intervention message to display
        """
        # Log the intervention
        logger.info(f"ADHD intervention triggered: {message}")
        
        # Record as behavior pattern
        await self.add_behavior_pattern(
            pattern_type="rapid_switching",
            phase=self.current_phase,
            pattern_data={
                'intervention': message,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Call the intervention callback if set
        if self.intervention_callback:
            try:
                await self.intervention_callback(message)
            except Exception as e:
                logger.error(f"Failed to trigger intervention callback: {e}")
    
    def set_intervention_callback(self, callback) -> None:
        """
        Set callback function for ADHD interventions
        
        Args:
            callback: Async function to call with intervention message
        """
        self.intervention_callback = callback
    
    async def search_with_context(self, query: str, num_results: int = 10) -> List[Any]:
        """
        Search Graphiti with user context centering
        
        Args:
            query: Search query
            num_results: Maximum number of results
            
        Returns:
            List of search results
        """
        if not self.graphiti_client:
            return []
        
        try:
            # Use user node UUID for context centering if available
            if self.user_node_uuid:
                results = await self.graphiti_client.search(
                    query=query,
                    center_node_uuid=self.user_node_uuid,
                    num_results=num_results
                )
                logger.debug(f"Context-centered search for '{query}' returned {len(results)} results")
            else:
                # Fallback to regular search
                results = await self.graphiti_client.search(
                    query=query,
                    num_results=num_results
                )
                logger.debug(f"Regular search for '{query}' returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def create_session_summary(self, review_data: Dict[str, Any],
                                   timing_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Create a summary episode for the entire session
        
        Args:
            review_data: Complete review data including metrics
            timing_data: Optional timing analysis data
        """
        # Report performance metrics before creating summary
        self._report_performance_metrics()
        
        summary_data = {
            "type": "session_summary",
            "phase": "COMPLETE",
            "data": {
                "review_metrics": review_data,
                "total_interactions": self.interaction_count,
                "phases_completed": list(self.phase_start_times.keys())
            }
        }
        
        # Include timing summary if available
        if timing_data and timing_data.get('focus_metrics'):
            summary_data["data"]["timing_summary"] = {
                "focus_score": timing_data['focus_metrics'].get('focus_score'),
                "switches_per_hour": timing_data['focus_metrics'].get('switches_per_hour'),
                "focus_periods": timing_data['focus_metrics'].get('focus_periods_count'),
                "interpretation": timing_data['focus_metrics'].get('interpretation')
            }
        
        await self.queue_episode(summary_data)
        await self.flush_episodes()
    
    def _report_performance_metrics(self) -> None:
        """Report performance metrics for entity extraction"""
        logger.info("=" * 60)
        logger.info("ENTITY EXTRACTION PERFORMANCE METRICS")
        logger.info("=" * 60)
        
        for episode_type, times in self.extraction_metrics.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                logger.info(
                    f"{episode_type:20s}: "
                    f"avg={avg_time:.2f}s, "
                    f"min={min_time:.2f}s, "
                    f"max={max_time:.2f}s, "
                    f"count={len(times)}"
                )
        
        # Calculate total extraction time
        all_times = []
        for times in self.extraction_metrics.values():
            all_times.extend(times)
        
        if all_times:
            total_time = sum(all_times)
            avg_time = total_time / len(all_times)
            logger.info("-" * 60)
            logger.info(f"Total extraction time: {total_time:.2f}s")
            logger.info(f"Average per episode: {avg_time:.2f}s")
            logger.info(f"Total episodes: {len(all_times)}")
        
        logger.info("=" * 60)


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