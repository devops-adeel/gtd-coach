#!/usr/bin/env python3
"""
Daily Clarify Workflow - Agent-First Implementation
Processes Todoist inbox with keep/delete decisions
"""

import logging
from typing import Dict, List, TypedDict, Literal, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

# Import tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.agent.tools.todoist import (
    get_inbox_tasks_tool,
    add_to_today_tool,
    mark_task_complete_tool,
    check_deep_work_limit_tool,
    analyze_task_for_deep_work_tool
)
from gtd_coach.agent.tools.clarify_v3 import (
    clarify_decision_v3,
    batch_clarify_preview_v3,
    deep_work_confirmation_v3,
    clarify_break_v3,
    clarify_session_summary_v3
)
from gtd_coach.integrations.graphiti import GraphitiMemory

logger = logging.getLogger(__name__)


class ClarifyState(TypedDict):
    """State for the daily clarify workflow"""
    # Task management
    inbox_tasks: List[Dict]
    current_task_index: int
    
    # Metrics
    processed_count: int
    deleted_count: int
    deep_work_count: int
    quick_task_count: int
    
    # Session info
    session_id: str
    session_active: bool
    needs_break: bool
    
    # Messages for context
    messages: List


class DailyClarifyWorkflow:
    """
    Agent workflow for daily clarify - processing Todoist inbox
    """
    
    def __init__(self, use_graphiti: bool = True):
        """
        Initialize the clarify workflow
        
        Args:
            use_graphiti: Whether to save metrics to Graphiti
        """
        self.use_graphiti = use_graphiti
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()
        
        # Initialize Graphiti if configured
        if self.use_graphiti:
            session_id = f"clarify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                self.memory = GraphitiMemory(session_id=session_id)
            except:
                logger.warning("Graphiti not configured, metrics won't be saved")
                self.memory = None
        else:
            self.memory = None
    
    def _build_graph(self) -> StateGraph:
        """Build the clarify workflow graph"""
        
        # Initialize graph with state schema
        workflow = StateGraph(ClarifyState)
        
        # Add nodes
        workflow.add_node("load_inbox", self.load_inbox_node)
        workflow.add_node("preview_session", self.preview_session_node)
        workflow.add_node("process_task", self.process_task_node)
        workflow.add_node("check_deep_work", self.check_deep_work_node)
        workflow.add_node("add_to_today", self.add_to_today_node)
        workflow.add_node("offer_break", self.offer_break_node)
        workflow.add_node("save_metrics", self.save_metrics_node)
        workflow.add_node("show_summary", self.show_summary_node)
        
        # Define flow
        workflow.set_entry_point("load_inbox")
        
        # From load_inbox
        workflow.add_conditional_edges(
            "load_inbox",
            lambda x: "preview" if len(x["inbox_tasks"]) > 0 else "show_summary",
            {
                "preview": "preview_session",
                "show_summary": "show_summary"
            }
        )
        
        # From preview_session
        workflow.add_conditional_edges(
            "preview_session",
            lambda x: "process" if x["session_active"] else "show_summary",
            {
                "process": "process_task",
                "show_summary": "show_summary"
            }
        )
        
        # From process_task
        workflow.add_conditional_edges(
            "process_task",
            self._route_after_process,
            {
                "check_deep": "check_deep_work",
                "add_regular": "add_to_today",
                "next_task": "offer_break",
                "done": "save_metrics"
            }
        )
        
        # From check_deep_work
        workflow.add_edge("check_deep_work", "add_to_today")
        
        # From add_to_today
        workflow.add_conditional_edges(
            "add_to_today",
            lambda x: "offer_break" if x["current_task_index"] < len(x["inbox_tasks"]) else "save_metrics",
            {
                "offer_break": "offer_break",
                "save_metrics": "save_metrics"
            }
        )
        
        # From offer_break
        workflow.add_conditional_edges(
            "offer_break",
            lambda x: "process_task" if x["session_active"] else "save_metrics",
            {
                "process_task": "process_task",
                "save_metrics": "save_metrics"
            }
        )
        
        # From save_metrics
        workflow.add_edge("save_metrics", "show_summary")
        
        # From show_summary
        workflow.add_edge("show_summary", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _route_after_process(self, state: ClarifyState) -> str:
        """Route after processing a task"""
        last_decision = state.get("last_decision", "")
        
        if last_decision == "delete":
            # Deleted, move to next task
            if state["current_task_index"] < len(state["inbox_tasks"]):
                return "next_task"
            else:
                return "done"
        elif last_decision == "keep":
            # Check if it might be deep work
            current_task = state["inbox_tasks"][state["current_task_index"] - 1]
            analysis = analyze_task_for_deep_work_tool.invoke(
                {"content": current_task["content"]}
            )
            if analysis["is_deep_work"] and state["deep_work_count"] < 2:
                return "check_deep"
            else:
                return "add_regular"
        else:
            return "done"
    
    def load_inbox_node(self, state: ClarifyState) -> Dict:
        """Load tasks from Todoist inbox"""
        logger.info("Loading Todoist inbox")
        
        result = get_inbox_tasks_tool.invoke({})
        
        if "error" in result:
            logger.error(f"Failed to load inbox: {result['error']}")
            return {
                "inbox_tasks": [],
                "session_active": False,
                "messages": [SystemMessage(content=f"Error: {result['error']}")]
            }
        
        tasks = result.get("tasks", [])
        logger.info(f"Loaded {len(tasks)} tasks from inbox")
        
        return {
            "inbox_tasks": tasks,
            "current_task_index": 0,
            "processed_count": 0,
            "deleted_count": 0,
            "deep_work_count": 0,
            "quick_task_count": 0,
            "session_id": f"clarify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "session_active": len(tasks) > 0,
            "messages": [SystemMessage(content=f"Loaded {len(tasks)} tasks")]
        }
    
    def preview_session_node(self, state: ClarifyState) -> Dict:
        """Preview session and get user confirmation"""
        tasks = state["inbox_tasks"]
        
        # Get user confirmation
        decision = batch_clarify_preview_v3.invoke({
            "task_count": len(tasks),
            "sample_tasks": tasks[:3]
        })
        
        if decision == "proceed":
            logger.info("User confirmed to proceed with clarify session")
            return {
                "session_active": True,
                "messages": state["messages"] + [
                    HumanMessage(content="Let's process these tasks")
                ]
            }
        else:
            logger.info("User cancelled clarify session")
            return {
                "session_active": False,
                "messages": state["messages"] + [
                    HumanMessage(content="Cancel session")
                ]
            }
    
    def process_task_node(self, state: ClarifyState) -> Dict:
        """Process a single task with keep/delete decision"""
        idx = state["current_task_index"]
        tasks = state["inbox_tasks"]
        
        if idx >= len(tasks):
            return {"session_active": False}
        
        current_task = tasks[idx]
        
        # Get user decision
        decision = clarify_decision_v3.invoke({
            "task_content": current_task["content"],
            "task_number": idx + 1,
            "total_tasks": len(tasks)
        })
        
        # Mark task complete in inbox (achieve inbox zero)
        mark_task_complete_tool.invoke({"task_id": current_task["id"]})
        
        updates = {
            "current_task_index": idx + 1,
            "processed_count": state["processed_count"] + 1,
            "last_decision": decision
        }
        
        if decision == "delete":
            updates["deleted_count"] = state["deleted_count"] + 1
            logger.info(f"Deleted task: {current_task['content'][:50]}...")
        
        return updates
    
    def check_deep_work_node(self, state: ClarifyState) -> Dict:
        """Check if task should be deep work"""
        idx = state["current_task_index"] - 1  # We've already incremented
        current_task = state["inbox_tasks"][idx]
        
        # Ask user to confirm deep work
        decision = deep_work_confirmation_v3.invoke({
            "task_content": current_task["content"],
            "current_deep_count": state["deep_work_count"]
        })
        
        return {
            "is_deep_work": decision == "deep",
            "messages": state["messages"] + [
                AIMessage(content=f"Task will be {'deep work' if decision == 'deep' else 'regular'}")
            ]
        }
    
    def add_to_today_node(self, state: ClarifyState) -> Dict:
        """Add task to today's list"""
        idx = state["current_task_index"] - 1  # We've already incremented
        current_task = state["inbox_tasks"][idx]
        is_deep = state.get("is_deep_work", False)
        
        # Add to today
        result = add_to_today_tool.invoke({
            "content": current_task["content"],
            "is_deep_work": is_deep
        })
        
        updates = {}
        if result["success"]:
            if is_deep:
                updates["deep_work_count"] = state["deep_work_count"] + 1
                logger.info(f"Added deep work: {current_task['content'][:50]}...")
            else:
                updates["quick_task_count"] = state["quick_task_count"] + 1
                logger.info(f"Added task: {current_task['content'][:50]}...")
        
        # Clear the deep work flag
        updates["is_deep_work"] = False
        
        return updates
    
    def offer_break_node(self, state: ClarifyState) -> Dict:
        """Offer break every 5 items"""
        processed = state["processed_count"]
        
        # Only offer break every 5 items
        if processed % 5 == 0 and processed < len(state["inbox_tasks"]):
            remaining = len(state["inbox_tasks"]) - processed
            
            decision = clarify_break_v3.invoke({
                "items_processed": processed,
                "items_remaining": remaining
            })
            
            if decision == "pause":
                logger.info(f"User paused session after {processed} items")
                return {"session_active": False}
        
        return {}  # Continue processing
    
    def save_metrics_node(self, state: ClarifyState) -> Dict:
        """Save session metrics to Graphiti"""
        if self.memory:
            try:
                metrics = {
                    "type": "daily_clarify",
                    "date": datetime.now().isoformat(),
                    "metrics": {
                        "inbox_count": len(state["inbox_tasks"]),
                        "processed": state["processed_count"],
                        "deleted": state["deleted_count"],
                        "deep_work": state["deep_work_count"],
                        "quick_tasks": state["quick_task_count"]
                    }
                }
                
                self.memory.add_episode(
                    metrics,
                    f"Daily clarify: {state['processed_count']} items processed"
                )
                
                logger.info("Metrics saved to Graphiti")
            except Exception as e:
                logger.error(f"Failed to save metrics: {e}")
        
        return {}
    
    def show_summary_node(self, state: ClarifyState) -> Dict:
        """Show session summary"""
        summary = clarify_session_summary_v3.invoke({
            "processed": state.get("processed_count", 0),
            "deleted": state.get("deleted_count", 0),
            "deep_work": state.get("deep_work_count", 0),
            "quick_tasks": state.get("quick_task_count", 0)
        })
        
        # Print summary for user
        print(summary["summary"])
        
        return {
            "messages": state.get("messages", []) + [
                SystemMessage(content=summary["summary"])
            ]
        }
    
    def run(self, config: Optional[Dict] = None) -> Dict:
        """
        Run the clarify workflow
        
        Args:
            config: Optional configuration overrides
        
        Returns:
            Final state with metrics
        """
        initial_state = {
            "inbox_tasks": [],
            "current_task_index": 0,
            "processed_count": 0,
            "deleted_count": 0,
            "deep_work_count": 0,
            "quick_task_count": 0,
            "session_active": True,
            "needs_break": False,
            "messages": []
        }
        
        try:
            # Run the workflow
            final_state = self.graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": "clarify-session"}}
            )
            
            return final_state
            
        except KeyboardInterrupt:
            logger.info("Session interrupted by user")
            # Still show summary of what was processed
            self.show_summary_node(initial_state)
            return initial_state
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise


def main():
    """Standalone entry point for testing"""
    import argparse
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(description="Daily Clarify Workflow")
    parser.add_argument("--no-graphiti", action="store_true", 
                       help="Skip Graphiti metrics")
    args = parser.parse_args()
    
    load_dotenv()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run workflow
    workflow = DailyClarifyWorkflow(use_graphiti=not args.no_graphiti)
    workflow.run()


if __name__ == "__main__":
    main()