#!/usr/bin/env python3
"""
Test script for GTD Coach - non-interactive verification
"""

import requests
import json
from pathlib import Path

# Configuration
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama-3.1-8b-instruct"
PROMPTS_DIR = Path.home() / "gtd-coach" / "prompts"

def test_llm_connection():
    """Test basic LLM connectivity"""
    print("Testing LLM connection...")
    
    # Load system prompt
    with open(PROMPTS_DIR / "system-prompt.txt", 'r') as f:
        system_prompt = f.read()
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Start the weekly review process."}
    ]
    
    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 200
        }, timeout=10)
        
        response.raise_for_status()
        assistant_message = response.json()['choices'][0]['message']['content']
        
        print("\n✅ LLM Connection successful!")
        print("\nCoach response:")
        print("-" * 50)
        print(assistant_message)
        print("-" * 50)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if LM Studio server is running: lms server status")
        print("2. Check if model is loaded: lms ps")
        print("3. Verify model identifier matches: lms ps --json")
        return False

def test_timer():
    """Test the timer script"""
    print("\n\nTesting timer script...")
    import subprocess
    
    timer_script = Path.home() / "gtd-coach" / "scripts" / "timer.sh"
    
    try:
        # Test with 0.1 minutes (6 seconds)
        print("Starting 6-second timer test...")
        result = subprocess.run([str(timer_script), "0.1", "Timer test complete!"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Timer script working!")
            print("Output:", result.stdout)
        else:
            print("❌ Timer script failed!")
            print("Error:", result.stderr)
            
    except Exception as e:
        print(f"❌ Timer test failed: {e}")

def main():
    print("GTD Coach System Test")
    print("=" * 50)
    
    # Test 1: LLM Connection
    if test_llm_connection():
        # Test 2: Timer
        test_timer()
        
        print("\n\n✅ All tests passed!")
        print("\nTo run the full interactive review:")
        print("  python3 ~/gtd-coach/gtd-review.py")
    else:
        print("\n❌ Tests failed. Please fix the issues above.")

if __name__ == "__main__":
    main()