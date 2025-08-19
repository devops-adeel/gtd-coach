#!/usr/bin/env python3
"""
Daily Capture Workflow Graph
Hybrid workflow combining structured phases with agent decision points
"""

import logging
from typing import Dict, Literal, Annotated, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command
# Use SQLite in-memory for checkpointing
from langgraph.checkpoint.memory import InMemorySaver
# RetryPolicy is now configured differently in v0.6

# Import state and tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.tools import (
    analyze_timing_tool,
    load_context_tool,
    scan_inbox_tool,
    brain_dump_tool,
    detect_capture_patterns_tool,
    clarify_items_tool,
    organize_tool,
    save_memory_tool,
    detect_patterns_tool,
    adjust_behavior_tool,
    assess_user_state_tool
)

logger = logging.getLogger(__name__)


class DailyCaptureWorkflow:
    """
    Hybrid workflow for daily capture combining structure with agent flexibility
    """
    
    def __init__(self, llm_client=None, use_agent_decisions=True):
        """
        Initialize the workflow
        
        Args:
            llm_client: LLM client for agent decisions
            use_agent_decisions: Whether to allow agent to make routing decisions
        """
        self.llm_client = llm_client
        self.use_agent_decisions = use_agent_decisions
        self.tools = self._get_workflow_tools()
        self.graph = self._build_graph()
        self.checkpointer = InMemorySaver()
    
    def _get_workflow_tools(self):
        """Get tools needed for this workflow"""
        return [
            analyze_timing_tool,
            load_context_tool,
            scan_inbox_tool,
            brain_dump_tool,
            detect_capture_patterns_tool,
            clarify_items_tool,
            organize_tool,
            save_memory_tool,
            detect_patterns_tool,
            adjust_behavior_tool,
            assess_user_state_tool
        ]
    
    def _build_graph(self) -> StateGraph:
        """Build the hybrid workflow graph"""
        
        # Initialize the graph with our state schema
        workflow = StateGraph(AgentState)
        
        # Add nodes for each phase
        workflow.add_node("startup", self.startup_node)
        workflow.add_node("load_context", self.load_context_node)
        workflow.add_node("timing_review", self.timing_review_node)
        workflow.add_node("capture_phase", self.capture_phase_node)
        workflow.add_node("pattern_check", self.pattern_check_node)  # Agent decision point
        workflow.add_node("clarify_phase", self.clarify_phase_node)
        workflow.add_node("organize_phase", self.organize_phase_node)
        workflow.add_node("save_memory", self.save_memory_node)
        workflow.add_node("wrapup", self.wrapup_node)
        
        # Add tool node for agent-directed tool use
        tool_node = ToolNode(
            self.tools,
            handle_tool_errors=True
        )
        workflow.add_node("tools", tool_node)
        
        # Define the flow with conditional edges
        workflow.add_edge(START, "startup")
        workflow.add_edge("startup", "load_context")
        
        # After loading context, decide whether to do timing review
        workflow.add_conditional_edges(
            "load_context",
            self.should_review_timing,
            {
                "timing": "timing_review",
                "skip": "capture_phase"
            }
        )
        
        workflow.add_edge("timing_review", "capture_phase")
        workflow.add_edge("capture_phase", "pattern_check")
        
        # Pattern check can trigger intervention or continue
        workflow.add_conditional_edges(
            "pattern_check",
            self.check_intervention_needed,
            {
                "intervene": "tools",  # Use tools for intervention
                "continue": "clarify_phase"
            }
        )
        
        # Tools can return to workflow
        workflow.add_conditional_edges(
            "tools",
            lambda state: "clarify_phase",  # Always return to clarify after intervention
            ["clarify_phase"]
        )
        
        workflow.add_edge("clarify_phase", "organize_phase")
        
        # After organizing, decide if we need to save to memory
        workflow.add_conditional_edges(
            "organize_phase",
            self.should_save_memory,
            {
                "save": "save_memory",
                "skip": "wrapup"
            }
        )
        
        workflow.add_edge("save_memory", "wrapup")
        workflow.add_edge("wrapup", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def startup_node(self, state: AgentState) -> AgentState:
        """Initialize the session"""
        logger.info("Starting daily capture session")
        
        # Ensure required fields exist
        state = StateValidator.ensure_required_fields(state)
        
        # Set workflow type
        state['workflow_type'] = 'daily_capture'
        state['session_id'] = datetime.now().strftime("%Y%m%d_%H%M%S")
        state['started_at'] = datetime.now().isoformat()
        state['current_phase'] = 'startup'
        state['completed_phases'] = []
        
        # Add startup message
        state['messages'].append(
            AIMessage(content="🌅 Good morning! Let's capture what's on your mind and get organized for the day.")
        )
        
        return state
    
    def load_context_node(self, state: AgentState) -> AgentState:
        """Load user context from memory"""
        logger.info("Loading user context")
        
        # Use the load_context_tool
        result = load_context_tool.invoke(
            {"user_id": state.get('user_id')},
            state
        )
        
        # Add message about loaded context
        if result.get('patterns_found', 0) > 0:
            patterns = state.get('recurring_patterns', [])[:3]
            msg = "💭 On your mind lately:\n"
            for pattern in patterns:
                msg += f"  • {pattern}\n"
            state['messages'].append(AIMessage(content=msg))
        
        state['completed_phases'].append('load_context')
        state['current_phase'] = 'load_context'
        
        return state
    
    def timing_review_node(self, state: AgentState) -> AgentState:
        """Review yesterday's time tracking"""
        logger.info("Reviewing timing data")
        
        # Use timing analysis tool
        result = analyze_timing_tool.invoke(
            {"date": "yesterday"},
            state
        )
        
        # Add timing insights message
        if result.get('focus_score'):
            msg = f"📊 Yesterday's focus score: {result['focus_score']}/100\n"
            if result.get('uncategorized_minutes', 0) > 30:
                msg += f"⏱️ {result['uncategorized_minutes']} minutes uncategorized\n"
            msg += result.get('recommendation', '')
            state['messages'].append(AIMessage(content=msg))
        
        state['completed_phases'].append('timing_review')
        state['current_phase'] = 'timing_review'
        
        return state
    
    def capture_phase_node(self, state: AgentState) -> AgentState:
        """Run capture phase - scan inboxes and brain dump"""
        logger.info("Running capture phase")
        
        # This is where in a real implementation we'd handle user interaction
        # For now, we'll add placeholder messages
        
        # Scan inboxes
        inboxes = ['outlook', 'physical', 'slack']
        for inbox in inboxes:
            result = scan_inbox_tool.invoke(
                {"inbox_type": inbox},
                state
            )
            
            state['messages'].append(
                AIMessage(content=f"📥 Scanning {inbox}: {result['guidance']}")
            )
        
        # Brain dump
        brain_dump_result = brain_dump_tool.invoke(
            {},
            state
        )
        
        state['messages'].append(
            AIMessage(content=brain_dump_result['prompt'])
        )
        
        state['completed_phases'].append('capture')
        state['current_phase'] = 'capture'
        
        return state
    
    def pattern_check_node(self, state: AgentState) -> AgentState:
        """Check for ADHD patterns and decide on intervention"""
        logger.info("Checking for patterns")
        
        # Detect patterns
        result = detect_patterns_tool.invoke(
            {},
            state
        )
        
        # Store pattern analysis
        state['pattern_analysis'] = result
        
        # Adjust behavior if needed
        if result.get('severity') in ['high', 'critical']:
            adjust_result = adjust_behavior_tool.invoke(
                {"reason": f"Pattern severity: {result['severity']}"},
                state
            )
            
            state['messages'].append(
                AIMessage(content=f"📊 {adjust_result['message']}")
            )
        
        state['current_phase'] = 'pattern_check'
        
        return state
    
    def clarify_phase_node(self, state: AgentState) -> AgentState:
        """Clarify captured items"""
        logger.info("Clarifying items")
        
        # Clarify all captured items
        result = clarify_items_tool.invoke(
            {},
            state
        )
        
        msg = f"✨ Clarified {result['clarified_count']} items:\n"
        msg += f"  • {len(result['actions'])} next actions\n"
        msg += f"  • {len(result['projects'])} projects\n"
        msg += f"  • {len(result['someday_maybe'])} someday/maybe\n"
        
        state['messages'].append(AIMessage(content=msg))
        
        state['completed_phases'].append('clarify')
        state['current_phase'] = 'clarify'
        
        return state
    
    def organize_phase_node(self, state: AgentState) -> AgentState:
        """Organize items into GTD system"""
        logger.info("Organizing items")
        
        # Organize clarified items
        result = organize_tool.invoke(
            {},
            state
        )
        
        msg = f"📂 Organized {result['organized_count']} items\n"
        msg += result.get('summary', '')
        
        state['messages'].append(AIMessage(content=msg))
        
        state['completed_phases'].append('organize')
        state['current_phase'] = 'organize'
        
        return state
    
    def save_memory_node(self, state: AgentState) -> AgentState:
        """Save session to memory"""
        logger.info("Saving to memory")
        
        # Prepare session data
        session_data = {
            'session_id': state['session_id'],
            'captures': state.get('captures', []),
            'processed_items': state.get('processed_items', []),
            'patterns': state.get('adhd_patterns', []),
            'focus_score': state.get('focus_score')
        }
        
        # Save to memory
        result = save_memory_tool.invoke(
            {
                "episode_type": "daily_capture_session",
                "episode_data": session_data,
                "description": f"Daily capture session {state['session_id']}"
            },
            state
        )
        
        state['messages'].append(
            AIMessage(content=f"💾 {result['message']}")
        )
        
        state['completed_phases'].append('save_memory')
        
        return state
    
    def wrapup_node(self, state: AgentState) -> AgentState:
        """Wrap up the session"""
        logger.info("Wrapping up session")
        
        # Assess final user state
        assessment = assess_user_state_tool.invoke(
            {},
            state
        )
        
        # Generate summary
        capture_count = len(state.get('captures', []))
        processed_count = len(state.get('processed_items', []))
        
        msg = "🎉 Daily Capture Complete!\n\n"
        msg += f"📊 Session Summary:\n"
        msg += f"  • Captured: {capture_count} items\n"
        msg += f"  • Processed: {processed_count} actions\n"
        
        if state.get('focus_score'):
            msg += f"  • Focus Score: {state['focus_score']}/100\n"
        
        msg += f"\n💡 Your state: Energy={assessment['energy']}, Focus={assessment['focus']}\n"
        msg += f"🎯 Top recommendations:\n"
        for rec in assessment['recommendations'][:2]:
            msg += f"  • {rec}\n"
        
        state['messages'].append(AIMessage(content=msg))
        
        state['completed_phases'].append('wrapup')
        state['current_phase'] = 'complete'
        
        return state
    
    def should_review_timing(self, state: AgentState) -> Literal["timing", "skip"]:
        """Decide whether to review timing data"""
        # Skip if explicitly disabled
        if state.get('skip_timing'):
            return "skip"
        
        # Skip if no Timing API configured
        import os
        if not os.getenv('TIMING_API_KEY'):
            return "skip"
        
        # Use agent decision if enabled
        if self.use_agent_decisions and self.llm_client:
            # In production, would ask LLM to decide
            # For now, default to including timing
            pass
        
        return "timing"
    
    def check_intervention_needed(self, state: AgentState) -> Literal["intervene", "continue"]:
        """Check if intervention is needed based on patterns"""
        pattern_analysis = state.get('pattern_analysis', {})
        
        # Intervene if severity is high or critical
        if pattern_analysis.get('intervention_needed'):
            logger.info("Intervention needed based on patterns")
            return "intervene"
        
        return "continue"
    
    def should_save_memory(self, state: AgentState) -> Literal["save", "skip"]:
        """Decide whether to save to memory"""
        # Skip if in test mode
        if state.get('test_mode'):
            return "skip"
        
        # Skip if no items were processed
        if not state.get('processed_items'):
            return "skip"
        
        # Check if Graphiti is configured
        import os
        if not os.getenv('NEO4J_PASSWORD'):
            return "skip"
        
        return "save"
    
    def run(self, initial_state: Optional[Dict] = None) -> Dict:
        """
        Run the workflow
        
        Args:
            initial_state: Optional initial state
        
        Returns:
            Final state after workflow completion
        """
        # Prepare initial state
        if initial_state is None:
            initial_state = {}
        
        state = StateValidator.ensure_required_fields(initial_state)
        
        # Configure for execution
        config = {
            "configurable": {
                "thread_id": state['session_id']
            }
        }
        
        # Run the workflow
        try:
            final_state = self.graph.invoke(state, config)
            logger.info(f"Workflow completed successfully: {final_state['session_id']}")
            return final_state
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise


def create_daily_capture_workflow(llm_client=None, **kwargs):
    """
    Factory function to create a daily capture workflow
    
    Args:
        llm_client: Optional LLM client for agent decisions
        **kwargs: Additional configuration
    
    Returns:
        Configured DailyCaptureWorkflow instance
    """
    return DailyCaptureWorkflow(
        llm_client=llm_client,
        use_agent_decisions=kwargs.get('use_agent_decisions', True)
    )