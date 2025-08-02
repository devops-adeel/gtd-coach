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
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama-3.1-8b-instruct"  # Actual model name for API
COACH_DIR = Path.home() / "gtd-coach"
PROMPTS_DIR = COACH_DIR / "prompts"
DATA_DIR = COACH_DIR / "data" 
LOGS_DIR = COACH_DIR / "logs"
SCRIPTS_DIR = COACH_DIR / "scripts"

class GTDCoach:
    def __init__(self):
        self.messages = []
        self.review_start_time = None
        self.review_data = {
            "projects_reviewed": 0,
            "decisions_made": 0,
            "items_captured": 0,
            "phase_durations": {}
        }
        self.load_system_prompt()
        
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
            else:
                with open(full_prompt_file, 'r') as f:
                    system_prompt = f.read()
            self.messages.append({"role": "system", "content": system_prompt})
        except FileNotFoundError:
            print(f"Error: System prompt not found")
            sys.exit(1)
    
    def start_timer(self, minutes, message="Time's up!"):
        """Start a background timer"""
        timer_script = SCRIPTS_DIR / "timer.sh"
        subprocess.Popen([str(timer_script), str(minutes), message])
    
    def send_message(self, content, save_to_history=True):
        """Send a message to the LLM and get response"""
        if save_to_history:
            self.messages.append({"role": "user", "content": content})
        
        try:
            response = requests.post(API_URL, json={
                "model": MODEL_NAME,
                "messages": self.messages,
                "temperature": 0.3,
                "max_tokens": 2048
            }, timeout=30)
            
            response.raise_for_status()
            assistant_message = response.json()['choices'][0]['message']['content']
            
            if save_to_history:
                self.messages.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with LM Studio: {e}")
            print("Make sure LM Studio server is running (lms server start)")
            return None
    
    def phase_timer(self, phase_name, duration_minutes):
        """Track phase duration"""
        phase_start = time.time()
        self.start_timer(duration_minutes, f"{phase_name} phase complete!")
        return phase_start
    
    def end_phase(self, phase_name, phase_start):
        """Record phase completion"""
        duration = time.time() - phase_start
        self.review_data["phase_durations"][phase_name] = duration
        print(f"\n✓ {phase_name} completed in {duration/60:.1f} minutes")
    
    def run_startup_phase(self):
        """1. STARTUP PHASE (2 min)"""
        print("\n" + "="*50)
        print("GTD WEEKLY REVIEW - ADHD COACH")
        print("="*50)
        
        phase_start = self.phase_timer("Startup", 2)
        self.review_start_time = datetime.now()
        
        # Initial greeting
        response = self.send_message("Start the weekly review process.")
        print(f"\nCoach: {response}")
        
        self.end_phase("Startup", phase_start)
    
    def run_mindsweep_phase(self):
        """2. MIND SWEEP PHASE (10 min)"""
        print("\n" + "-"*50)
        print("MIND SWEEP PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Mind Sweep", 10)
        
        # Capture items
        print("\nWrite down everything on your mind (5 minutes):")
        items = []
        
        # Simulate 5-minute capture with periodic reminders
        capture_start = time.time()
        while time.time() - capture_start < 300:  # 5 minutes
            try:
                item = input("> ")
                if item.strip():
                    items.append(item.strip())
                    self.review_data["items_captured"] += 1
            except KeyboardInterrupt:
                break
                
            # Check time warnings
            elapsed = time.time() - capture_start
            if elapsed >= 240 and elapsed < 241:  # 4 minutes
                print("\n⚠️  1 minute remaining for capture!")
        
        # Process with coach
        items_summary = f"I captured {len(items)} items during mind sweep."
        if len(items) > 15:
            items_summary += " This seems like too many for one session."
        
        response = self.send_message(items_summary)
        print(f"\nCoach: {response}")
        
        # Save items for later processing
        self.save_mindsweep_items(items)
        
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
                response = self.send_message("I'm halfway through project review. Maintaining pace.")
                print(f"\nCoach: {response}")
        
        self.end_phase("Project Review", phase_start)
    
    def run_prioritization_phase(self):
        """4. NEXT ACTIONS PRIORITIZATION (5 min)"""
        print("\n" + "-"*50)
        print("PRIORITIZATION PHASE")
        print("-"*50)
        
        phase_start = self.phase_timer("Prioritization", 5)
        
        # Get coach's prioritization guidance
        response = self.send_message("Guide me through prioritizing my next actions based on the review.")
        print(f"\nCoach: {response}")
        
        # Quick ABC prioritization
        priorities = []
        for i in range(5):
            action = input(f"\nAction {i+1}: ")
            if action.strip():
                priority = input("Priority (A/B/C): ").upper()
                priorities.append({"action": action, "priority": priority})
        
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
        
        response = self.send_message(f"Wrap up the review with these metrics: {summary}")
        print(f"\nCoach: {response}")
        
        # Save review log
        self.save_review_log()
        
        self.end_phase("Wrap-up", phase_start)
        
        print("\n🎉 REVIEW COMPLETE! Great job showing up!")
    
    def save_mindsweep_items(self, items):
        """Save captured items to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"mindsweep_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "items": items,
                "count": len(items)
            }, f, indent=2)
    
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
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "priorities": priorities
            }, f, indent=2)
    
    def save_review_log(self):
        """Save complete review log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = LOGS_DIR / f"review_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "review_data": self.review_data,
                "messages": self.messages[1:]  # Exclude system prompt
            }, f, indent=2)

def check_server():
    """Check if LM Studio server is running"""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Main entry point"""
    print("GTD Weekly Review Coach for ADHD")
    print("================================")
    
    # Check prerequisites
    if not check_server():
        print("\n❌ LM Studio server is not running!")
        print("Please run: lms server start")
        print("Then load a model: lms load meta-llama-3.1-8b-instruct")
        sys.exit(1)
    
    print("\n✓ LM Studio server is running")
    
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