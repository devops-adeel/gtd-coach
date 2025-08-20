#!/usr/bin/env python3
"""
Main Runner for GTD LangGraph Agent
Orchestrates the weekly review with all phases and tools
"""

import logging
import asyncio
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from contextlib import nullcontext
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.types import Command

# Import agent components
from gtd_coach.agent.core import GTDAgent
from gtd_coach.agent.tools import ALL_TOOLS, ESSENTIAL_TOOLS, initialize_state_manager
from gtd_coach.agent.state import AgentState

# Import integrations
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector

# Import enhanced observability
try:
    from gtd_coach.observability import (
        LangfuseTracer, 
        set_global_tracer,
        InterruptDebugger,
        analyze_interrupt_failure
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Enhanced observability not available - using basic mode")
    OBSERVABILITY_AVAILABLE = False
    LangfuseTracer = None

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
        
        # Session tracking (needs to be first for GraphitiMemory)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.user_id = datetime.now().strftime("%G-W%V")  # Weekly user ID
        
        # Initialize prompt manager and fetch prompt object for linking
        self.prompt_object = None
        try:
            from gtd_coach.prompts.manager import get_prompt_manager
            prompt_manager = get_prompt_manager()
            # Fetch the raw prompt object (not just formatted string) for Langfuse linking
            if hasattr(prompt_manager, 'langfuse') and prompt_manager.langfuse:
                self.prompt_object = prompt_manager.langfuse.get_prompt(
                    "gtd-coach-system",
                    label="production"
                )
                logger.info("Fetched Langfuse prompt object for linking")
        except Exception as e:
            logger.warning(f"Could not fetch Langfuse prompt object: {e}")
        
        # Initialize components with correct LM Studio URL and model
        # Fix: Ensure /v1 is included in the URL
        lm_studio_url = os.getenv('LM_STUDIO_URL', 'http://host.docker.internal:1234')
        if not lm_studio_url.endswith('/v1'):
            lm_studio_url = f"{lm_studio_url}/v1"
        self.model_name = os.getenv('LM_STUDIO_MODEL', 'meta-llama-3.1-8b-instruct')  # Store as instance variable
        logger.info(f"Configuring LM Studio: URL={lm_studio_url}, Model={self.model_name}")
        self.agent = GTDAgent(
            lm_studio_url=lm_studio_url, 
            model_name=self.model_name,
            prompt_object=self.prompt_object  # Pass prompt object for linking
        )
        self.memory = GraphitiMemory(session_id=self.session_id)
        self.pattern_detector = ADHDPatternDetector()
        
        # Initialize Graphiti memory connection asynchronously
        self.user_facts_cache = None
        self.cache_time = 0
        self.cache_ttl = int(os.getenv('GRAPHITI_USER_FACTS_CACHE_TTL', '86400'))  # 24 hours default
        
        # Set tools on agent - use ESSENTIAL_TOOLS for now
        self.agent.set_tools(ESSENTIAL_TOOLS)
        logger.info(f"Using essential tool set ({len(ESSENTIAL_TOOLS)} tools)")
        
        logger.info(f"Initialized GTD Agent Runner - Session: {self.session_id}")
    
    async def get_user_facts_cached(self) -> List[str]:
        """
        Fetch and cache user facts from Graphiti for dynamic prompt personalization
        
        Returns:
            List of relevant user facts (strings)
        """
        # Check if cache is still valid
        if self.user_facts_cache and (time.time() - self.cache_time < self.cache_ttl):
            logger.debug("Using cached user facts")
            return self.user_facts_cache
        
        # Initialize Graphiti if not already done
        if not self.memory.is_configured():
            try:
                await self.memory.initialize()
                logger.info("Initialized Graphiti memory connection")
            except Exception as e:
                logger.warning(f"Could not initialize Graphiti: {e}")
                return []
        
        # Fetch fresh facts from Graphiti
        try:
            # Search for user patterns, preferences, and history
            search_query = f"user {self.user_id} patterns preferences history weekly review ADHD"
            results = await self.memory.search_with_context(
                query=search_query,
                num_results=5  # Limit to top 5 most relevant facts
            )
            
            # Extract facts as strings
            facts = []
            for result in results:
                if hasattr(result, 'fact'):
                    facts.append(result.fact)
                elif hasattr(result, 'content'):
                    facts.append(result.content)
                elif isinstance(result, dict) and 'fact' in result:
                    facts.append(result['fact'])
            
            # Cache the results
            self.user_facts_cache = facts
            self.cache_time = time.time()
            
            logger.info(f"Retrieved {len(facts)} user facts from Graphiti")
            return facts
            
        except Exception as e:
            logger.warning(f"Error fetching user facts from Graphiti: {e}")
            return []
    
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
            # Core messaging
            "messages": [],
            
            # Session management  
            "session_id": self.session_id,
            "workflow_type": "weekly_review",
            "started_at": datetime.now().isoformat(),
            "user_id": self.user_id,
            
            # User context
            "user_context": {},
            "previous_session": None,
            "recurring_patterns": None,
            
            # ADHD & Adaptive
            "adhd_patterns": [],
            "accountability_mode": "firm",
            "user_energy": None,
            "focus_level": None,
            "stress_indicators": [],
            
            # GTD data
            "captures": [],
            "processed_items": [],
            "projects": [],
            "weekly_priorities": [],
            
            # Timing integration
            "timing_data": None,
            "focus_score": None,
            "context_switches": None,
            "uncategorized_minutes": None,
            
            # Graphiti memory
            "graphiti_episode_ids": [],
            "memory_batch": [],
            
            # Workflow control
            "current_phase": "STARTUP",
            "completed_phases": [],
            "available_tools": [t.name for t in ESSENTIAL_TOOLS],
            "tool_history": [],
            
            # Time management
            "phase_start_time": datetime.now(),
            "phase_time_limit": 2,  # STARTUP is 2 minutes
            "total_elapsed": 0.0,
            "time_warnings": [],
            "last_time_check": None,
            "time_pressure_mode": False,
            
            # Interaction management
            "interaction_mode": "conversational",
            "awaiting_input": False,
            "input_timeout": None,
            
            # Context window management
            "context_usage": {},
            "message_summary": "",
            "phase_summary": "",
            "phase_changed": False,
            "context_overflow_count": 0,
            
            # Error handling
            "errors": [],
            "retry_count": 0,
            "last_checkpoint": None,
            
            # Metrics
            "phase_durations": {},
            "tool_latencies": {},
            "llm_token_usage": {},
            
            # Feature flags
            "skip_timing": False,
            "voice_enabled": False,
            "verbose_mode": False,
            "test_mode": False,
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
            # Track session start time for metrics
            session_start_time = time.time()
            
            # Initialize enhanced tracer if available
            tracer = None
            callbacks = []
            if OBSERVABILITY_AVAILABLE and LangfuseTracer:
                try:
                    tracer = LangfuseTracer(
                        session_id=self.session_id,
                        user_id=self.user_id,
                        metadata={
                            "workflow_type": "weekly_review",
                            "agent_type": "react_with_interrupt",
                            "tools_count": len(ESSENTIAL_TOOLS),
                            "model": self.model_name
                        }
                    )
                    
                    # Set global tracer for interrupt monitoring
                    set_global_tracer(tracer)
                    
                    # Get Langfuse handler for callbacks
                    # IMPORTANT: Handler is created without parameters per Langfuse v3 pattern
                    # Session ID is passed via config metadata instead
                    langfuse_handler = tracer.get_handler()
                    if langfuse_handler:
                        callbacks = [langfuse_handler]
                    
                    logger.info(f"Enhanced observability enabled for session {self.session_id}")
                except Exception as e:
                    logger.warning(f"Failed to initialize enhanced tracer: {e}")
            
            # Configuration for agent
            config = {
                "configurable": {
                    "thread_id": thread_id or self.session_id,
                    "checkpoint_ns": "weekly_review"
                },
                "callbacks": callbacks,
                "metadata": {
                    "langfuse_session_id": self.session_id,  # Required for Langfuse session tracking
                    "user_id": self.user_id,
                    "workflow_type": "weekly_review",
                    # Add prompt metadata for tracing
                    "prompt_name": "gtd-coach-system" if not self.prompt_object else self.prompt_object.name,
                    "prompt_version": None if not self.prompt_object else getattr(self.prompt_object, 'version', None)
                },
                "recursion_limit": 150  # Ensure agent has enough steps for full conversation
            }
            
            if resume and thread_id:
                logger.info(f"Resuming session: {thread_id}")
                # Resume from checkpoint
                state = None  # Agent will load from checkpoint
            else:
                logger.info("Starting new weekly review")
                
                # Get system prompt from Langfuse
                from gtd_coach.prompts.manager import get_prompt_manager
                prompt_manager = get_prompt_manager()
                
                # Fetch user facts from Graphiti for personalization
                user_facts = []
                try:
                    user_facts = asyncio.run(self.get_user_facts_cached())
                    if user_facts:
                        logger.info(f"Enriching prompt with {len(user_facts)} user facts")
                except Exception as e:
                    logger.warning(f"Could not fetch user facts: {e}")
                
                # Format user facts for inclusion in prompt
                user_context = ""
                if user_facts:
                    user_context = "\n\nPERSONALIZED CONTEXT FROM PREVIOUS SESSIONS:\n"
                    user_context += "\n".join([f"- {fact}" for fact in user_facts[:5]])  # Limit to 5 facts
                    user_context += "\n"
                
                # Get the weekly review system prompt with user context
                prompt_variables = {
                    "current_phase": "STARTUP",
                    "time_elapsed": 0,
                    "time_remaining": 30,  # Total session time
                    "user_context": user_context  # Add user facts as a variable
                }
                
                # Try to use user_context if the prompt template supports it
                system_prompt = prompt_manager.format_prompt(
                    "gtd-coach-system",
                    prompt_variables
                )
                
                # If user_context wasn't in the template, append it manually
                if user_context and "PERSONALIZED CONTEXT" not in system_prompt:
                    system_prompt = system_prompt + user_context
                
                # Add critical instructions for conversation flow
                system_prompt += """

CRITICAL INSTRUCTIONS FOR CONVERSATION FLOW:
1. After calling transition_phase_v2, you MUST use one of the conversation tools to continue
2. Use check_in_with_user_v2 for multiple questions in a phase
3. Use wait_for_user_input_v2 for single questions
4. Use confirm_with_user_v2 for yes/no confirmations

PHASE-SPECIFIC BEHAVIOR:
- STARTUP: After transitioning, use check_in_with_user_v2 with:
  ["How's your energy level today on a scale of 1-10?",
   "Do you have any concerns or blockers before we begin?",
   "Are you ready to start the mind sweep phase?"]
- MIND_SWEEP: Use wait_for_user_input_v2 to ask "What's been on your mind this week?"
- PROJECT_REVIEW: Use wait_for_user_input_v2 to ask about specific projects
- PRIORITIZATION: Use check_in_with_user_v2 to identify top 3 priorities
- WRAP_UP: Use confirm_with_user_v2 to confirm session completion

AVAILABLE CONVERSATION TOOLS:
- check_in_with_user_v2(phase, questions): Ask multiple questions
- wait_for_user_input_v2(prompt): Ask single question and wait
- confirm_with_user_v2(message): Get yes/no confirmation

IMPORTANT: The conversation tools will pause execution and wait for user input.
Never end the conversation without using these tools to engage the user."""
                
                # Start with minimal state to debug streaming issue
                state = {
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content="Let's start the GTD weekly review.")
                    ]
                }
                
                # Add essential fields for tools to work
                state["session_id"] = self.session_id
                state["workflow_type"] = "weekly_review"
                state["current_phase"] = "STARTUP"
                state["started_at"] = datetime.now().isoformat()
                state["user_id"] = self.user_id
                
                # Add minimal required fields for tools
                state["user_context"] = {}
                state["previous_session"] = None
                state["recurring_patterns"] = None
                state["adhd_patterns"] = []
                state["accountability_mode"] = "firm"
                state["user_energy"] = None
                state["focus_level"] = None
                state["stress_indicators"] = []
                
                # GTD data
                state["captures"] = []
                state["processed_items"] = []
                state["projects"] = []
                state["weekly_priorities"] = []
                
                # Timing and memory
                state["timing_data"] = None
                state["focus_score"] = None
                state["context_switches"] = None
                state["uncategorized_minutes"] = None
                state["graphiti_episode_ids"] = []
                state["memory_batch"] = []
                
                # Phase management
                state["completed_phases"] = []
                state["phase_start_time"] = datetime.now()
                state["phase_time_limit"] = 2  # STARTUP is 2 minutes
                
                # Initialize state manager for V2 tools
                initialize_state_manager(state)
                logger.info("Initialized state manager for V2 tools with minimal state")
            
            # Run the agent with streaming
            print("\n" + "="*60)
            print("🎯 GTD WEEKLY REVIEW - LANGGRAPH AGENT")
            print("="*60 + "\n")
            
            # Trace graph configuration
            if tracer:
                tracer.trace_graph_config({
                    "checkpointer": "InMemorySaver",
                    "thread_id": config["configurable"]["thread_id"],
                    "recursion_limit": config.get("recursion_limit"),
                    "tools": [t.name for t in ESSENTIAL_TOOLS]
                })
            
            # Stream agent execution with debugging
            stream_completed = False
            chunk_count = 0
            interrupt_count = 0
            last_result = None
            
            logger.info(f"Starting agent stream with config: {config}")
            logger.debug(f"Session ID in metadata: {config.get('metadata', {}).get('langfuse_session_id')}")
            
            # Use interrupt debugger for comprehensive tracking
            with InterruptDebugger("main_stream") if OBSERVABILITY_AVAILABLE else nullcontext() as debugger:
                for chunk in self.agent.stream(state, config, stream_mode="values"):
                    self._handle_stream_chunk(chunk)
                    stream_completed = True
                    chunk_count += 1
                    last_result = chunk  # Store the last chunk
                    
                    # Log chunk details for debugging
                    logger.debug(f"Stream chunk #{chunk_count}: keys={list(chunk.keys()) if isinstance(chunk, dict) else 'non-dict'}")
                    
                    # Track chunk with enhanced tracer
                    if tracer:
                        tracer.trace_stream_chunk(chunk, chunk_count)
                    
                    # Check for interrupts in debugger
                    if debugger and hasattr(debugger, 'check_interrupt_result'):
                        debugger.check_interrupt_result(chunk)
            
            # Handle interrupts in a loop until there are no more
            logger.info(f"Checking for interrupts in last result. Has __interrupt__ key: {'__interrupt__' in last_result if last_result else 'No result'}")
            
            while last_result and '__interrupt__' in last_result:
                logger.info(f"✅ INTERRUPT DETECTED in result: {last_result.get('__interrupt__')}")
                interrupts = last_result['__interrupt__']
                
                # Handle each interrupt in this batch
                for interrupt_data in interrupts if isinstance(interrupts, list) else [interrupts]:
                    interrupt_count += 1
                    
                    # Extract the interrupt value/question
                    if hasattr(interrupt_data, 'value'):
                        prompt = interrupt_data.value
                    elif isinstance(interrupt_data, dict) and 'value' in interrupt_data:
                        prompt = interrupt_data['value']
                    else:
                        prompt = str(interrupt_data)
                    
                    logger.info(f"Interrupt #{interrupt_count}: {prompt}")
                    
                    # Track interrupt with enhanced tracer
                    if tracer:
                        tracer.trace_interrupt_captured(interrupt_data)
                    
                    print("\n" + "="*60)
                    print(f"🔔 Agent needs input: {prompt}")
                    
                    # Get user input
                    try:
                        user_input = input("👤 You: ")
                    except (EOFError, KeyboardInterrupt):
                        print("\n⚠️ Review interrupted by user")
                        break
                    
                    print("="*60 + "\n")
                    
                    # Resume agent with user input
                    logger.info(f"Resuming agent with Command(resume={user_input})")
                    
                    # Track resume with enhanced tracer
                    if tracer:
                        tracer.trace_interrupt_resume(user_input)
                    
                    # Resume using invoke to get complete state (avoids nested streaming)
                    # This returns the full state including any new interrupts
                    logger.info("Using invoke() for resume to avoid nested streaming")
                    last_result = self.agent.invoke(
                        Command(resume=user_input),
                        config
                    )
                    
                    # Handle the result as a single chunk
                    if last_result:
                        self._handle_stream_chunk(last_result)
                        chunk_count += 1
                        
                        # Track resumed state
                        if tracer:
                            tracer.trace_stream_chunk(last_result, chunk_count)
                    
                    # After handling this interrupt, the loop will check for more
                    logger.info(f"Completed interrupt #{interrupt_count}, checking for more...")
            
            # Log when no more interrupts are detected
            if interrupt_count == 0:
                logger.warning(f"❌ NO INTERRUPTS DETECTED in stream result")
            else:
                logger.info(f"✅ All {interrupt_count} interrupts handled successfully")
                if last_result:
                    logger.debug(f"Last result keys: {list(last_result.keys()) if isinstance(last_result, dict) else 'non-dict'}")
                    logger.debug(f"Last result (truncated): {str(last_result)[:500]}")
            
            # Final tracking and analysis
            if tracer:
                # Score conversation flow
                flow_scores = tracer.score_conversation_flow()
                
                # Get metrics summary
                metrics_summary = tracer.get_metrics_summary()
                logger.info(f"Session metrics: {metrics_summary}")
                
                # Analyze interrupt success
                if interrupt_count == 0 and tracer.metrics["interrupt_attempts"] > 0:
                    analyze_interrupt_failure(
                        expected_interrupt=True,
                        actual_result=last_result,
                        tool_name="conversation_tools",
                        additional_context={
                            "chunks": chunk_count,
                            "attempts": tracer.metrics["interrupt_attempts"]
                        }
                    )
                
                # Add session effectiveness scoring
                session_duration_minutes = (time.time() - session_start_time) / 60
                session_completed = stream_completed and interrupt_count > 0
                
                # Extract metrics from last_result (final state)
                if last_result:
                    captures_count = len(last_result.get("captures", []))
                    priorities_count = len(last_result.get("weekly_priorities", []))
                else:
                    captures_count = 0
                    priorities_count = 0
                
                # Calculate effectiveness score
                effectiveness_score = 1.0 if session_completed else 0.0
                if captures_count > 0:
                    effectiveness_score = min(1.0, effectiveness_score + 0.2)
                if priorities_count > 0:
                    effectiveness_score = min(1.0, effectiveness_score + 0.3)
                if session_duration_minutes <= 30:
                    effectiveness_score = min(1.0, effectiveness_score + 0.2)
                
                # Trace session effectiveness
                tracer.trace_event("session.effectiveness", {
                    "completed": session_completed,
                    "duration_minutes": session_duration_minutes,
                    "tasks_captured": captures_count,
                    "priorities_set": priorities_count,
                    "interrupts_handled": interrupt_count
                }, score=effectiveness_score)
                
                logger.info(f"Session effectiveness: {effectiveness_score:.2f} "
                          f"(captured: {captures_count}, priorities: {priorities_count}, "
                          f"duration: {session_duration_minutes:.1f}min)")
                
                # Flush events
                tracer.flush()
            
            if not stream_completed:
                logger.warning("Stream ended without producing any chunks")
            else:
                logger.info(f"Stream completed with {chunk_count} chunks, {interrupt_count} interrupts")
            
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
        
        # Track phase transition if tracer available
        from gtd_coach.observability import get_global_tracer
        tracer = get_global_tracer()
        if tracer and hasattr(self, '_last_phase'):
            tracer.trace_phase_transition(
                from_phase=self._last_phase,
                to_phase=new_phase,
                duration=None  # Duration tracked elsewhere
            )
        
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