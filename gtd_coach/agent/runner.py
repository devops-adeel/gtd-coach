#!/usr/bin/env python3
"""
Main Runner for GTD LangGraph Agent
Orchestrates the weekly review with all phases and tools
"""

import logging
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import agent components
from gtd_coach.agent.core import GTDAgent
from gtd_coach.agent.tools import ALL_TOOLS
from gtd_coach.agent.state import AgentState

# Import integrations
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector

logger = logging.getLogger(__name__)


class GTDAgentRunner:
    """
    Main runner for the GTD Agent weekly review
    """
    
    def __init__(self):
        """Initialize the agent runner"""
        # Load environment variables
        load_dotenv()
        
        # Set up logging
        self.setup_logging()
        
        # Initialize components
        self.agent = GTDAgent()
        self.memory = GraphitiMemory()
        self.pattern_detector = ADHDPatternDetector()
        
        # Set tools on agent
        self.agent.set_tools(ALL_TOOLS)
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.user_id = datetime.now().strftime("%G-W%V")  # Weekly user ID
        
        logger.info(f"Initialized GTD Agent Runner - Session: {self.session_id}")
    
    def setup_logging(self):
        """Configure logging for the session"""
        logs_dir = Path.home() / "gtd-coach" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        session_log = logs_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(session_log),
                logging.StreamHandler()
            ]
        )
    
    def create_initial_state(self) -> Dict:
        """
        Create initial state for the agent
        
        Returns:
            Initial state dictionary
        """
        return {
            "messages": [],
            "session_id": self.session_id,
            "workflow_type": "weekly_review",
            "started_at": datetime.now().isoformat(),
            "user_id": self.user_id,
            "user_context": {},
            "adhd_patterns": [],
            "accountability_mode": "firm",
            "captures": [],
            "processed_items": [],
            "projects": [],
            "weekly_priorities": [],
            "current_phase": "STARTUP",
            "completed_phases": [],
            "phase_start_time": datetime.now(),
            "phase_time_limit": 2,  # STARTUP is 2 minutes
            "total_elapsed": 0,
            "time_warnings": [],
            "time_pressure_mode": False,
            "interaction_mode": "conversational",
            "context_usage": {},
            "message_summary": "",
            "phase_summary": "",
            "phase_changed": False,
            "context_overflow_count": 0,
            "phase_durations": {},
            "errors": [],
            "retry_count": 0,
            "skip_timing": False,
            "verbose_mode": True,
            "test_mode": False
        }
    
    def run_weekly_review(self, resume: bool = False, thread_id: Optional[str] = None) -> int:
        """
        Run the complete weekly review
        
        Args:
            resume: Whether to resume from checkpoint
            thread_id: Thread ID for resuming session
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Configuration for agent
            config = {
                "configurable": {
                    "thread_id": thread_id or self.session_id,
                    "checkpoint_ns": "weekly_review"
                }
            }
            
            if resume and thread_id:
                logger.info(f"Resuming session: {thread_id}")
                # Resume from checkpoint
                state = None  # Agent will load from checkpoint
            else:
                logger.info("Starting new weekly review")
                # Create initial state
                state = self.create_initial_state()
                
                # Add welcome message
                welcome = self._get_welcome_message()
                state["messages"].append(SystemMessage(content=welcome))
            
            # Run the agent with streaming
            print("\n" + "="*60)
            print("🎯 GTD WEEKLY REVIEW - LANGGRAPH AGENT")
            print("="*60 + "\n")
            
            # Stream agent execution
            for chunk in self.agent.stream(state, config, stream_mode="values"):
                self._handle_stream_chunk(chunk)
            
            # Final summary
            self._show_final_summary()
            
            logger.info("Weekly review completed successfully")
            return 0
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Review interrupted by user")
            logger.info("Review interrupted by user")
            return 1
            
        except Exception as e:
            print(f"\n\n❌ Error during review: {e}")
            logger.error(f"Review failed: {e}", exc_info=True)
            return 1
    
    def _get_welcome_message(self) -> str:
        """
        Generate welcome message for the review
        
        Returns:
            Welcome message string
        """
        return """🎯 Welcome to your GTD Weekly Review!

