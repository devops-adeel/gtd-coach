#!/usr/bin/env python3
"""
Demo GTD Review - Testing with xLAM-7b-fc-r model
Optimized for function calling model
"""

import requests
import json
import time
from datetime import datetime

def send_message(messages, model_name="local-model"):
    """Send message to LLM and return response"""
    response = requests.post("http://localhost:1234/v1/chat/completions", 
        json={
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 300
        }, 
        timeout=30)
    
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def main():
    print("GTD Coach Demo - xLAM-7b-fc-r Model Test")
    print("=" * 60)
    print("\nTesting with xLAM-7b-fc-r (specialized for function calling)")
    print("This model ranks 3rd on Berkeley Function Calling Leaderboard\n")
    
    # System prompt optimized for xLAM
    messages = [{
        "role": "system", 
        "content": """You are an ADHD-specialized GTD coach. Be direct, time-aware, and structured.
        Guide the user through a 30-minute weekly review with these phases:
        1. STARTUP (2 min) - Welcome and setup
        2. MIND SWEEP (10 min) - Capture everything 
        3. PROJECT REVIEW (12 min) - Quick decisions
        4. PRIORITIZATION (5 min) - ABC priorities
        5. WRAP-UP (3 min) - Save and celebrate
        
        Be concise and action-oriented in your responses."""
    }]
    
    # Test 1: Basic interaction
    print("\n--- TEST 1: Basic Coach Interaction ---")
    messages.append({"role": "user", "content": "I'm ready to start my weekly review."})
    
    try:
        response = send_message(messages)
        messages.append({"role": "assistant", "content": response})
        print(f"\nCoach: {response}")
        print("✅ Basic interaction successful")
    except Exception as e:
        print(f"❌ Basic interaction failed: {e}")
        return 1
    
    time.sleep(1)
    
    # Test 2: Structured capture
    print("\n\n--- TEST 2: Mind Sweep Capture ---")
    messages.append({"role": "user", "content": "I need to capture: finish report, dentist appointment, review budget, team meeting prep"})
    
    try:
        response = send_message(messages)
        messages.append({"role": "assistant", "content": response})
        print(f"\nCoach: {response}")
        print("✅ Capture processing successful")
    except Exception as e:
        print(f"❌ Capture test failed: {e}")
        return 1
    
    time.sleep(1)
    
    # Test 3: Prioritization
    print("\n\n--- TEST 3: Prioritization ---")
    messages.append({"role": "user", "content": "Help me prioritize: project report (deadline Friday), dentist call, budget review"})
    
    try:
        response = send_message(messages)
        messages.append({"role": "assistant", "content": response})
        print(f"\nCoach: {response}")
        print("✅ Prioritization successful")
    except Exception as e:
        print(f"❌ Prioritization failed: {e}")
        return 1
    
    print("\n\n" + "=" * 60)
    print("✅ xLAM Model Test Complete!")
    print("\nModel Performance:")
    print("- Basic coaching dialogue: ✅")
    print("- Structured capture: ✅")
    print("- Prioritization guidance: ✅")
    print("\nNext step: Test with full GTD Coach agent and tools")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())