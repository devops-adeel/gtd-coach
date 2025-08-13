#!/usr/bin/env python3
"""
Weekly Review Workflow Graph
Implements the full GTD weekly review with human-in-the-loop
"""

import logging
import subprocess
import asyncio
from typing import Dict, Literal, Annotated, Optional, List
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langgraph.errors import NodeInterrupt as interrupt
# RetryPolicy is now configured differently in v0.6
# from langgraph.pregel.retry import RetryPolicy

# Import state and tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.tools import (
    analyze_timing_tool,
    load_context_tool,
    save_memory_tool,
    detect_patterns_tool,
    adjust_behavior_tool,
    assess_user_state_tool,
    clarify_items_tool,
    organize_tool,
    prioritize_actions_tool,
    create_project_tool,
    provide_intervention_tool
)

logger = logging.getLogger(__name__)

# Configuration paths
COACH_DIR = Path.home() / "gtd-coach"
SCRIPTS_DIR = COACH_DIR / "scripts"
DATA_DIR = COACH_DIR / "data"


class PhaseTimer:
    """Manages phase timing with subprocess timers"""
    
    # Phase time limits in minutes
    PHASE_LIMITS = {
        'STARTUP': 2,
        'MIND_SWEEP': 10,
        'PROJECT_REVIEW': 12,
        'PRIORITIZATION': 5,
        'WRAP_UP': 3
    }
    
    def __init__(self):
        self.current_timer = None
        self.current_phase = None
    
    def start_phase(self, phase: str) -> subprocess.Popen:
        """Start timer for phase with audio alerts"""
        limit = self.PHASE_LIMITS.get(phase, 5)
        
        # Kill any existing timer
        if self.current_timer:
            self.current_timer.terminate()
        
        # Start bash timer in background
        timer_script = SCRIPTS_DIR / "timer.sh"
        if timer_script.exists():
            self.current_timer = subprocess.Popen(
                [str(timer_script), str(limit * 60), f"{phase} - {limit} minutes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Started timer for {phase}: {limit} minutes")
        else:
            logger.warning(f"Timer script not found: {timer_script}")
        
        self.current_phase = phase
        return self.current_timer
    
    def stop_timer(self):
        """Stop current timer"""
        if self.current_timer:
            self.current_timer.terminate()
            self.current_timer = None


class WeeklyReviewWorkflow:
    """
    GTD Weekly Review workflow with human-in-the-loop
    Implements all 5 phases with strict time-boxing
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize the workflow
        
        Args:
            llm_client: LLM client for agent decisions (optional)
        """
        self.llm_client = llm_client
        self.timer = PhaseTimer()
        
        # Use SqliteSaver for persistence across interrupts
        db_path = DATA_DIR / "gtd_coach.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpointer = SqliteSaver.from_conn_string(str(db_path))
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Get available tools
        self.tools = self._get_workflow_tools()
    
    def _get_workflow_tools(self):
        """Get tools needed for this workflow"""
        return [
            analyze_timing_tool,
            load_context_tool,
            save_memory_tool,
            detect_patterns_tool,
            adjust_behavior_tool,
            assess_user_state_tool,
            clarify_items_tool,
            organize_tool,
            prioritize_actions_tool,
            create_project_tool,
            provide_intervention_tool
        ]
    
    def _build_graph(self) -> StateGraph:
        """Build the weekly review workflow graph"""
        
        # Initialize the graph with our state schema
        workflow = StateGraph(AgentState)
        
        # Add nodes for each phase
        workflow.add_node("startup", self.startup_node)
        workflow.add_node("mind_sweep", self.mind_sweep_node)
        workflow.add_node("project_review", self.project_review_node)
        workflow.add_node("prioritization", self.prioritization_node)
        workflow.add_node("wrapup", self.wrapup_node)
        
        # Add intervention node for ADHD support
        workflow.add_node("intervention", self.intervention_node)
        
        # Add tool node for agent-directed tool use
        tool_node = ToolNode(
            self.tools,
            handle_tool_errors=True
        )
        workflow.add_node("tools", tool_node)
        
        # Add retry policy for critical nodes
        retry_policy = RetryPolicy(
            max_attempts=3,
            retry_on=[ConnectionError, TimeoutError]
        )
        
        # Define the flow
        workflow.add_edge(START, "startup")
        workflow.add_edge("startup", "mind_sweep")
        
        # After mind sweep, check if intervention needed
        workflow.add_conditional_edges(
            "mind_sweep",
            self.check_intervention_needed,
            {
                "intervene": "intervention",
                "continue": "project_review"
            }
        )
        
        # Intervention returns to next phase
        workflow.add_edge("intervention", "project_review")
        
        workflow.add_edge("project_review", "prioritization")
        workflow.add_edge("prioritization", "wrapup")
        workflow.add_edge("wrapup", END)
        
        # Compile with checkpointer for interrupt support
        return workflow.compile(checkpointer=self.checkpointer)
    
    def startup_node(self, state: AgentState) -> AgentState:
        """Initialize the weekly review session"""
        logger.info("Starting weekly review")
        
        # Ensure required fields exist
        state = StateValidator.ensure_required_fields(state)
        
        # Set workflow type
        state['workflow_type'] = 'weekly_review'
        state['session_id'] = datetime.now().strftime("%Y%m%d_%H%M%S")
        state['started_at'] = datetime.now().isoformat()
        state['current_phase'] = 'STARTUP'
        state['completed_phases'] = []
        
        # Start timer
        self.timer.start_phase('STARTUP')
        
        # Load user context
        context_result = load_context_tool.invoke(
            {"user_id": state.get('user_id')},
            state
        )
        
        # Add startup message
        msg = "🎯 GTD Weekly Review - 30 minutes to clarity!\n\n"
        msg += "We'll go through 5 phases:\n"
        msg += "1. STARTUP (2 min) - Get ready\n"
        msg += "2. MIND SWEEP (10 min) - Capture everything\n"
        msg += "3. PROJECT REVIEW (12 min) - Update projects\n"
        msg += "4. PRIORITIZATION (5 min) - Set priorities\n"
        msg += "5. WRAP-UP (3 min) - Save and celebrate\n\n"
        
        if context_result.get('patterns_found', 0) > 0:
            msg += "💭 On your mind lately:\n"
            for pattern in state.get('recurring_patterns', [])[:3]:
                msg += f"  • {pattern}\n"
        
        state['messages'].append(AIMessage(content=msg))
        
        # Ask if ready
        ready_response = interrupt({
            "phase": "STARTUP",
            "prompt": "Ready to begin your weekly review? (yes/no)",
            "type": "confirmation"
        })
        
        if not ready_response.get('ready', True):
            state['messages'].append(
                AIMessage(content="No problem! Come back when you're ready.")
            )
            state['current_phase'] = 'ABORTED'
            return state
        
        state['completed_phases'].append('STARTUP')
        return state
    
    def mind_sweep_node(self, state: AgentState) -> AgentState:
        """Mind sweep phase with human interaction"""
        logger.info("Starting mind sweep phase")
        
        state['current_phase'] = 'MIND_SWEEP'
        self.timer.start_phase('MIND_SWEEP')
        
        # Phase 1: Capture (5 minutes)
        state['messages'].append(
            AIMessage(content="📝 MIND SWEEP - Capture Phase (5 minutes)\n"
                      "Empty your mind! Type everything that's on your mind.\n"
                      "Don't think, just dump. We'll process later.")
        )
        
        # Request items from user
        captured_response = interrupt({
            "phase": "MIND_SWEEP_CAPTURE",
            "prompt": "What's on your mind? (5 minutes to capture everything)",
            "timer_remaining": 300,
            "type": "text_list"
        })
        
        # Store captured items
        items = captured_response.get('items', [])
        for item in items:
            state['captures'].append({
                'content': item,
                'source': 'mind_sweep',
                'capture_time': datetime.now().isoformat(),
                'clarified': False
            })
        
        # Check for ADHD patterns in real-time
        pattern_result = detect_patterns_tool.invoke({}, state)
        
        if pattern_result.get('severity') in ['high', 'critical']:
            # Need intervention
            state['pattern_analysis'] = pattern_result
            state['intervention_needed'] = True
        
        # Phase 2: Scan inboxes (5 minutes)
        state['messages'].append(
            AIMessage(content="\n📥 Now let's scan your inboxes (5 minutes)")
        )
        
        inbox_response = interrupt({
            "phase": "MIND_SWEEP_INBOX",
            "prompt": "Check: Email, Slack, physical inbox. Add any items you find.",
            "timer_remaining": 300,
            "type": "text_list"
        })
        
        # Add inbox items
        for item in inbox_response.get('items', []):
            state['captures'].append({
                'content': item,
                'source': 'inbox_scan',
                'capture_time': datetime.now().isoformat(),
                'clarified': False
            })
        
        state['messages'].append(
            AIMessage(content=f"✅ Mind Sweep complete! Captured {len(state['captures'])} items.")
        )
        
        state['completed_phases'].append('MIND_SWEEP')
        return state
    
    def project_review_node(self, state: AgentState) -> AgentState:
        """Project review phase"""
        logger.info("Starting project review")
        
        state['current_phase'] = 'PROJECT_REVIEW'
        self.timer.start_phase('PROJECT_REVIEW')
        
        # First, clarify captured items
        clarify_result = clarify_items_tool.invoke({}, state)
        
        msg = f"📊 PROJECT REVIEW (12 minutes)\n"
        msg += f"Clarified {clarify_result['clarified_count']} items:\n"
        msg += f"  • {len(clarify_result['actions'])} next actions\n"
        msg += f"  • {len(clarify_result['projects'])} projects\n\n"
        
        state['messages'].append(AIMessage(content=msg))
        
        # Review existing projects
        project_response = interrupt({
            "phase": "PROJECT_REVIEW",
            "prompt": "Review your projects. For each: Is it still active? What's the next action?",
            "timer_remaining": 720,  # 12 minutes
            "type": "project_updates",
            "existing_projects": clarify_result.get('projects', [])
        })
        
        # Process project updates
        for project_update in project_response.get('updates', []):
            if project_update.get('create_new'):
                create_project_tool.invoke({
                    'title': project_update['title'],
                    'outcome': project_update['outcome'],
                    'next_action': project_update['next_action']
                }, state)
        
        state['messages'].append(
            AIMessage(content=f"✅ Reviewed {len(project_response.get('updates', []))} projects")
        )
        
        state['completed_phases'].append('PROJECT_REVIEW')
        return state
    
    def prioritization_node(self, state: AgentState) -> AgentState:
        """Prioritization phase"""
        logger.info("Starting prioritization")
        
        state['current_phase'] = 'PRIORITIZATION'
        self.timer.start_phase('PRIORITIZATION')
        
        # Organize items
        organize_result = organize_tool.invoke({}, state)
        
        # Prioritize actions
        prioritize_result = prioritize_actions_tool.invoke(
            {"criteria": "eisenhower"},
            state
        )
        
        msg = "🎯 PRIORITIZATION (5 minutes)\n"
        msg += f"Organized {organize_result['organized_count']} items\n"
        msg += f"Priority distribution:\n"
        for priority, count in prioritize_result['distribution'].items():
            msg += f"  • {priority}: {count} items\n"
        
        state['messages'].append(AIMessage(content=msg))
        
        # Get user's top 3 for the week
        priority_response = interrupt({
            "phase": "PRIORITIZATION",
            "prompt": "What are your TOP 3 priorities for this week?",
            "timer_remaining": 300,
            "type": "priority_selection",
            "suggestions": prioritize_result['top_priorities'][:5]
        })
        
        state['weekly_priorities'] = priority_response.get('priorities', [])
        
        state['messages'].append(
            AIMessage(content=f"✅ Set {len(state['weekly_priorities'])} weekly priorities")
        )
        
        state['completed_phases'].append('PRIORITIZATION')
        return state
    
    def wrapup_node(self, state: AgentState) -> AgentState:
        """Wrap up the review"""
        logger.info("Wrapping up review")
        
        state['current_phase'] = 'WRAP_UP'
        self.timer.start_phase('WRAP_UP')
        
        # Save to memory
        session_data = {
            'session_id': state['session_id'],
            'captures': state.get('captures', []),
            'processed_items': state.get('processed_items', []),
            'weekly_priorities': state.get('weekly_priorities', []),
            'patterns': state.get('adhd_patterns', []),
            'completed_phases': state['completed_phases']
        }
        
        save_result = save_memory_tool.invoke({
            "episode_type": "weekly_review",
            "episode_data": session_data,
            "description": f"Weekly review {state['session_id']}"
        }, state)
        
        # Assess final state
        assessment = assess_user_state_tool.invoke({}, state)
        
        # Generate summary
        duration = (datetime.now() - datetime.fromisoformat(state['started_at'])).seconds // 60
        
        msg = "🎉 WEEKLY REVIEW COMPLETE!\n\n"
        msg += f"📊 Summary:\n"
        msg += f"  • Duration: {duration} minutes\n"
        msg += f"  • Captured: {len(state.get('captures', []))} items\n"
        msg += f"  • Processed: {len(state.get('processed_items', []))} actions\n"
        msg += f"  • Priorities set: {len(state.get('weekly_priorities', []))}\n\n"
        
        msg += f"💡 Your state: Energy={assessment['energy']}, Focus={assessment['focus']}\n\n"
        
        msg += "🎯 This week focus on:\n"
        for i, priority in enumerate(state.get('weekly_priorities', [])[:3], 1):
            msg += f"  {i}. {priority}\n"
        
        msg += "\n✨ Great job completing your review!"
        
        state['messages'].append(AIMessage(content=msg))
        
        # Stop timer
        self.timer.stop_timer()
        
        state['completed_phases'].append('WRAP_UP')
        state['current_phase'] = 'COMPLETE'
        
        return state
    
    def intervention_node(self, state: AgentState) -> AgentState:
        """Provide ADHD intervention when needed"""
        logger.info("Providing intervention")
        
        pattern_analysis = state.get('pattern_analysis', {})
        patterns = pattern_analysis.get('patterns', {})
        
        # Determine intervention type
        if 'rapid_switching' in patterns:
            intervention_type = 'rapid_switching'
        elif 'overwhelm' in patterns:
            intervention_type = 'overwhelm'
        else:
            intervention_type = 'distraction'
        
        # Provide intervention
        intervention_result = provide_intervention_tool.invoke(
            {"intervention_type": intervention_type},
            state
        )
        
        state['messages'].append(
            AIMessage(content=f"💡 {intervention_result['message']}\n\n"
                      f"Action: {intervention_result['action']}")
        )
        
        # Ask for acknowledgment
        ack_response = interrupt({
            "phase": "INTERVENTION",
            "prompt": intervention_result['action'],
            "type": "acknowledgment"
        })
        
        state['interventions'] = state.get('interventions', [])
        state['interventions'].append({
            'type': intervention_type,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': ack_response.get('acknowledged', True)
        })
        
        # Clear intervention flag
        state['intervention_needed'] = False
        
        return state
    
    def check_intervention_needed(self, state: AgentState) -> Literal["intervene", "continue"]:
        """Check if intervention is needed based on patterns"""
        if state.get('intervention_needed'):
            logger.info("Intervention needed based on patterns")
            return "intervene"
        return "continue"
    
    def run(self, initial_state: Optional[Dict] = None, resume: bool = False) -> Dict:
        """
        Run the workflow
        
        Args:
            initial_state: Optional initial state
            resume: Whether to resume from checkpoint
        
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
                "thread_id": state.get('session_id', datetime.now().strftime("%Y%m%d_%H%M%S")),
                "checkpoint_ns": "weekly_review"
            }
        }
        
        # Run the workflow
        try:
            if resume:
                # Resume from last checkpoint
                logger.info("Resuming from checkpoint")
                final_state = self.graph.invoke(None, config)
            else:
                # Start fresh
                final_state = self.graph.invoke(state, config)
            
            logger.info(f"Workflow completed successfully: {final_state.get('session_id')}")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            # Stop timer on failure
            self.timer.stop_timer()
            raise
        finally:
            # Ensure timer is stopped
            self.timer.stop_timer()


def create_weekly_review_workflow(llm_client=None, **kwargs):
    """
    Factory function to create a weekly review workflow
    
    Args:
        llm_client: Optional LLM client for agent decisions
        **kwargs: Additional configuration
    
    Returns:
        Configured WeeklyReviewWorkflow instance
    """
    return WeeklyReviewWorkflow(llm_client=llm_client)