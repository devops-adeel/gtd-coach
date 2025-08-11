#!/usr/bin/env python3
"""
GTD Weekly Review Coach for ADHD
Orchestrates the review process with LM Studio
"""

import requests
import json
import subprocess
import time
import sys
import os
import logging
import asyncio
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import memory integration modules
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector

# Import Langfuse for prompt management and OpenAI SDK wrapper
try:
    from langfuse import Langfuse
    LANGFUSE_PROMPTS_AVAILABLE = True
except ImportError:
    LANGFUSE_PROMPTS_AVAILABLE = False

# Import Langfuse OpenAI SDK wrapper for trace linking
try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
    LANGFUSE_OPENAI_AVAILABLE = True
except ImportError:
    LANGFUSE_OPENAI_AVAILABLE = False
    # Fall back to standard OpenAI SDK if available
    try:
        from openai import OpenAI as StandardOpenAI
        STANDARD_OPENAI_AVAILABLE = True
    except ImportError:
        STANDARD_OPENAI_AVAILABLE = False

# Import Timing integration
from gtd_coach.integrations.timing import TimingAPI, get_mock_projects
from gtd_coach.integrations.timing_comparison import compare_time_with_priorities, generate_simple_time_summary, suggest_time_adjustments

# Import Langfuse for LLM observability
try:
    from gtd_coach.integrations.langfuse import get_langfuse_client, score_response, validate_configuration
    from langfuse import observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    observe = lambda *args, **kwargs: lambda func: func  # No-op decorator

# Import LLM-as-a-Judge evaluation system
try:
    from gtd_coach.evaluation import PostSessionEvaluator
    EVALUATION_AVAILABLE = True
except ImportError:
    EVALUATION_AVAILABLE = False

# Configuration
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama-3.1-8b-instruct"  # Actual model name for API
# Handle Docker vs local paths
if os.environ.get("IN_DOCKER"):
    COACH_DIR = Path("/app")
else:
    COACH_DIR = Path.home() / "gtd-coach"

PROMPTS_DIR = COACH_DIR / "prompts"
DATA_DIR = COACH_DIR / "data" 
LOGS_DIR = COACH_DIR / "logs"
SCRIPTS_DIR = COACH_DIR / "scripts"

# Create a session for connection reuse
session = requests.Session()
session.headers.update({'Connection': 'keep-alive'})

