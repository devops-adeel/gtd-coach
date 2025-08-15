#!/usr/bin/env python3
"""
Demo GTD Review - Shows the coach in action
"""

import requests
import json
import time
from datetime import datetime

def send_message(messages):
    """Send message to LLM and return response"""
    response = requests.post("http://localhost:1234/v1/chat/completions", 
        json={
            "model": "xlam-7b-fc-r",  # Using xLAM function calling model
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 300
        }, 
        timeout=10)
    
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def main():
    print("GTD Coach Demo - Interactive Review Simulation")
    print("=" * 60)
    print("\nThis demo simulates a GTD review session with the ADHD coach.")
    print("In a real session, you would interact with the coach.\n")
    
    # Simple system prompt
    messages = [{
        "role": "system", 
        "content": """You are an ADHD-specialized GTD coach. Be direct, time-aware, and structured.
        Guide the user through a 30-minute weekly review with these phases:
        1. STARTUP (2 min) - Welcome and setup
        2. MIND SWEEP (10 min) - Capture everything 
        3. PROJECT REVIEW (12 min) - Quick decisions
        4. PRIORITIZATION (5 min) - ABC priorities
        5. WRAP-UP (3 min) - Save and celebrate"""
    }]
    
    # Phase 1: Startup
    print("\n--- PHASE 1: STARTUP (2 minutes) ---")
    messages.append({"role": "user", "content": "I'm ready to start my weekly review."})
    response = send_message(messages)
    messages.append({"role": "assistant", "content": response})
    print(f"\nCoach: {response}")
    
    time.sleep(2)
    
    # Phase 2: Mind Sweep (simulated)
    print("\n\n--- PHASE 2: MIND SWEEP (10 minutes) ---")
    messages.append({"role": "user", "content": "I've captured 8 items: finish project report, call dentist, review budget, team meeting prep, clean desk, update resume, exercise plan, birthday gift for mom."})
    response = send_message(messages)
    messages.append({"role": "assistant", "content": response})
    print(f"\nCoach: {response}")
    
    time.sleep(2)
    
    # Phase 3: Project Review (simulated)
    print("\n\n--- PHASE 3: PROJECT REVIEW (12 minutes) ---")
    messages.append({"role": "user", "content": "I'm reviewing my projects. For 'Project Alpha', I spent 12 hours last week. Next action: draft section 3."})
    response = send_message(messages)
    messages.append({"role": "assistant", "content": response})
    print(f"\nCoach: {response}")
    
    time.sleep(2)
    
    # Phase 4: Prioritization
    print("\n\n--- PHASE 4: PRIORITIZATION (5 minutes) ---")
    messages.append({"role": "user", "content": "Help me prioritize. My top actions are: project report (deadline Friday), dentist call, and budget review."})
    response = send_message(messages)
    messages.append({"role": "assistant", "content": response})
    print(f"\nCoach: {response}")
    
    time.sleep(2)
    
    # Phase 5: Wrap-up
    print("\n\n--- PHASE 5: WRAP-UP (3 minutes) ---")
    messages.append({"role": "user", "content": "Review complete. I reviewed 5 projects, made 8 decisions, and captured 8 new items."})
    response = send_message(messages)
    messages.append({"role": "assistant", "content": response})
    print(f"\nCoach: {response}")
    
    print("\n\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("\nTo run the full interactive review:")
    print("  python3 ~/gtd-coach/gtd-review.py")
    print("\nNote: The full version includes timers, data saving, and interactive prompts.")

if __name__ == "__main__":
    main()