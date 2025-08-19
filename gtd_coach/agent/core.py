#!/usr/bin/env python3
"""
Core LangGraph ReAct Agent for GTD Coach
Handles the main agent logic with aggressive context management for 32K token limit
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import InMemorySaver
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class GTDAgent:
    """
    Main GTD Coach agent using LangGraph ReAct pattern
    Optimized for Llama 3.1 8B with 32K context window
    """
    
    # Phase time limits in minutes
    PHASE_LIMITS = {
        'STARTUP': 2,
        'MIND_SWEEP': 10,
        'PROJECT_REVIEW': 12,
        'PRIORITIZATION': 5,
        'WRAP_UP': 3
    }
    
    # Token budget allocation (optimized for xLAM-7b-fc-r)
    MAX_INPUT_TOKENS = 6000  # Increased for better tool descriptions
    MAX_RESPONSE_TOKENS = 2000  # Response generation
    SUMMARY_TOKENS = 500  # Phase summaries
    SAFETY_BUFFER = 23500  # Reserve for system prompt and tools
    
    def __init__(self, 
                 lm_studio_url: str = "http://localhost:1234/v1",
                 model_name: str = "xlam-7b-fc-r",  # Default to xLAM function calling model
                 checkpoint_dir: Optional[Path] = None,
                 use_memory_saver: bool = False):
        """
        Initialize the GTD Agent
        
        Args:
            lm_studio_url: URL for LM Studio API
            model_name: Model identifier
            checkpoint_dir: Directory for SQLite checkpoints
            use_memory_saver: Use in-memory checkpointer (for testing)
        """
        self.lm_studio_url = lm_studio_url
        self.model_name = model_name
        
        # Initialize LLM client for LM Studio
        self.llm = self._create_lm_studio_client()
        
        # Set up checkpointer
        if use_memory_saver:
            self.checkpointer = InMemorySaver()
        else:
            # For now, use InMemorySaver to avoid SQLite issues
            # TODO: Fix SqliteSaver implementation
            self.checkpointer = InMemorySaver()
            logger.warning("Using InMemorySaver instead of SqliteSaver due to compatibility issues")
        
        # Will be populated with tools
        self.tools = []
        
        # Agent will be created after tools are set
        self.agent = None
        
        # Track context usage
        self.context_metrics = {
            'total_tokens': 0,
            'phase_tokens': {},
            'overflow_count': 0
        }
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=lambda retry_state: logger.warning(
            f"LM Studio connection attempt {retry_state.attempt_number} failed, retrying..."
        )
    )
    def _create_lm_studio_client(self) -> ChatOpenAI:
        """
        Create OpenAI-compatible client for LM Studio with retry logic
        
        Returns:
            Configured ChatOpenAI client
            
        Raises:
            ConnectionError: If unable to connect after retries
        """
        client = ChatOpenAI(
            base_url=self.lm_studio_url,
            api_key="not-needed",  # LM Studio doesn't require API key
            model=self.model_name,
            temperature=0.7,
            max_tokens=self.MAX_RESPONSE_TOKENS,
            streaming=True,  # Enable streaming for real-time feedback
            timeout=30,  # 30 second timeout for local inference
        )
        
        # Perform health check
        if not self._check_lm_studio_health():
            raise ConnectionError(
                f"LM Studio server not responding at {self.lm_studio_url}. "
                "Please ensure LM Studio is running with a model loaded."
            )
        
        logger.info(f"Successfully connected to LM Studio at: {self.lm_studio_url}")
        return client
    
    def _check_lm_studio_health(self) -> bool:
        """
        Check if LM Studio server is healthy
        
        Returns:
            True if server is responding, False otherwise
        """
        try:
            import requests
            # Check the models endpoint
            response = requests.get(
                f"{self.lm_studio_url.replace('/v1', '')}/v1/models",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                if models:
                    logger.info(f"LM Studio has {len(models)} model(s) loaded")
                    return True
                else:
                    logger.warning("LM Studio is running but no models are loaded")
                    return False
            return False
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def set_tools(self, tools: List) -> None:
        """
        Set tools and create the agent
        
        Args:
            tools: List of LangChain tools
        """
        self.tools = tools
        self._create_agent()
        
    def _create_agent(self) -> None:
        """
        Create the ReAct agent with tools and context management
        """
        if not self.tools:
            raise ValueError("Tools must be set before creating agent")
        
        # Test LLM directly before creating agent
        logger.info("Testing LLM connection before creating agent...")
        try:
            from langchain_core.messages import HumanMessage
            test_response = self.llm.invoke([HumanMessage(content="Say 'OK'")])
            logger.info(f"LLM test successful: {test_response.content[:50]}")
        except Exception as e:
            logger.error(f"LLM test failed: {e}")
            raise
        
        # Create agent with tools (V2 tools don't need state injection)
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            checkpointer=self.checkpointer
        )
        
        logger.info(f"Created ReAct agent with {len(self.tools)} tools")
    
    def _pre_model_hook(self, state: Dict) -> List:
        """
        Aggressive context management hook
        Called before every LLM invocation
        
        Args:
            state: Current agent state
            
        Returns:
            Modified messages for LLM input
        """
        messages = state.get("messages", [])
        
        # Check if phase changed - if so, summarize and reset
        if state.get("phase_changed", False):
            summary = self._summarize_phase(messages, state.get("current_phase", ""))
            state["phase_summary"] = state.get("phase_summary", "") + f"\n{summary}"
            # Keep only last 2 messages after phase change
            messages = messages[-2:] if len(messages) > 2 else messages
            state["phase_changed"] = False
            logger.info(f"Phase changed - reset context to {len(messages)} messages")
        
        # Count current tokens
        current_tokens = count_tokens_approximately(messages)
        
        # Aggressive trimming if over limit
        if current_tokens > self.MAX_INPUT_TOKENS:
            logger.warning(f"Context at {current_tokens} tokens - trimming aggressively")
            messages = trim_messages(
                messages,
                strategy="last",
                token_counter=count_tokens_approximately,
                max_tokens=self.MAX_INPUT_TOKENS,
                start_on="human",
                end_on=("human", "tool"),
                allow_partial=False
            )
            self.context_metrics['overflow_count'] += 1
        
        # Add time awareness and phase context
        time_context = self._get_time_context(state)
        phase_guidance = self._get_phase_guidance(state)
        
        # Construct final message list with system prompts
        system_messages = []
        
        # Compact system prompt
        system_messages.append(SystemMessage(content=self._get_system_prompt(state)))
        
        # Add time and phase context
        if time_context:
            system_messages.append(SystemMessage(content=time_context))
        
        if phase_guidance:
            system_messages.append(SystemMessage(content=phase_guidance))
        
        # Add phase summary if exists
        if state.get("phase_summary"):
            system_messages.append(SystemMessage(
                content=f"Previous phases summary:\n{state['phase_summary'][-self.SUMMARY_TOKENS:]}"
            ))
        
        # Track token usage
        total_tokens = count_tokens_approximately(system_messages + messages)
        self.context_metrics['total_tokens'] = total_tokens
        
        current_phase = state.get("current_phase", "UNKNOWN")
        if current_phase not in self.context_metrics['phase_tokens']:
            self.context_metrics['phase_tokens'][current_phase] = []
        self.context_metrics['phase_tokens'][current_phase].append(total_tokens)
        
        logger.debug(f"Sending {total_tokens} tokens to LLM (phase: {current_phase})")
        
        return system_messages + messages
    
    def _get_system_prompt(self, state: Dict) -> str:
        """
        Get compact system prompt based on current state
        
        Args:
            state: Current agent state
            
        Returns:
            System prompt string
        """
        mode = state.get("accountability_mode", "firm")
        phase = state.get("current_phase", "STARTUP")
        
        # Compact ADHD-optimized prompt with tool hints for xLAM
        base_prompt = (
            "You are an ADHD coach guiding a 30-minute GTD weekly review. "
            f"Current phase: {phase}. "
            "Be concise, supportive, and time-aware. "
            "Help user stay focused and celebrate progress. "
            "Use available tools to manage time, capture items, and track progress. "
        )
        
        if mode == "firm":
            base_prompt += "Use direct, structured guidance. Keep strict time boundaries."
        else:
            base_prompt += "Use gentle encouragement. Allow some flexibility."
        
        return base_prompt
    
    def _get_time_context(self, state: Dict) -> str:
        """
        Generate time awareness context
        
        Args:
            state: Current agent state
            
        Returns:
            Time context string
        """
        if not state.get("phase_start_time"):
            return ""
        
        phase = state.get("current_phase", "UNKNOWN")
        phase_limit = self.PHASE_LIMITS.get(phase, 5)
        
        elapsed = (datetime.now() - state["phase_start_time"]).seconds / 60
        remaining = phase_limit - elapsed
        
        if remaining < 1:
            return f"⚠️ TIME UP for {phase}! Must transition NOW!"
        elif remaining < 2:
            return f"⏰ {remaining:.1f} min left in {phase} - wrap up quickly!"
        elif remaining < phase_limit * 0.3:
            return f"⏱️ {remaining:.1f} min remaining in {phase}"
        else:
            return f"✓ {remaining:.0f} min remaining in {phase}"
    
    def _get_phase_guidance(self, state: Dict) -> str:
        """
        Get phase-specific guidance
        
        Args:
            state: Current agent state
            
        Returns:
            Phase guidance string
        """
        phase = state.get("current_phase", "STARTUP")
        
        guidance = {
            'STARTUP': "Check in with user. Are they ready? Set positive tone.",
            'MIND_SWEEP': "Capture everything quickly. No judging, just dumping.",
            'PROJECT_REVIEW': "Review projects efficiently. What's the next action?",
            'PRIORITIZATION': "Focus on top 3 for the week. Use ABC method.",
            'WRAP_UP': "Save data, celebrate completion, positive reinforcement."
        }
        
        return guidance.get(phase, "")
    
    def _summarize_phase(self, messages: List, phase: str) -> str:
        """
        Create compact summary of phase for context preservation
        
        Args:
            messages: Messages from the phase
            phase: Phase name
            
        Returns:
            Summary string
        """
        # Extract key information based on phase
        if phase == "MIND_SWEEP":
            # Count items captured
            items = [m.content for m in messages if isinstance(m, HumanMessage)]
            return f"Mind Sweep: Captured {len(items)} items"
        
        elif phase == "PROJECT_REVIEW":
            # Note projects touched
            return f"Project Review: Reviewed projects, identified next actions"
        
        elif phase == "PRIORITIZATION":
            # Extract priorities if mentioned
            return f"Prioritization: Set weekly priorities"
        
        else:
            return f"{phase}: Completed"
    
    def invoke(self, state: Dict, config: Dict) -> Dict:
        """
        Invoke the agent with state and configuration
        
        Args:
            state: Initial or current state
            config: Configuration including thread_id
            
        Returns:
            Updated state after agent execution
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call set_tools() first.")
        
        try:
            # Ensure required state fields
            state = self._ensure_state_fields(state)
            
            # Run agent
            result = self.agent.invoke(state, config)
            
            # Log context metrics
            logger.info(f"Context usage - Total: {self.context_metrics['total_tokens']}, "
                       f"Overflows: {self.context_metrics['overflow_count']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    def stream(self, state: Dict, config: Dict, stream_mode: str = "values"):
        """
        Stream agent execution for real-time feedback
        
        Args:
            state: Initial or current state
            config: Configuration including thread_id
            stream_mode: Type of streaming (values, updates, debug)
            
        Yields:
            Streaming chunks from agent
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call set_tools() first.")
        
        try:
            # Ensure required state fields
            state = self._ensure_state_fields(state)
            
            # Stream agent execution
            for chunk in self.agent.stream(state, config, stream_mode=stream_mode):
                yield chunk
                
        except Exception as e:
            logger.error(f"Agent streaming failed: {e}")
            raise
    
    def _ensure_state_fields(self, state: Dict) -> Dict:
        """
        Ensure required fields exist in state
        
        Args:
            state: Current state
            
        Returns:
            State with required fields
        """
        defaults = {
            "messages": [],
            "current_phase": "STARTUP",
            "phase_start_time": datetime.now(),
            "accountability_mode": "firm",
            "phase_summary": "",
            "phase_changed": False,
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        
        for key, default_value in defaults.items():
            if key not in state:
                state[key] = default_value
        
        return state
    
    def get_context_metrics(self) -> Dict:
        """
        Get context usage metrics
        
        Returns:
            Dictionary of context metrics
        """
        return self.context_metrics.copy()