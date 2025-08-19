#!/usr/bin/env python3
"""
GTD Agent - Hybrid Workflow-Agent System
Main agent class that orchestrates tools and workflows
"""

import os
import logging
from typing import Dict, List, Optional, Literal
from datetime import datetime

from langchain_openai import ChatOpenAI
try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
except ImportError:
    LangfuseOpenAI = None
    logger.warning("Langfuse OpenAI wrapper not available")
# from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

# Import workflows and tools
from .state import AgentState, StateValidator
from .tools import get_daily_capture_tools, get_weekly_review_tools, get_all_tools
from .workflows.daily_capture import create_daily_capture_workflow

logger = logging.getLogger(__name__)


class GTDAgent:
    """
    Main GTD Agent class supporting multiple modes and workflows
    """
    
    def __init__(
        self,
        mode: Literal["workflow", "agent", "hybrid"] = "hybrid",
        workflow_type: Literal["daily_capture", "weekly_review", "ad_hoc"] = "daily_capture",
        llm_client=None,
        use_langfuse=True,
        test_mode=False
    ):
        """
        Initialize the GTD Agent
        
        Args:
            mode: Operating mode (workflow, agent, or hybrid)
            workflow_type: Type of workflow to run
            llm_client: Optional pre-configured LLM client
            use_langfuse: Whether to use Langfuse for observability
            test_mode: Whether running in test mode (mocked APIs)
        """
        self.mode = mode
        self.workflow_type = workflow_type
        self.test_mode = test_mode
        
        # Initialize LLM client
        self.llm_client = llm_client or self._initialize_llm_client(use_langfuse)
        
        # Get appropriate tools
        self.tools = self._get_tools_for_workflow()
        
        # Initialize the graph based on mode
        self.graph = self._build_graph()
        
        # Initialize checkpointer for state persistence
        self.checkpointer = InMemorySaver()
        
        logger.info(f"GTDAgent initialized in {mode} mode for {workflow_type}")
    
    def _initialize_llm_client(self, use_langfuse: bool):
        """Initialize the LLM client with optional Langfuse wrapper"""
        
        # Get LM Studio URL from environment
        lm_studio_url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')
        
        if use_langfuse and os.getenv('LANGFUSE_PUBLIC_KEY') and LangfuseOpenAI:
            # Use Langfuse wrapper for observability
            logger.info("Using Langfuse-wrapped OpenAI client")
            client = LangfuseOpenAI(
                base_url=lm_studio_url,
                api_key="lm-studio",  # LM Studio doesn't need a real key
                default_headers={"X-Custom-Header": "gtd-agent"}
            )
        else:
            # Use standard OpenAI client
            logger.info("Using standard OpenAI client")
            client = ChatOpenAI(
                base_url=lm_studio_url,
                api_key="lm-studio",
                model="meta-llama-3.1-8b-instruct",
                temperature=0.7,
                max_tokens=500
            )
        
        return client
    
    def _get_tools_for_workflow(self) -> List:
        """Get appropriate tools based on workflow type"""
        if self.workflow_type == "daily_capture":
            return get_daily_capture_tools()
        elif self.workflow_type == "weekly_review":
            return get_weekly_review_tools()
        else:
            return get_all_tools()
    
    def _build_graph(self):
        """Build the appropriate graph based on mode"""
        if self.mode == "workflow":
            return self._build_workflow_graph()
        elif self.mode == "agent":
            return self._build_agent_graph()
        else:  # hybrid
            return self._build_hybrid_graph()
    
    def _build_workflow_graph(self):
        """Build a pure workflow graph (no agent decisions)"""
        if self.workflow_type == "daily_capture":
            workflow = create_daily_capture_workflow(
                llm_client=None,  # No LLM for pure workflow
                use_agent_decisions=False
            )
            return workflow.graph
        else:
            raise NotImplementedError(f"Workflow {self.workflow_type} not implemented yet")
    
    def _build_agent_graph(self):
        """Build a pure agent graph (fully dynamic)"""
        # TODO: Uncomment when langchain_openai is installed
        # # Use LangGraph's prebuilt create_react_agent
        # agent = create_react_agent(
        #     self.llm_client,
        #     self.tools,
        #     checkpointer=self.checkpointer,
        #     state_schema=AgentState
        # )
        # return agent
        raise NotImplementedError("Agent graph requires langchain_openai to be installed")
    
    def _build_hybrid_graph(self):
        """Build a hybrid workflow-agent graph"""
        if self.workflow_type == "daily_capture":
            workflow = create_daily_capture_workflow(
                llm_client=self.llm_client,
                use_agent_decisions=True
            )
            return workflow.graph
        else:
            raise NotImplementedError(f"Hybrid workflow {self.workflow_type} not implemented yet")
    
    async def run(
        self,
        initial_state: Optional[Dict] = None,
        user_id: Optional[str] = None,
        session_config: Optional[Dict] = None
    ) -> Dict:
        """
        Run the agent/workflow
        
        Args:
            initial_state: Optional initial state
            user_id: Optional user identifier
            session_config: Optional session configuration
        
        Returns:
            Final state after execution
        """
        # Prepare initial state
        if initial_state is None:
            initial_state = {}
        
        # Ensure required fields
        state = StateValidator.ensure_required_fields(initial_state)
        
        # Add configuration
        state['workflow_type'] = self.workflow_type
        state['test_mode'] = self.test_mode
        if user_id:
            state['user_id'] = user_id
        
        # Apply session config if provided
        if session_config:
            state.update(session_config)
        
        # Create execution config
        config = {
            "configurable": {
                "thread_id": state['session_id'],
                "user_id": user_id or "default"
            }
        }
        
        # Add Langfuse metadata if available
        if os.getenv('LANGFUSE_PUBLIC_KEY'):
            config['metadata'] = {
                'langfuse_session_id': state['session_id'],
                'langfuse_user_id': user_id or "default",
                'langfuse_tags': [
                    f"mode:{self.mode}",
                    f"workflow:{self.workflow_type}",
                    "gtd-agent"
                ]
            }
        
        # Run the graph
        try:
            logger.info(f"Starting {self.workflow_type} in {self.mode} mode")
            start_time = datetime.now()
            
            # Execute
            if self.mode == "agent":
                # For pure agent mode, wrap with a simple message
                messages = [{
                    "role": "user",
                    "content": f"Help me with my {self.workflow_type.replace('_', ' ')}"
                }]
                state['messages'] = messages
            
            final_state = await self.graph.ainvoke(state, config)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            final_state['session_duration'] = duration
            
            logger.info(f"Completed {self.workflow_type} in {duration:.1f} seconds")
            
            # Extract summary for return
            summary = self._generate_summary(final_state)
            
            return {
                'success': True,
                'session_id': final_state['session_id'],
                'duration': duration,
                'summary': summary,
                'state': final_state
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': state.get('session_id'),
                'state': state
            }
    
    def _generate_summary(self, state: Dict) -> Dict:
        """Generate execution summary from final state"""
        summary = {
            'captures': len(state.get('captures', [])),
            'processed': len(state.get('processed_items', [])),
            'projects': len(state.get('projects', [])),
            'patterns_detected': state.get('adhd_patterns', []),
            'focus_score': state.get('focus_score'),
            'completed_phases': state.get('completed_phases', []),
            'accountability_mode': state.get('accountability_mode', 'adaptive')
        }
        
        # Add insights if available
        if state.get('pattern_analysis'):
            summary['pattern_severity'] = state['pattern_analysis'].get('severity')
        
        return summary
    
    async def resume(self, session_id: str, checkpoint_id: Optional[str] = None) -> Dict:
        """
        Resume an interrupted session
        
        Args:
            session_id: Session to resume
            checkpoint_id: Optional specific checkpoint
        
        Returns:
            Final state after resuming
        """
        try:
            # Load checkpoint
            config = {
                "configurable": {
                    "thread_id": session_id
                }
            }
            
            # Get saved state
            saved_state = self.checkpointer.get(config, checkpoint_id)
            
            if not saved_state:
                raise ValueError(f"No checkpoint found for session {session_id}")
            
            logger.info(f"Resuming session {session_id} from phase {saved_state.get('current_phase')}")
            
            # Resume execution
            return await self.run(initial_state=saved_state)
            
        except Exception as e:
            logger.error(f"Failed to resume session: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [tool.name for tool in self.tools]
    
    def get_mode_info(self) -> Dict:
        """Get information about current mode and configuration"""
        return {
            'mode': self.mode,
            'workflow_type': self.workflow_type,
            'tools_available': len(self.tools),
            'tool_names': self.get_available_tools(),
            'test_mode': self.test_mode,
            'has_llm': self.llm_client is not None,
            'has_langfuse': os.getenv('LANGFUSE_PUBLIC_KEY') is not None
        }


# Factory functions for common use cases
def create_daily_capture_agent(**kwargs) -> GTDAgent:
    """Create an agent for daily capture"""
    return GTDAgent(
        mode=kwargs.get('mode', 'hybrid'),
        workflow_type='daily_capture',
        **kwargs
    )


def create_weekly_review_agent(**kwargs) -> GTDAgent:
    """Create an agent for weekly review"""
    return GTDAgent(
        mode=kwargs.get('mode', 'hybrid'),
        workflow_type='weekly_review',
        **kwargs
    )


def create_ad_hoc_agent(**kwargs) -> GTDAgent:
    """Create an agent for ad-hoc GTD tasks"""
    return GTDAgent(
        mode=kwargs.get('mode', 'agent'),  # Pure agent for flexibility
        workflow_type='ad_hoc',
        **kwargs
    )