class GTDCoach:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Set up logging
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.setup_logging()
        
        # Generate weekly user profile (ISO 8601 week format)
        self.user_id = datetime.now().strftime("%G-W%V")  # e.g., "2025-W32"
        
        # Create event loop for async tasks
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.messages = []
        self.review_start_time = None
        self.review_data = {
            "projects_reviewed": 0,
            "decisions_made": 0,
            "items_captured": 0,
            "phase_durations": {},
            "interventions_offered": 0,
            "interventions_accepted": 0,
            "interventions_skipped": 0
        }
        self.priorities = []  # Store priorities for wrap-up phase
        self.mindsweep_items = []  # Store mindsweep items for pattern detection
        
        # Initialize memory and pattern detection
        self.memory = GraphitiMemory(self.session_id)
        self.pattern_detector = ADHDPatternDetector()
        self.current_phase = "STARTUP"
        
        # Initialize intervention system
        self.interventions_enabled = False  # Will be set by N-of-1 config
        self.last_intervention_time = None  # For cooldown tracking
        
        # Initialize North Star metrics tracking
        from gtd_coach.metrics import NorthStarMetrics
        self.north_star = NorthStarMetrics(self.session_id)
        
        # Initialize N-of-1 experiment framework
        from gtd_coach.experiments import NOf1Experimenter
        self.experimenter = NOf1Experimenter()
        self.experimenter.apply_experiment_config(self)
        self.experimenter.log_session_start()
        
        # Initialize lightweight pattern detector for memory retrieval
        try:
            from pattern_detector import PatternDetector
            self.memory_patterns = PatternDetector()
        except ImportError:
            self.logger.warning("Pattern detector not available for memory retrieval")
            self.memory_patterns = None
        
        # Initialize Timing API
        self.timing_api = TimingAPI()
        self.timing_projects = None  # Will be populated during startup
        self.timing_fetch_task = None  # Async task for fetching projects
        
        # Initialize Langfuse client if available
        self.langfuse_enabled = False
        self.langfuse_client = None
        self.langfuse_prompts = None  # For prompt management
        self.prompt_tone = None  # For A/B testing tracking
        self.openai_client = None  # OpenAI client for LLM calls
        self.current_graphiti_batch_id = None  # Track current Graphiti batch
        self.phase_metrics = {}  # Store phase-specific metrics for trace enrichment
        
        # Initialize OpenAI client with Langfuse wrapper or standard SDK
        self.initialize_openai_client()
        
        # Try to initialize Langfuse for observability
        if LANGFUSE_AVAILABLE and validate_configuration():
            try:
                self.langfuse_client = get_langfuse_client()
                self.langfuse_enabled = True
                self.logger.info("Langfuse observability enabled")
            except Exception as e:
                self.logger.warning(f"Langfuse initialization failed: {e}")
                self.langfuse_enabled = False
        
        # Try to initialize Langfuse for prompt management (separate from observability)
        if LANGFUSE_PROMPTS_AVAILABLE:
            try:
                self.langfuse_prompts = Langfuse()
                self.logger.info("Langfuse prompt management enabled")
                # A/B test: randomly select coaching tone
                self.prompt_tone = random.choice(["firm", "gentle"])
                self.logger.info(f"Selected coaching tone: {self.prompt_tone}")
            except Exception as e:
                self.logger.warning(f"Langfuse prompt management initialization failed: {e}")
                self.langfuse_prompts = None
        
        # Initialize LLM-as-a-Judge evaluation system
        self.evaluator = None
        self.interaction_history = []  # Track interactions for evaluation
        if EVALUATION_AVAILABLE:
            try:
                self.evaluator = PostSessionEvaluator()
                self.logger.info("LLM-as-a-Judge evaluation system enabled")
            except Exception as e:
                self.logger.warning(f"Evaluation system initialization failed: {e}")
                self.evaluator = None
        
        # Phase-specific settings for optimal LLM performance
        self.phase_settings = {
            'STARTUP': {
                'temperature': 0.8,  # Warm, welcoming tone
                'max_tokens': 300
            },
            'MIND_SWEEP': {
                'temperature': 0.7,  # More focused for capture
                'max_tokens': 300
            },
            'PROJECT_REVIEW': {
                'temperature': 0.8,  # Balanced creativity
                'max_tokens': 500
            },
            'PRIORITIZATION': {
                'temperature': 0.6,  # More deterministic for decisions
                'max_tokens': 400
            },
            'WRAP_UP': {
                'temperature': 0.9,  # Encouraging and celebratory
                'max_tokens': 400
            }
        }
        
        # Set up intervention callback for real-time pattern detection
        self.memory.set_intervention_callback(self.handle_intervention)
        
        self.load_system_prompt()
    
    def initialize_openai_client(self):
        """Initialize OpenAI client with Langfuse wrapper or standard SDK"""
        try:
            if LANGFUSE_OPENAI_AVAILABLE:
                # Use Langfuse OpenAI wrapper for automatic trace linking
                self.openai_client = LangfuseOpenAI(
                    base_url="http://localhost:1234/v1",  # LM Studio endpoint
                    api_key="lm-studio"  # Required but unused by LM Studio
                )
                self.logger.info("Initialized Langfuse OpenAI SDK wrapper for trace linking")
            elif STANDARD_OPENAI_AVAILABLE:
                # Fall back to standard OpenAI SDK
                self.openai_client = StandardOpenAI(
                    base_url="http://localhost:1234/v1",
                    api_key="lm-studio"
                )
                self.logger.info("Initialized standard OpenAI SDK (no automatic trace linking)")
            else:
                # No OpenAI SDK available, will use requests
                self.openai_client = None
                self.logger.info("No OpenAI SDK available, will use HTTP requests")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
    
    def setup_logging(self):
        """Configure logging for this session"""
        # Create logs directory if it doesn't exist
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Configure logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Set up file handler
        log_file = LOGS_DIR / f'session_{self.session_id}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        # Create logger
        self.logger = logging.getLogger(f'GTDCoach.{self.session_id}')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"GTD Coach session started - ID: {self.session_id}")
        
    def load_system_prompt(self):
        """Load the system prompt from Langfuse or fall back to file"""
        prompt_loaded = False
        
        # Try to load from Langfuse first
        if self.langfuse_prompts:
            try:
                # Fetch the main prompt with selected tone
                self.system_prompt = self.langfuse_prompts.get_prompt(
                    "gtd-coach-system",
                    label=self.prompt_tone,
                    cache_ttl_seconds=300  # Cache for 5 minutes
                )
                
                # Also fetch fallback prompt
                self.fallback_prompt = self.langfuse_prompts.get_prompt(
                    "gtd-coach-fallback",
                    label="production",
                    cache_ttl_seconds=300
                )
                
                # Store model configuration from prompt
                self.model_config = self.system_prompt.config
                self.model_name = self.model_config.get("model", MODEL_NAME)
                
                # Initialize with compiled prompt for startup phase
                initial_prompt = self.compile_prompt("STARTUP", time_remaining=30)
                self.messages.append({"role": "system", "content": initial_prompt})
                
                prompt_loaded = True
                self.logger.info(f"Loaded system prompt from Langfuse (tone: {self.prompt_tone})")
                self.logger.info(f"Using model: {self.model_name} from prompt config")
                
            except Exception as e:
                self.logger.warning(f"Failed to load prompts from Langfuse: {e}")
                self.langfuse_prompts = None
        
        # Fall back to local files if Langfuse not available
        if not prompt_loaded:
            # Try simple prompt first, fall back to full prompt
            simple_prompt_file = PROMPTS_DIR / "system-prompt-simple.txt"
            full_prompt_file = PROMPTS_DIR / "system-prompt.txt"
            
            try:
                # Use simple prompt to avoid timeout issues
                if simple_prompt_file.exists():
                    with open(simple_prompt_file, 'r') as f:
                        system_prompt = f.read()
                    self.logger.info("Loaded simple system prompt from file")
                else:
                    with open(full_prompt_file, 'r') as f:
                        system_prompt = f.read()
                    self.logger.info("Loaded full system prompt from file")
                self.messages.append({"role": "system", "content": system_prompt})
                self.logger.info(f"System prompt loaded from file, length: {len(system_prompt)} chars")
                self.model_name = MODEL_NAME  # Use default model
            except FileNotFoundError as e:
                self.logger.error(f"System prompt not found: {e}")
                print(f"Error: System prompt not found")
                sys.exit(1)
    
    def compile_prompt(self, phase_name, time_remaining=None, time_elapsed=0):
        """Compile prompt with dynamic variables"""
        if not self.langfuse_prompts or not hasattr(self, 'system_prompt'):
            return None
        
        try:
            # Get phase instructions from config
            phase_instructions = self.model_config.get("phase_instructions", {}).get(
                phase_name,
                "Guide the user through this phase of the GTD review."
            )
            
            # Get phase time limit from config
            phase_times = self.model_config.get("phase_times", {})
            phase_time_limit = phase_times.get(phase_name, 5)
            
            # Calculate time remaining if not provided
            if time_remaining is None:
                time_remaining = phase_time_limit - time_elapsed
            
            # Compile the prompt with variables
            compiled = self.system_prompt.compile(
                total_time=30,
                phase_name=phase_name,
                phase_time_limit=phase_time_limit,
                time_remaining=max(0, time_remaining),
                time_elapsed=time_elapsed,
                phase_instructions=phase_instructions
            )
            
            # Return the content of the compiled message
            if isinstance(compiled, list) and len(compiled) > 0:
                return compiled[0].get("content", "")
            return compiled
            
        except Exception as e:
            self.logger.warning(f"Failed to compile prompt: {e}")
            return None
    
    def get_time_remaining(self, phase_name):
        """Calculate time remaining for current phase"""
        if not hasattr(self, 'phase_start_times'):
            self.phase_start_times = {}
        
        # Get phase time limit from config or defaults
        if self.langfuse_prompts and hasattr(self, 'model_config'):
            phase_times = self.model_config.get("phase_times", {})
        else:
            phase_times = {
                "STARTUP": 2,
                "MIND_SWEEP": 10,
                "PROJECT_REVIEW": 12,
                "PRIORITIZATION": 5,
                "WRAP_UP": 3
            }
        
        phase_limit = phase_times.get(phase_name.upper(), 5)
        
        # Calculate time elapsed
        if phase_name in self.phase_start_times:
            elapsed = (time.time() - self.phase_start_times[phase_name]) / 60  # Convert to minutes
            return max(0, phase_limit - elapsed)
        
        return phase_limit
    
    def get_time_elapsed(self):
        """Calculate total time elapsed in review"""
        if hasattr(self, 'review_start_time') and self.review_start_time:
            return (time.time() - self.review_start_time.timestamp()) / 60  # Convert to minutes
        return 0
    
    def update_phase_metrics(self, phase_name, metrics):
        """Update phase-specific metrics that will be included in trace metadata"""
        if phase_name not in self.phase_metrics:
            self.phase_metrics[phase_name] = {}
        self.phase_metrics[phase_name].update(metrics)
        self.logger.info(f"Updated metrics for {phase_name}: {metrics}")
    
    def complete_phase(self, phase_name):
        """Update trace metadata with phase completion metrics"""
        metrics = {}
        
        if phase_name == "MIND_SWEEP":
            metrics = {
                "items_captured": len(self.mindsweep_items) if hasattr(self, 'mindsweep_items') else 0,
                "capture_duration": self.review_data.get("phase_durations", {}).get(phase_name, 0)
            }
        elif phase_name == "PROJECT_REVIEW":
            metrics = {
                "projects_reviewed": self.review_data.get("projects_reviewed", 0),
                "decisions_made": self.review_data.get("decisions_made", 0)
            }
        elif phase_name == "PRIORITIZATION":
            if hasattr(self, 'priorities'):
                metrics = {
                    "a_priorities": len([p for p in self.priorities if p.get("priority") == "A"]),
                    "b_priorities": len([p for p in self.priorities if p.get("priority") == "B"]),
                    "c_priorities": len([p for p in self.priorities if p.get("priority") == "C"]),
                    "total_priorities": len(self.priorities)
                }
        elif phase_name == "WRAP_UP" and hasattr(self, 'timing_projects') and self.timing_projects:
            # Add Timing focus metrics if available
            try:
                from gtd_coach.integrations.timing import calculate_focus_score, detect_context_switches
                focus_data = {
                    "focus_score": calculate_focus_score(self.timing_projects),
                    "context_switches": detect_context_switches(self.timing_projects)
                }
                metrics.update(focus_data)
            except Exception as e:
                self.logger.warning(f"Could not calculate Timing metrics: {e}")
        
        if metrics:
            self.update_phase_metrics(phase_name, metrics)
    
    def start_timer(self, minutes, message="Time's up!"):
        """Start a background timer"""
        timer_script = SCRIPTS_DIR / "timer.sh"
        subprocess.Popen([str(timer_script), str(minutes), message])
    
    @observe(name="llm_call", as_type="generation")
    def send_message(self, content, save_to_history=True, phase_name=None):
        """Send a message to the LLM and get response with enhanced retry logic"""
        self.logger.info(f"Sending message to LLM - Phase: {phase_name or 'None'}, Content length: {len(content)} chars")
        
        # Set session context for this trace if Langfuse is enabled
        if self.langfuse_enabled and LANGFUSE_AVAILABLE:
            try:
                from langfuse import get_client
                langfuse = get_client()
                langfuse.update_current_trace(
                    session_id=self.session_id,
                    name=f"gtd_review_{phase_name or 'general'}",
                    metadata={
                        "phase": self.current_phase,
                        "review_session": self.session_id
                    }
                )
            except Exception as e:
                self.logger.debug(f"Failed to update trace context: {e}")
        
        # Track message timing for pattern detection
        message_start_time = time.time()
        
        if save_to_history:
            self.messages.append({"role": "user", "content": content})
            # Record user interaction in memory
            self.loop.create_task(
                self.memory.add_interaction(
                    role="user",
                    content=content,
                    phase=self.current_phase
                )
            )
        
        # Get phase-specific settings from prompt config or use defaults
        temperature = 0.8  # Better for conversational coaching
        max_tokens = 500   # Prevent overly long responses
        
        # Try to use settings from Langfuse prompt config first
        if self.langfuse_prompts and hasattr(self, 'model_config'):
            temperature = self.model_config.get('temperature', temperature)
            max_tokens = self.model_config.get('max_tokens', max_tokens)
        # Fall back to phase-specific settings
        elif phase_name and hasattr(self, 'phase_settings') and phase_name in self.phase_settings:
            settings = self.phase_settings[phase_name]
            temperature = settings.get('temperature', temperature)
            max_tokens = settings.get('max_tokens', max_tokens)
        
        # Update system prompt for current phase if using Langfuse
        if self.langfuse_prompts and phase_name:
            compiled_prompt = self.compile_prompt(
                phase_name,
                time_remaining=self.get_time_remaining(phase_name),
                time_elapsed=self.get_time_elapsed()
            )
            if compiled_prompt:
                # Update the system message with the compiled prompt
                if self.messages and self.messages[0].get('role') == 'system':
                    self.messages[0]['content'] = compiled_prompt
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use current messages for this attempt
                current_messages = self.messages.copy()
                
                # Try to use OpenAI client (with or without Langfuse wrapper)
                if self.openai_client:
                    try:
                        # Build metadata for trace enrichment
                        metadata = {
                            "langfuse_session_id": self.session_id,
                            "langfuse_user_id": self.user_id,  # Weekly profile tracking
                            "langfuse_tags": [
                                f"variant:{self.prompt_tone}" if self.prompt_tone else "variant:unknown",
                                f"week:{self.user_id}",
                                f"phase:{self.current_phase}",
                                "gtd-review"
                            ],
                            # Custom metadata (not prefixed with langfuse_)
                            "phase_name": phase_name or "general",
                            "tone": self.prompt_tone,
                            "attempt": attempt + 1,
                            "review_timestamp": self.session_id
                        }
                        
                        # Add North Star metrics
                        north_star_metrics = self.north_star.get_all_metrics()
                        metadata.update({
                            "memory_relevance_score": north_star_metrics.get("memory_relevance_score", 0.0),
                            "time_to_first_capture": north_star_metrics.get("time_to_first_capture"),
                            "task_followthrough_rate": north_star_metrics.get("task_followthrough_rate", 0.0),
                            "pre_capture_hesitation": north_star_metrics.get("pre_capture_hesitation", 0),
                            "context_switches_per_minute": north_star_metrics.get("context_switches_per_minute", 0.0),
                            "hyperfocus_periods": north_star_metrics.get("hyperfocus_periods", 0),
                            "scatter_periods": north_star_metrics.get("scatter_periods", 0)
                        })
                        
                        # Add experiment tracking (will be set by experiment framework)
                        metadata.update({
                            "experiment_week": self.user_id,  # ISO week format
                            "experiment_variable": getattr(self, "current_experiment_variable", None),
                            "experiment_value": getattr(self, "current_experiment_value", None)
                        })
                        
                        # Add Graphiti batch ID if available
                        if hasattr(self, 'current_graphiti_batch_id') and self.current_graphiti_batch_id:
                            metadata["graphiti_batch_id"] = self.current_graphiti_batch_id
                        
                        # Add Timing session status
                        metadata["timing_session_active"] = self.timing_projects is not None
                        
                        # Add phase-specific metrics if available
                        if self.current_phase in self.phase_metrics:
                            for key, value in self.phase_metrics[self.current_phase].items():
                                metadata[f"phase_{key}"] = value
                        
                        # Build kwargs for OpenAI call
                        openai_kwargs = {
                            "model": self.model_name if hasattr(self, 'model_name') else MODEL_NAME,
                            "messages": current_messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "timeout": 30,
                            "metadata": metadata
                        }
                        
                        # Add prompt linking if using Langfuse OpenAI wrapper and have a prompt
                        if LANGFUSE_OPENAI_AVAILABLE and self.langfuse_prompts and hasattr(self, 'system_prompt'):
                            openai_kwargs["langfuse_prompt"] = self.system_prompt  # Links prompt to trace
                        
                        # Make the API call
                        completion = self.openai_client.chat.completions.create(**openai_kwargs)
                        assistant_message = completion.choices[0].message.content
                        
                    except Exception as e:
                        self.logger.warning(f"OpenAI client call failed, falling back to direct HTTP: {e}")
                        # Fall back to direct HTTP API
                        response = session.post(API_URL, json={
                            "model": self.model_name if hasattr(self, 'model_name') else MODEL_NAME,
                            "messages": current_messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }, timeout=30)
                        response.raise_for_status()
                        assistant_message = response.json()['choices'][0]['message']['content']
                else:
                    # Direct HTTP API call (no OpenAI client available)
                    response = session.post(API_URL, json={
                        "model": self.model_name if hasattr(self, 'model_name') else MODEL_NAME,
                        "messages": current_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }, timeout=30)
                    response.raise_for_status()
                    assistant_message = response.json()['choices'][0]['message']['content']
                
                if save_to_history:
                    self.messages.append({"role": "assistant", "content": assistant_message})
                    
                    # Calculate response metrics
                    response_time = time.time() - message_start_time
                    
                    # Record assistant response in memory
                    self.loop.create_task(
                        self.memory.add_interaction(
                            role="assistant",
                            content=assistant_message,
                            phase=self.current_phase,
                            metrics={
                                "response_time": response_time,
                                "temperature": temperature,
                                "max_tokens": max_tokens
                            }
                        )
                    )
                
                self.logger.info(f"LLM response received - Length: {len(assistant_message)} chars")
                
                # Track interaction for evaluation
                if self.evaluator:
                    interaction_data = {
                        'timestamp': datetime.now().isoformat(),
                        'phase': self.current_phase,
                        'user_input': content,
                        'coach_response': assistant_message,
                        'time_remaining': getattr(self, 'current_phase_time_remaining', None),
                        'experiment_variable': getattr(self, 'current_experiment_variable', None),
                        'retrieved_memories': getattr(self, 'last_retrieved_memories', []),
                        'extracted_tasks': getattr(self, 'last_extracted_tasks', [])
                    }
                    self.interaction_history.append(interaction_data)
                
                # Score the response if Langfuse is enabled
                if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                    response_time = time.time() - message_start_time
                    score_response(self.current_phase, True, response_time, session_id=self.session_id)
                
                return assistant_message
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                print(f"\n⏱️  Timeout on attempt {attempt + 1}/{max_retries}")
                
                if attempt == max_retries - 1:
                    # Final attempt: use simple prompt
                    self.logger.info("Switching to simple prompt for final attempt")
                    print("Switching to simple prompt for final attempt...")
                    simple_prompt_file = PROMPTS_DIR / "system-prompt-simple.txt"
                    if simple_prompt_file.exists():
                        with open(simple_prompt_file, 'r') as f:
                            simple_prompt = f.read()
                        # Replace system prompt temporarily
                        current_messages[0] = {"role": "system", "content": simple_prompt}
                        
                        # Try one more time with simple prompt
                        try:
                            response = session.post(API_URL, json={
                                "model": MODEL_NAME,
                                "messages": current_messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens
                            }, timeout=45)  # Longer timeout for final attempt
                            
                            response.raise_for_status()
                            assistant_message = response.json()['choices'][0]['message']['content']
                            
                            if save_to_history:
                                self.messages.append({"role": "assistant", "content": assistant_message})
                            
                            self.logger.info("Simple prompt attempt succeeded")
                            return assistant_message
                        except Exception as e:
                            self.logger.error(f"Final attempt with simple prompt failed: {e}")
                            print(f"❌ Final attempt failed: {e}")
                
                # Exponential backoff
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error on attempt {attempt + 1}/{max_retries}: {e}")
                print(f"\n❌ Error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error("All retry attempts exhausted")
                    print("Make sure LM Studio server is running (lms server start)")
                    
                    # Score the failure if Langfuse is enabled
                    if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                        response_time = time.time() - message_start_time
                        score_response(self.current_phase, False, response_time, session_id=self.session_id)
                    
                    return None
        
        # Score the failure if we got here
        if self.langfuse_enabled and LANGFUSE_AVAILABLE:
            response_time = time.time() - message_start_time
            score_response(self.current_phase, False, response_time)
        
        return None
    
    async def handle_intervention(self, message: str):
        """
        Handle intervention triggered by real-time pattern detection
        This is called by GraphitiMemory when rapid switching is detected
        
        Args:
            message: Intervention message from the pattern detector
        """
        # Check if interventions are enabled by N-of-1 experiment
        if not self.interventions_enabled:
            self.logger.debug(f"Intervention suggested but disabled: {message}")
            return
        
        # Check cooldown (10 minutes between interventions)
        if self.last_intervention_time:
            time_since_last = time.time() - self.last_intervention_time
            if time_since_last < 600:  # 10 minutes
                self.logger.debug(f"Intervention skipped due to cooldown: {message}")
                return
        
        # Track that we offered an intervention
        self.review_data["interventions_offered"] += 1
        self.last_intervention_time = time.time()
        
        # Offer the intervention to the user
        print(f"\n💭 {message}")
        print("Press Enter for a 30-second grounding exercise, or any other key to continue: ")
        
        try:
            # Get user response with a timeout
            start_time = time.time()
            response = input()
            response_time = time.time() - start_time
            
            if response == "":
                # User accepted the intervention
                self.review_data["interventions_accepted"] += 1
                self.logger.info(f"User accepted intervention after {response_time:.1f}s")
                self.deliver_grounding_exercise()
            else:
                # User skipped the intervention
                self.review_data["interventions_skipped"] += 1
                self.logger.info(f"User skipped intervention after {response_time:.1f}s")
                print("Continuing with review...")
        except Exception as e:
            self.logger.error(f"Error handling intervention: {e}")
    
    def deliver_grounding_exercise(self):
        """
        Deliver the 5-4-3-2-1 grounding exercise
        This helps reduce ADHD-related anxiety and refocus attention
        """
        print("\n🌟 Let's take 30 seconds to ground ourselves...")
        print("\nThis quick exercise will help refocus your attention.")
        print("\n5-4-3-2-1 Grounding Technique:")
        
        exercises = [
            ("5", "Name 5 things you can SEE around you"),
            ("4", "Notice 4 things you can TOUCH"),
            ("3", "Listen for 3 things you can HEAR"),
            ("2", "Identify 2 things you can SMELL"),
            ("1", "Notice 1 thing you can TASTE")
        ]
        
        for number, instruction in exercises:
            print(f"\n{number}: {instruction}")
            time.sleep(5)  # Give 5 seconds for each sense
        
        print("\n✨ Great job! You're now more grounded and focused.")
        print("Let's continue with your review...\n")
        
        # Log completion
        self.logger.info("Grounding exercise completed")
    
    def phase_timer(self, phase_name, duration_minutes):
        """Track phase duration"""
        phase_start = time.time()
        self.start_timer(duration_minutes, f"{phase_name} phase complete!")
        self.logger.info(f"Starting phase: {phase_name} ({duration_minutes} minutes)")
        
        # Store phase start time for prompt compilation
        if not hasattr(self, 'phase_start_times'):
            self.phase_start_times = {}
        self.phase_start_times[phase_name.upper()] = phase_start
        
        # Record phase start in memory
        self.current_phase = phase_name.upper().replace(" ", "_")
        self.loop.create_task(self.memory.add_phase_transition(phase_name, "start"))
        
        return phase_start
    
    def end_phase(self, phase_name, phase_start):
        """Record phase completion"""
        duration = time.time() - phase_start
        self.review_data["phase_durations"][phase_name] = duration
        self.logger.info(f"Phase completed: {phase_name} - Duration: {duration/60:.1f} minutes")
        print(f"\n✓ {phase_name} completed in {duration/60:.1f} minutes")
        
        # Capture phase metrics for trace enrichment
        self.complete_phase(phase_name.upper().replace(" ", "_"))
        
        # Record phase end and flush episodes
        self.loop.create_task(self.memory.add_phase_transition(phase_name, "end", duration))
        self.loop.create_task(self.memory.flush_episodes())
    
    def run_startup_phase(self):
        """1. STARTUP PHASE (2 min)"""
        print("\n" + "="*50)
        print("GTD WEEKLY REVIEW - ADHD COACH")
        print("="*50)
        
        phase_start = self.phase_timer("Startup", 2)
        self.review_start_time = datetime.now()
        
        # Initialize Graphiti memory connection
        self.logger.info("Initializing Graphiti memory...")
        try:
            self.loop.run_until_complete(self.memory.initialize())
        except Exception as e:
            self.logger.warning(f"Failed to initialize Graphiti: {e}")
            # Continue anyway with JSON backup
        
        # Load and display pre-computed context (instant, zero-friction)
        if self.memory_patterns:
            context = self.memory_patterns.load_context()
        else:
            context = None
        if context and context.get('patterns'):
            print("\n💭 On your mind lately:")
            for pattern in context['patterns'][:3]:  # Show top 3 patterns
                print(f"   • {pattern['pattern']} (seen {pattern['weeks_seen']} weeks)")
            print()  # Add spacing
        
        # Start fetching Timing data asynchronously if configured
        if self.timing_api.is_configured():
            self.logger.info("Starting async fetch of Timing project data")
            min_minutes = int(os.getenv('TIMING_MIN_MINUTES', '30'))
            self.timing_fetch_task = self.loop.create_task(
                self.timing_api.fetch_projects_async(min_minutes)
            )
            print("\n📊 Fetching your project data from Timing...")
        else:
            self.logger.info("Timing API not configured, will use mock data")
            if not os.path.exists('.env'):
                print("\n💡 Tip: Set up Timing integration for real project data")
                print("   Copy .env.example to .env and add your API key")
        
        # Initial greeting
        response = self.send_message("Start the weekly review process.", phase_name='STARTUP')
        print(f"\nCoach: {response}")
        
        # Complete async fetch if it was started
        if self.timing_fetch_task:
            try:
                # Wait for fetch to complete (with timeout)
                self.timing_projects = self.loop.run_until_complete(
                    asyncio.wait_for(self.timing_fetch_task, timeout=2.0)
                )
                if self.timing_projects:
                    self.logger.info(f"Successfully fetched {len(self.timing_projects)} projects from Timing")
                    print(f"✓ Loaded {len(self.timing_projects)} projects from last week")
                else:
                    self.logger.warning("No projects returned from Timing API")
            except asyncio.TimeoutError:
                self.logger.warning("Timing API fetch timed out, will use mock data")
                print("⚠️  Timing data fetch timed out, using backup data")
            except Exception as e:
                self.logger.error(f"Error fetching Timing data: {e}")
                print("⚠️  Could not fetch Timing data, using backup data")
        
        self.end_phase("Startup", phase_start)
    
    def run_mindsweep_phase(self):
        """2. MIND SWEEP PHASE (10 min)"""
        print("\n" + "-"*50)
        print("MIND SWEEP PHASE (10 minutes total)")
        print("-"*50)
        
        phase_start = self.phase_timer("Mind Sweep", 10)
        
        # Phase A: Initial Capture (5 minutes)
        print("\n📝 Phase A: CAPTURE (5 minutes)")
        print("Write down everything on your mind.")
        print("(Press Enter with empty line to finish early)\n")
        items = []
        item_timestamps = []  # Track when each item was entered
        previous_item = None
        
        capture_start = time.time()
        last_progress_update = 0
        
        while True:
            elapsed = time.time() - capture_start
            
            # Check if 5 minutes have passed
            if elapsed >= 300:  # 5 minutes
                print("\n⏰ Capture time complete! Press Enter to continue to processing phase...")
                # Wait for final input to avoid jarring interruption
                try:
                    final_input = input()
                    if final_input.strip():
                        items.append(final_input.strip())
                        self.review_data["items_captured"] += 1
                except KeyboardInterrupt:
                    pass
                break
            
            # Visual progress indicators every minute
            current_minute = int(elapsed // 60)
            if current_minute > last_progress_update and current_minute < 5:
                remaining = 5 - current_minute
                print(f"\n⏱️  {current_minute} minute{'s' if current_minute > 1 else ''} elapsed, {remaining} minute{'s' if remaining > 1 else ''} remaining")
                last_progress_update = current_minute
            
            # Warning at 4 minutes
            if elapsed >= 240 and elapsed < 241:
                print("\n⚠️  1 minute remaining for capture!")
            
            try:
                # Use a prompt that doesn't repeat
                prompt = "> " if not items or (elapsed < 10) else ""
                item = input(prompt)
                
                # Handle empty line - offer to exit early
                if not item.strip():
                    confirm = input("Finish capture early? (y/n): ")
                    if confirm.lower() == 'y':
                        print("✓ Moving to processing phase...")
                        break
                    else:
                        continue  # Continue capturing
                        
                items.append(item.strip())
                item_timestamps.append(time.time())
                self.review_data["items_captured"] += 1
                
                # Track time to first capture for North Star metrics
                if len(items) == 1:
                    self.north_star.measure_time_to_insight(datetime.now())
                
                # Detect task switching pattern
                if previous_item:
                    time_between = item_timestamps[-1] - item_timestamps[-2] if len(item_timestamps) > 1 else None
                    switch_data = self.pattern_detector.detect_task_switching(
                        item.strip(), previous_item, time_between
                    )
                    
                    if switch_data:
                        self.loop.create_task(
                            self.memory.add_behavior_pattern(
                                pattern_type="task_switch",
                                phase="MIND_SWEEP",
                                pattern_data=switch_data
                            )
                        )
                
                previous_item = item.strip()
                
            except KeyboardInterrupt:
                print("\n✓ Capture phase ended by user")
                break
            except EOFError:
                break
        
        # Phase B: Quick Process (5 minutes)
        print(f"\n📋 Phase B: PROCESS (5 minutes)")
        print(f"You captured {len(items)} items. Let's process them quickly.")
        
        # Always display captured items first
        print("\n📝 Your captured items:")
        for i, item in enumerate(items, 1):
            print(f"{i}. {item}")
        
        process_start = time.time()
        
        # Send full context to coach with clear phase boundaries
        items_context = f"""We are in MIND SWEEP Phase B (Processing). We have 5 minutes for this processing phase.
I captured {len(items)} items during the 5-minute capture phase:

{chr(10).join(f"{i}. {item}" for i, item in enumerate(items, 1))}

Please help me quickly process and organize these items. Stay within the Mind Sweep phase - we are NOT in Project Review yet."""
        
        if len(items) > 15:
            items_context += "\n\nNote: I have more than 15 items, so we'll need to prioritize the most important ones."
        
        response = self.send_message(items_context, phase_name='MIND_SWEEP')
        print(f"\nCoach: {response}")
        
        # If too many items, quick prioritization
        if len(items) > 15:
            print(f"\n🎯 You have {len(items)} items. Let's quickly identify your top 10-15.")
            print("Type the numbers of your most important items (comma-separated):")
            print("\nYour items:")
            for i, item in enumerate(items, 1):
                print(f"{i}. {item}")
            
            try:
                # Set a reasonable timeout for selection
                selection_input = input("\nTop items (e.g., 1,3,5,7): ")
                if selection_input.strip():
                    selected_indices = [int(x.strip()) - 1 for x in selection_input.split(',') 
                                      if x.strip().isdigit() and 0 < int(x.strip()) <= len(items)]
                    if selected_indices:
                        priority_items = [items[i] for i in selected_indices[:15]]  # Cap at 15
                        print(f"\n✓ Focusing on {len(priority_items)} priority items")
                    else:
                        priority_items = items[:15]
                        print("\n✓ Using first 15 items")
                else:
                    priority_items = items[:15]
                    print("\n✓ Using first 15 items")
            except (ValueError, KeyboardInterrupt):
                priority_items = items[:15]
                print("\n✓ Using first 15 items")
        else:
            priority_items = items
        
        # Quick clarification opportunity
        remaining_process_time = 300 - (time.time() - process_start)  # 5 minutes for process phase
        if remaining_process_time > 60 and len(priority_items) > 0:
            print(f"\n💭 Any items need quick clarification? ({int(remaining_process_time/60)} minutes remaining)")
            print("(Type item number and clarification, or press Enter to skip)")
            
            # Display the items we're working with
            print("\n📝 Items to process:")
            for i, item in enumerate(priority_items, 1):
                print(f"{i}. {item}")
            
            # Allow a few quick clarifications
            clarification_count = 0
            while clarification_count < 3 and (time.time() - process_start) < 240:  # Max 3 clarifications, 4 min limit
                try:
                    clarify_input = input("\n> ")
                    if not clarify_input.strip():
                        break
                    # Simple parsing: "3 - needs to call by Friday"
                    parts = clarify_input.split(' ', 1)
                    if len(parts) >= 2 and parts[0].isdigit():
                        item_num = int(parts[0]) - 1
                        if 0 <= item_num < len(priority_items):
                            # Just acknowledge, don't modify items
                            print(f"✓ Noted clarification for item {item_num + 1}")
                            clarification_count += 1
                except (ValueError, KeyboardInterrupt):
                    break
        
        # Analyze patterns before saving
        final_items = priority_items if len(items) > 15 else items
        coherence_analysis = self.pattern_detector.analyze_mindsweep_coherence(final_items)
        
        # Store items for pattern detection in wrap-up
        self.mindsweep_items = final_items
        
        # Calculate capture phase metrics
        capture_duration = time.time() - capture_start
        phase_metrics = {
            "capture_duration_seconds": capture_duration,
            "items_per_minute": len(items) / (capture_duration / 60),
            "coherence_analysis": coherence_analysis
        }
        
        # Add mindsweep data to memory with pattern analysis
        self.loop.create_task(
            self.memory.add_mindsweep_batch(final_items, phase_metrics)
        )
        
        # Log coherence patterns if concerning
        if coherence_analysis['coherence_score'] < 0.5:
            self.loop.create_task(
                self.memory.add_behavior_pattern(
                    pattern_type="low_coherence",
                    phase="MIND_SWEEP",
                    pattern_data={
                        "score": coherence_analysis['coherence_score'],
                        "topic_switches": coherence_analysis['topic_switches'],
                        "fragmentation_count": len(coherence_analysis['fragmentation_indicators'])
                    }
                )
            )
        
        # Save items for later processing
        self.save_mindsweep_items(final_items)
        
        # Final coach encouragement with phase context
        final_summary = f"""We are completing MIND SWEEP Phase B.
We successfully processed {len(priority_items)} items:

{chr(10).join(f"{i}. {item}" for i, item in enumerate(priority_items, 1))}

Mind sweep phase is now complete. Please provide encouragement and prepare me for the next phase (Project Review)."""
        
        response = self.send_message(final_summary, phase_name='MIND_SWEEP')
        print(f"\nCoach: {response}")
        
        self.end_phase("Mind Sweep", phase_start)
    
    def run_project_review_phase(self):
        """3. PROJECT REVIEW PHASE (12 min)"""
        print("\n" + "-"*50)
        print("PROJECT REVIEW PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Project Review", 12)
        
        # Load projects (mock data for now)
        projects = self.load_projects()
        
        for i, project in enumerate(projects[:10]):  # Max 10 projects
            print(f"\n[{i+1}/10] Project: {project['name']}")
            print(f"Last week time: {project['time_spent']} hours")
            
            # Get next action
            decision_start = time.time()
            next_action = input("Next action (45 sec): ")
            decision_time = time.time() - decision_start
            
            if decision_time < 45 and next_action.strip():
                self.review_data["decisions_made"] += 1
                self.review_data["projects_reviewed"] += 1
                print("✓ Recorded")
            else:
                print("⏱️  Time's up - marked for clarification")
            
            # Coach feedback
            if i == 4:  # Halfway check
                response = self.send_message("I'm halfway through project review. Maintaining pace.", phase_name='PROJECT_REVIEW')
                print(f"\nCoach: {response}")
        
        self.end_phase("Project Review", phase_start)
    
    def run_prioritization_phase(self):
        """4. NEXT ACTIONS PRIORITIZATION (5 min)"""
        print("\n" + "-"*50)
        print("PRIORITIZATION PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Prioritization", 5)
        
        # Get coach's prioritization guidance
        response = self.send_message("Guide me through prioritizing my next actions based on the review.", phase_name='PRIORITIZATION')
        print(f"\nCoach: {response}")
        
        # Quick ABC prioritization
        priorities = []
        for i in range(5):
            action = input(f"\nAction {i+1}: ")
            if action.strip():
                priority_input = input("Priority (A/B/C): ")
                # Validate priority
                priority = validate_priority(priority_input)
                priorities.append({"action": action.strip(), "priority": priority})
        
        self.save_priorities(priorities)
        self.priorities = priorities  # Store for wrap-up phase
        
        # Show time comparison if we have Timing data
        if self.timing_projects:
            time_summary = generate_simple_time_summary(self.timing_projects)
            if time_summary:
                print(time_summary)
        
        # Compare priorities with actual time spent
        comparison = compare_time_with_priorities(priorities)
        if comparison:
            print(comparison)
        
        self.end_phase("Prioritization", phase_start)
    
    def run_wrapup_phase(self):
        """5. WRAP-UP PHASE (3 min)"""
        print("\n" + "-"*50)
        print("WRAP-UP PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Wrap-up", 3)
        
        # Analyze timing patterns if available
        timing_analysis = None
        if self.timing_api.is_configured():
            try:
                # Get detailed timing analysis
                timing_analysis = self.loop.run_until_complete(
                    self.timing_api.analyze_timing_patterns_async()
                )
                
                if timing_analysis and timing_analysis.get('focus_metrics'):
                    # Store in memory
                    adhd_analysis = self.pattern_detector.analyze_timing_switches(timing_analysis)
                    
                    self.loop.create_task(
                        self.memory.add_timing_analysis(timing_analysis, adhd_analysis)
                    )
                    
                    # Show focus score
                    focus_score = timing_analysis['focus_metrics'].get('focus_score', 0)
                    print(f"\n📊 Your Focus Score: {focus_score}/100")
                    print(f"   ({timing_analysis['focus_metrics'].get('interpretation', '')})")
                    
                    # Compare with priorities
                    if self.priorities and timing_analysis.get('projects'):
                        comparison = compare_time_with_priorities(
                            timing_analysis['projects'],
                            self.priorities,
                            timing_analysis
                        )
                        
                        # Show alignment
                        alignment = comparison.get('alignment_score', 0)
                        emoji = "✅" if alignment > 70 else "⚠️" if alignment > 40 else "❌"
                        print(f"\n{emoji} Priority Alignment: {alignment:.0f}%")
                        
                        # Store comparison
                        self.review_data['timing_comparison'] = comparison
                        self.review_data['timing_analysis'] = timing_analysis
            
            except Exception as e:
                self.logger.error(f"Failed to analyze timing patterns: {e}")
        
        # Generate summary
        total_time = (datetime.now() - self.review_start_time).total_seconds() / 60
        
        summary = f"""Review completed in {total_time:.1f} minutes.
Projects reviewed: {self.review_data['projects_reviewed']}
Decisions made: {self.review_data['decisions_made']}  
Items captured: {self.review_data['items_captured']}"""
        
        response = self.send_message(f"Wrap up the review with these metrics: {summary}", phase_name='WRAP_UP')
        print(f"\nCoach: {response}")
        
        # Save review log
        self.save_review_log()
        
        # Show time adjustment suggestion if we have data
        if timing_analysis and self.priorities:
            comparison = self.review_data.get('timing_comparison', {})
            suggestion = suggest_time_adjustments(comparison, self.priorities)
            if suggestion:
                print(suggestion)
        
        # Pre-compute patterns for next session (runs in background)
        print("\n📋 Analyzing patterns for next session...")
        try:
            # Find recurring patterns from recent sessions
            patterns = self.memory_patterns.find_recurring_patterns(weeks_back=4)
            
            # Generate insights from current session
            insights = self.memory_patterns.get_simple_insights(self.mindsweep_items)
            
            # Save context for next session
            next_context = {
                'patterns': patterns,
                'last_session': self.session_id,
                'last_insights': insights,
                'timestamp': datetime.now().isoformat()
            }
            self.memory_patterns.save_context(next_context)
            
            if patterns:
                self.logger.info(f"Found {len(patterns)} recurring patterns for next session")
            
        except Exception as e:
            self.logger.warning(f"Failed to pre-compute patterns: {e}")
            # Not critical - continue without patterns
        
        self.end_phase("Wrap-up", phase_start)
        
        print("\n🎉 REVIEW COMPLETE! Great job showing up!")
    
    def save_mindsweep_items(self, items):
        """Save captured items to file"""
        # Validate items first
        validated_items = validate_mindsweep_items(items)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"mindsweep_{timestamp}.json"
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "items": validated_items,
                "count": len(validated_items)
            }, f, indent=2)
        
        self.logger.info(f"Saved {len(validated_items)} mindsweep items to {filepath.name}")
    
    def load_projects(self):
        """Load project list from Timing API or use mock data"""
        # Use pre-fetched Timing data if available
        if self.timing_projects:
            self.logger.info(f"Using {len(self.timing_projects)} projects from Timing API")
            
            # Check if projects look auto-generated and provide guidance
            app_names = ['Safari', 'Chrome', 'Mail', 'Slack', 'Terminal', 'Code']
            auto_generated = [p for p in self.timing_projects 
                            if any(app in p['name'] for app in app_names)]
            
            if len(auto_generated) > len(self.timing_projects) * 0.5:
                print("\n💡 Project Organization Tip:")
                print("   Many of your projects appear to be app names.")
                print("   Consider creating specific projects in Timing for better GTD reviews.")
                print("   Example: Instead of 'Safari', create 'Research - Project X'\n")
            
            return self.timing_projects
        
        # Fallback to mock data
        self.logger.info("Using mock project data (Timing API not available)")
        return get_mock_projects()
    
    def save_priorities(self, priorities):
        """Save prioritized actions"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"priorities_{timestamp}.json"
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "priorities": priorities
            }, f, indent=2)
        
        self.logger.info(f"Saved {len(priorities)} priorities to {filepath.name}")
    
    def save_review_log(self):
        """Save complete review log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = LOGS_DIR / f"review_{timestamp}.json"
        
        # Ensure logs directory exists
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create session data and validate
        session_data = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "review_data": self.review_data,
            "messages": self.messages[1:]  # Exclude system prompt
        }
        validated_data = validate_session_data(session_data)
        
        # Save North Star metrics
        self.north_star.save_metrics()
        
        with open(filepath, 'w') as f:
            json.dump(validated_data, f, indent=2)
        
        # Create session summary in memory with timing data
        timing_data = self.review_data.get('timing_analysis')
        self.loop.create_task(self.memory.create_session_summary(self.review_data, timing_data))
        
        # Run all pending async tasks before saving
        pending = [task for task in asyncio.all_tasks(self.loop) if not task.done()]
        if pending:
            self.loop.run_until_complete(asyncio.gather(*pending))
        
        self.logger.info(f"Saved complete review log to {filepath.name}")
        self.logger.info(f"Session summary: {self.review_data}")

