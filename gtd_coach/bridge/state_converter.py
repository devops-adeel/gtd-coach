#!/usr/bin/env python3
"""
State converter for bidirectional conversion between legacy and agent state formats.
Ensures compatibility during incremental migration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import both state formats
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


class StateBridge:
    """
    Bidirectional converter between legacy review_data dict and AgentState.
    Maintains data integrity during incremental migration.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def legacy_to_agent(self, review_data: Dict[str, Any]) -> AgentState:
        """
        Convert legacy review_data dictionary to AgentState format.
        
        Args:
            review_data: Legacy dictionary with review data
            
        Returns:
            AgentState compatible with LangGraph workflow
        """
        try:
            # Initialize base state
            agent_state = AgentState(
                # Core identification
                session_id=review_data.get('session_id', datetime.now().strftime("%Y%m%d_%H%M%S")),
                user_id=review_data.get('user_id', 'default_user'),
                workflow_type='weekly_review',
                
                # Timing
                started_at=review_data.get('started_at', datetime.now().isoformat()),
                ended_at=review_data.get('ended_at'),
                
                # Phase tracking
                current_phase=self._map_phase(review_data.get('current_phase', 'STARTUP')),
                completed_phases=review_data.get('completed_phases', []),
                phase_timings=review_data.get('phase_timings', {}),
                
                # Messages - convert from message history
                messages=self._convert_messages(review_data.get('messages', [])),
                
                # GTD data
                mind_sweep_items=review_data.get('mindsweep', []),
                projects=self._convert_projects(review_data.get('projects', [])),
                priorities=self._convert_priorities(review_data.get('priorities', {})),
                
                # Integrations
                timing_data=review_data.get('timing_data', {}),
                graphiti_batch_id=review_data.get('graphiti_batch_id'),
                
                # Memory and patterns
                recurring_patterns=review_data.get('recurring_patterns', []),
                adhd_patterns=review_data.get('adhd_patterns', {}),
                
                # User state (for adaptive behavior)
                user_state={
                    'energy_level': review_data.get('user_energy', 'normal'),
                    'engagement': review_data.get('user_engagement', 'engaged'),
                    'confusion_level': 0,
                    'stress_indicators': []
                },
                
                # Experiments
                experiment_config=review_data.get('experiment_config', {}),
                
                # Metrics
                metrics=review_data.get('metrics', {}),
                
                # Error handling
                errors=[],
                warnings=[]
            )
            
            # Validate converted state
            if not self._validate_agent_state(agent_state):
                logger.warning("Converted state failed validation, using defaults for missing fields")
            
            return agent_state
            
        except Exception as e:
            logger.error(f"Failed to convert legacy to agent state: {e}")
            # Return minimal valid state on error
            return self._create_minimal_agent_state(review_data)
    
    def agent_to_legacy(self, state: AgentState) -> Dict[str, Any]:
        """
        Convert AgentState back to legacy review_data format.
        Ensures backward compatibility for legacy components.
        
        Args:
            state: AgentState from LangGraph workflow
            
        Returns:
            Legacy review_data dictionary
        """
        try:
            review_data = {
                # Core fields
                'session_id': state.get('session_id'),
                'user_id': state.get('user_id'),
                'started_at': state.get('started_at'),
                'ended_at': state.get('ended_at'),
                
                # Phase info
                'current_phase': self._unmap_phase(state.get('current_phase')),
                'completed_phases': state.get('completed_phases', []),
                'phase_timings': state.get('phase_timings', {}),
                
                # GTD data
                'mindsweep': state.get('mind_sweep_items', []),
                'projects': self._unconvert_projects(state.get('projects', [])),
                'priorities': self._unconvert_priorities(state.get('priorities', {})),
                
                # Messages (legacy format)
                'messages': self._unconvert_messages(state.get('messages', [])),
                
                # Integrations
                'timing_data': state.get('timing_data', {}),
                'graphiti_batch_id': state.get('graphiti_batch_id'),
                
                # Patterns
                'recurring_patterns': state.get('recurring_patterns', []),
                'adhd_patterns': state.get('adhd_patterns', {}),
                
                # User state (simplified)
                'user_energy': state.get('user_state', {}).get('energy_level', 'normal'),
                'user_engagement': state.get('user_state', {}).get('engagement', 'engaged'),
                
                # Experiments
                'experiment_config': state.get('experiment_config', {}),
                
                # Metrics
                'metrics': state.get('metrics', {}),
                
                # Additional legacy fields
                'total_time': self._calculate_total_time(state),
                'phase_durations': self._calculate_phase_durations(state)
            }
            
            return review_data
            
        except Exception as e:
            logger.error(f"Failed to convert agent to legacy state: {e}")
            return {}
    
    def _map_phase(self, legacy_phase: str) -> str:
        """Map legacy phase names to agent phase names"""
        phase_mapping = {
            'STARTUP': 'startup',
            'MIND_SWEEP': 'mind_sweep',
            'PROJECT_REVIEW': 'project_review', 
            'PRIORITIZATION': 'prioritization',
            'WRAP_UP': 'wrapup',
            'WRAP-UP': 'wrapup',
            'ABORTED': 'aborted'
        }
        return phase_mapping.get(legacy_phase, legacy_phase.lower())
    
    def _unmap_phase(self, agent_phase: str) -> str:
        """Map agent phase names back to legacy format"""
        phase_mapping = {
            'startup': 'STARTUP',
            'mind_sweep': 'MIND_SWEEP',
            'project_review': 'PROJECT_REVIEW',
            'prioritization': 'PRIORITIZATION',
            'wrapup': 'WRAP_UP',
            'aborted': 'ABORTED'
        }
        return phase_mapping.get(agent_phase, agent_phase.upper())
    
    def _convert_messages(self, legacy_messages: List) -> List:
        """Convert legacy message format to LangChain message objects"""
        converted = []
        
        for msg in legacy_messages:
            if isinstance(msg, dict):
                role = msg.get('role', 'human')
                content = msg.get('content', '')
                
                if role == 'system':
                    converted.append(SystemMessage(content=content))
                elif role == 'assistant' or role == 'ai':
                    converted.append(AIMessage(content=content))
                else:
                    converted.append(HumanMessage(content=content))
            elif isinstance(msg, str):
                # Assume string messages are from user
                converted.append(HumanMessage(content=msg))
            else:
                # Already a message object
                converted.append(msg)
        
        return converted
    
    def _unconvert_messages(self, agent_messages: List) -> List[Dict]:
        """Convert LangChain messages back to legacy format"""
        legacy = []
        
        for msg in agent_messages:
            if hasattr(msg, 'content'):
                if isinstance(msg, SystemMessage):
                    legacy.append({'role': 'system', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    legacy.append({'role': 'assistant', 'content': msg.content})
                elif isinstance(msg, HumanMessage):
                    legacy.append({'role': 'user', 'content': msg.content})
                else:
                    legacy.append({'role': 'unknown', 'content': str(msg)})
            else:
                legacy.append({'role': 'unknown', 'content': str(msg)})
        
        return legacy
    
    def _convert_projects(self, legacy_projects: List) -> List[Dict]:
        """Convert legacy project format to agent format"""
        return [
            {
                'name': p if isinstance(p, str) else p.get('name', 'Unknown'),
                'status': p.get('status', 'active') if isinstance(p, dict) else 'active',
                'next_action': p.get('next_action') if isinstance(p, dict) else None,
                'area_of_focus': p.get('area_of_focus') if isinstance(p, dict) else None
            }
            for p in legacy_projects
        ]
    
    def _unconvert_projects(self, agent_projects: List[Dict]) -> List:
        """Convert agent projects back to legacy format"""
        # Legacy sometimes uses simple strings, sometimes dicts
        return agent_projects  # Keep as dicts for consistency
    
    def _convert_priorities(self, legacy_priorities: Dict) -> Dict:
        """Convert legacy priority format to agent format"""
        if not legacy_priorities:
            return {'A': [], 'B': [], 'C': []}
        
        # Ensure all priority levels exist
        converted = {'A': [], 'B': [], 'C': []}
        for level in ['A', 'B', 'C']:
            if level in legacy_priorities:
                items = legacy_priorities[level]
                if isinstance(items, list):
                    converted[level] = items
                else:
                    converted[level] = [items]
        
        return converted
    
    def _unconvert_priorities(self, agent_priorities: Dict) -> Dict:
        """Convert agent priorities back to legacy format"""
        return agent_priorities  # Format is the same
    
    def _validate_agent_state(self, state: AgentState) -> bool:
        """Validate that converted state has all required fields"""
        required_fields = [
            'session_id', 'user_id', 'workflow_type',
            'current_phase', 'messages'
        ]
        
        for field in required_fields:
            if field not in state or state[field] is None:
                logger.warning(f"Missing required field in agent state: {field}")
                return False
        
        return True
    
    def _create_minimal_agent_state(self, review_data: Dict) -> AgentState:
        """Create minimal valid AgentState when conversion fails"""
        return AgentState(
            session_id=review_data.get('session_id', datetime.now().strftime("%Y%m%d_%H%M%S")),
            user_id=review_data.get('user_id', 'default_user'),
            workflow_type='weekly_review',
            started_at=datetime.now().isoformat(),
            current_phase='startup',
            completed_phases=[],
            messages=[],
            mind_sweep_items=[],
            projects=[],
            priorities={'A': [], 'B': [], 'C': []},
            errors=[],
            warnings=["State conversion failed, using minimal state"]
        )
    
    def _calculate_total_time(self, state: AgentState) -> float:
        """Calculate total review time from state"""
        if state.get('started_at') and state.get('ended_at'):
            try:
                start = datetime.fromisoformat(state['started_at'])
                end = datetime.fromisoformat(state['ended_at'])
                return (end - start).total_seconds() / 60  # Return minutes
            except:
                pass
        return 0.0
    
    def _calculate_phase_durations(self, state: AgentState) -> Dict[str, float]:
        """Calculate duration of each phase"""
        timings = state.get('phase_timings', {})
        durations = {}
        
        for phase, timing in timings.items():
            if isinstance(timing, dict) and 'start' in timing and 'end' in timing:
                try:
                    start = datetime.fromisoformat(timing['start'])
                    end = datetime.fromisoformat(timing['end'])
                    durations[phase] = (end - start).total_seconds() / 60
                except:
                    durations[phase] = 0.0
            elif isinstance(timing, (int, float)):
                durations[phase] = timing
        
        return durations


def test_state_bridge():
    """Test the state bridge with sample data"""
    bridge = StateBridge()
    
    # Test legacy to agent conversion
    legacy_data = {
        'session_id': '20250108_100000',
        'user_id': 'test_user',
        'current_phase': 'MIND_SWEEP',
        'mindsweep': ['Task 1', 'Task 2'],
        'priorities': {
            'A': ['High priority task'],
            'B': ['Medium priority'],
            'C': []
        },
        'messages': [
            {'role': 'system', 'content': 'Welcome'},
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there'}
        ]
    }
    
    agent_state = bridge.legacy_to_agent(legacy_data)
    print(f"Converted to agent state: {agent_state.get('session_id')}")
    
    # Test agent to legacy conversion
    legacy_restored = bridge.agent_to_legacy(agent_state)
    print(f"Converted back to legacy: {legacy_restored.get('session_id')}")
    
    # Verify round-trip consistency
    assert legacy_restored['session_id'] == legacy_data['session_id']
    assert legacy_restored['mindsweep'] == legacy_data['mindsweep']
    print("✅ State bridge tests passed")


if __name__ == "__main__":
    test_state_bridge()