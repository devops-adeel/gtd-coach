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
from datetime import datetime
from pathlib import Path

# Import memory integration modules
from graphiti_integration import GraphitiMemory
from adhd_patterns import ADHDPatternDetector

# Configuration
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama-3.1-8b-instruct"  # Actual model name for API
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
        # Set up logging
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.setup_logging()
        
        self.messages = []
        self.review_start_time = None
        self.review_data = {
            "projects_reviewed": 0,
            "decisions_made": 0,
            "items_captured": 0,
            "phase_durations": {}
        }
        
        # Initialize memory and pattern detection
        self.memory = GraphitiMemory(self.session_id)
        self.pattern_detector = ADHDPatternDetector()
        self.current_phase = "STARTUP"
        
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
        
        self.load_system_prompt()
    
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
        """Load the system prompt from file"""
        # Try simple prompt first, fall back to full prompt
        simple_prompt_file = PROMPTS_DIR / "system-prompt-simple.txt"
        full_prompt_file = PROMPTS_DIR / "system-prompt.txt"
        
        try:
            # Use simple prompt to avoid timeout issues
            if simple_prompt_file.exists():
                with open(simple_prompt_file, 'r') as f:
                    system_prompt = f.read()
                self.logger.info("Loaded simple system prompt")
            else:
                with open(full_prompt_file, 'r') as f:
                    system_prompt = f.read()
                self.logger.info("Loaded full system prompt")
            self.messages.append({"role": "system", "content": system_prompt})
            self.logger.info(f"System prompt loaded, length: {len(system_prompt)} chars")
        except FileNotFoundError as e:
            self.logger.error(f"System prompt not found: {e}")
            print(f"Error: System prompt not found")
            sys.exit(1)
    
    def start_timer(self, minutes, message="Time's up!"):
        """Start a background timer"""
        timer_script = SCRIPTS_DIR / "timer.sh"
        subprocess.Popen([str(timer_script), str(minutes), message])
    
    def send_message(self, content, save_to_history=True, phase_name=None):
        """Send a message to the LLM and get response with enhanced retry logic"""
        self.logger.info(f"Sending message to LLM - Phase: {phase_name or 'None'}, Content length: {len(content)} chars")
        
        # Track message timing for pattern detection
        message_start_time = time.time()
        
        if save_to_history:
            self.messages.append({"role": "user", "content": content})
            # Record user interaction in memory
            asyncio.create_task(
                self.memory.add_interaction(
                    role="user",
                    content=content,
                    phase=self.current_phase
                )
            )
        
        # Get phase-specific settings or use defaults
        temperature = 0.8  # Better for conversational coaching
        max_tokens = 500   # Prevent overly long responses
        
        if phase_name and hasattr(self, 'phase_settings') and phase_name in self.phase_settings:
            settings = self.phase_settings[phase_name]
            temperature = settings.get('temperature', temperature)
            max_tokens = settings.get('max_tokens', max_tokens)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use current messages for this attempt
                current_messages = self.messages.copy()
                
                response = session.post(API_URL, json={
                    "model": MODEL_NAME,
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
                    asyncio.create_task(
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
                    return None
        
        return None
    
    def phase_timer(self, phase_name, duration_minutes):
        """Track phase duration"""
        phase_start = time.time()
        self.start_timer(duration_minutes, f"{phase_name} phase complete!")
        self.logger.info(f"Starting phase: {phase_name} ({duration_minutes} minutes)")
        
        # Record phase start in memory
        self.current_phase = phase_name.upper().replace(" ", "_")
        asyncio.create_task(self.memory.add_phase_transition(phase_name, "start"))
        
        return phase_start
    
    def end_phase(self, phase_name, phase_start):
        """Record phase completion"""
        duration = time.time() - phase_start
        self.review_data["phase_durations"][phase_name] = duration
        self.logger.info(f"Phase completed: {phase_name} - Duration: {duration/60:.1f} minutes")
        print(f"\n✓ {phase_name} completed in {duration/60:.1f} minutes")
        
        # Record phase end and flush episodes
        asyncio.create_task(self.memory.add_phase_transition(phase_name, "end", duration))
        asyncio.create_task(self.memory.flush_episodes())
    
    def run_startup_phase(self):
        """1. STARTUP PHASE (2 min)"""
        print("\n" + "="*50)
        print("GTD WEEKLY REVIEW - ADHD COACH")
        print("="*50)
        
        phase_start = self.phase_timer("Startup", 2)
        self.review_start_time = datetime.now()
        
        # Initial greeting
        response = self.send_message("Start the weekly review process.", phase_name='STARTUP')
        print(f"\nCoach: {response}")
        
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
                
                # Detect task switching pattern
                if previous_item:
                    time_between = item_timestamps[-1] - item_timestamps[-2] if len(item_timestamps) > 1 else None
                    switch_data = self.pattern_detector.detect_task_switching(
                        item.strip(), previous_item, time_between
                    )
                    
                    if switch_data:
                        asyncio.create_task(
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
        
        # Calculate capture phase metrics
        capture_duration = time.time() - capture_start
        phase_metrics = {
            "capture_duration_seconds": capture_duration,
            "items_per_minute": len(items) / (capture_duration / 60),
            "coherence_analysis": coherence_analysis
        }
        
        # Add mindsweep data to memory with pattern analysis
        asyncio.create_task(
            self.memory.add_mindsweep_batch(final_items, phase_metrics)
        )
        
        # Log coherence patterns if concerning
        if coherence_analysis['coherence_score'] < 0.5:
            asyncio.create_task(
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
        self.end_phase("Prioritization", phase_start)
    
    def run_wrapup_phase(self):
        """5. WRAP-UP PHASE (3 min)"""
        print("\n" + "-"*50)
        print("WRAP-UP PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Wrap-up", 3)
        
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
        """Load project list (mock data for now)"""
        # In real implementation, load from Timing app export or saved data
        return [
            {"name": "Email Processing", "time_spent": 5.2},
            {"name": "Project Alpha Development", "time_spent": 12.5},
            {"name": "Team Meetings", "time_spent": 8.3},
            {"name": "Documentation", "time_spent": 3.1},
            {"name": "Code Reviews", "time_spent": 6.7},
        ]
    
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
        
        with open(filepath, 'w') as f:
            json.dump(validated_data, f, indent=2)
        
        # Create session summary in memory
        asyncio.create_task(self.memory.create_session_summary(self.review_data))
        
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