# Data validation functions
def validate_mindsweep_items(items):
    """Validate and clean mindsweep items"""
    if not isinstance(items, list):
        logging.warning("Mindsweep items must be a list")
        return []
    
    # Clean and validate each item
    validated = []
    for item in items:
        if item and isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                validated.append(cleaned)
    
    return validated

def validate_priority(priority):
    """Validate priority value"""
    if not priority or not isinstance(priority, str):
        return 'C'  # Default to C priority
    
    priority = priority.upper().strip()
    if priority in ['A', 'B', 'C']:
        return priority
    else:
        logging.warning(f"Invalid priority '{priority}', defaulting to 'C'")
        return 'C'

def validate_session_data(data):
    """Ensure session data has required fields"""
    required_fields = {
        'session_id': None,
        'timestamp': None,
        'review_data': {},
        'messages': []
    }
    
    if not isinstance(data, dict):
        return required_fields
    
    # Ensure all required fields exist
    for field, default in required_fields.items():
        if field not in data:
            data[field] = default
            logging.warning(f"Missing required field '{field}' in session data")
    
    return data

def check_server():
    """Check if LM Studio server is running and accessible"""
    try:
        # Try to get models list
        response = session.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code != 200:
            return False, "Server returned non-200 status code"
        
        # Check if any models are loaded
        models_data = response.json()
        if 'data' in models_data and len(models_data['data']) > 0:
            return True, f"Server running with {len(models_data['data'])} model(s) loaded"
        else:
            return False, "Server running but no models loaded"
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to LM Studio server"
    except requests.exceptions.Timeout:
        return False, "Server request timed out"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def main():
    """Main entry point"""
    print("GTD Weekly Review Coach for ADHD")
    print("================================")
    
    # Check prerequisites
    server_ok, server_message = check_server()
    if not server_ok:
        print(f"\n❌ LM Studio server check failed: {server_message}")
        print("\nTo fix this:")
        print("1. Start LM Studio server: lms server start")
        print("2. Load the model: lms load meta-llama-3.1-8b-instruct")
        sys.exit(1)
    
    print(f"\n✓ {server_message}")
    
    # Confirm ready
    input("\nPress Enter when ready to start your 30-minute review...")
    
    # Run the review
    coach = GTDCoach()
    
    try:
        coach.run_startup_phase()
        coach.run_mindsweep_phase()
        coach.run_project_review_phase()
        coach.run_prioritization_phase()
        coach.run_wrapup_phase()
        
        # Trigger post-session evaluation (fire-and-forget)
        if coach.evaluator and coach.interaction_history:
            print("\n📊 Queueing session evaluation...")
            session_data = {
                'session_id': coach.session_id,
                'interactions': coach.interaction_history,
                'duration': (datetime.now() - coach.review_start_time).total_seconds() / 60,
                'review_data': coach.review_data,
                'north_star_metrics': coach.north_star.get_all_metrics() if hasattr(coach, 'north_star') else {}
            }
            coach.evaluator.evaluate_session(session_data)
            coach.logger.info("Post-session evaluation queued")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Review interrupted")
        coach.save_review_log()
        print("Progress saved.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        coach.save_review_log()
        print("Progress saved.")

if __name__ == "__main__":
    main()