This is your ADHD-optimized 30-minute review with strict time boundaries.

We'll go through 5 phases:
1. STARTUP (2 min) - Get ready and set the tone
2. MIND SWEEP (10 min) - Capture everything on your mind
3. PROJECT REVIEW (12 min) - Review projects and next actions
4. PRIORITIZATION (5 min) - Set your top 3 for the week
5. WRAP-UP (3 min) - Save and celebrate

I'll keep you on track with time alerts and encouragement.
Ready to begin? Let's make this productive and fun!"""
    
    def _handle_stream_chunk(self, chunk: Dict):
        """
        Handle a streaming chunk from the agent
        
        Args:
            chunk: Stream chunk from agent
        """
        # Extract messages if present
        if "messages" in chunk and chunk["messages"]:
            last_message = chunk["messages"][-1]
            
            if isinstance(last_message, AIMessage):
                # Agent response
                print(f"\n🤖 Coach: {last_message.content}")
                
            elif isinstance(last_message, HumanMessage):
                # User input (from interrupt)
                print(f"\n👤 You: {last_message.content}")
                
            elif hasattr(last_message, 'content'):
                # Other message types
                print(f"\n{last_message.content}")
        
        # Check for phase transitions
        if "current_phase" in chunk:
            phase = chunk["current_phase"]
            if phase != getattr(self, '_last_phase', None):
                self._handle_phase_transition(phase)
                self._last_phase = phase
        
        # Check for time warnings
        if "time_warnings" in chunk and chunk["time_warnings"]:
            for warning in chunk["time_warnings"]:
                if warning not in getattr(self, '_shown_warnings', []):
                    print(f"\n{warning}")
                    if not hasattr(self, '_shown_warnings'):
                        self._shown_warnings = []
                    self._shown_warnings.append(warning)
    
    def _handle_phase_transition(self, new_phase: str):
        """
        Handle phase transition display
        
        Args:
            new_phase: Name of the new phase
        """
        phase_times = {
            'STARTUP': 2,
            'MIND_SWEEP': 10,
            'PROJECT_REVIEW': 12,
            'PRIORITIZATION': 5,
            'WRAP_UP': 3
        }
        
        time_limit = phase_times.get(new_phase, 5)
        
        print(f"\n{'='*60}")
        print(f"📍 PHASE: {new_phase} ({time_limit} minutes)")
        print(f"{'='*60}\n")
    
    def _show_final_summary(self):
        """Display final summary of the review"""
        print("\n" + "="*60)
        print("🎉 WEEKLY REVIEW COMPLETE!")
        print("="*60)
        
        # Get context metrics from agent
        metrics = self.agent.get_context_metrics()
        
        print(f"\n📊 Session Metrics:")
        print(f"  • Total tokens used: {metrics.get('total_tokens', 0)}")
        print(f"  • Context overflows: {metrics.get('overflow_count', 0)}")
        
        if 'phase_tokens' in metrics:
            print(f"\n  Token usage by phase:")
            for phase, tokens in metrics['phase_tokens'].items():
                if tokens:
                    avg_tokens = sum(tokens) / len(tokens)
                    print(f"    • {phase}: {avg_tokens:.0f} avg tokens")
        
        print(f"\n✨ Great job completing your review!")
        print(f"Remember: Progress, not perfection!\n")


def run_weekly_review(resume: bool = False, thread_id: Optional[str] = None) -> int:
    """
    Entry point for running weekly review
    
    Args:
        resume: Whether to resume from checkpoint
        thread_id: Thread ID for resuming
        
    Returns:
        Exit code
    """
    runner = GTDAgentRunner()
    return runner.run_weekly_review(resume, thread_id)


if __name__ == "__main__":
    # Run the weekly review
    sys.exit(run_weekly_review())