#!/usr/bin/env python3
"""
Fix the prompt type issue by re-uploading gtd-coach-system as a text prompt.
This ensures the prompt is stored as text type in Langfuse.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load credentials from home directory
load_dotenv('/Users/adeel/.env')

# Import Langfuse
try:
    from langfuse import Langfuse
except ImportError:
    print("❌ Langfuse not installed. Run: pip install langfuse")
    exit(1)

def main():
    """Re-upload the system prompt as text type"""
    
    print("Fixing prompt type issue...")
    print("=" * 60)
    
    # Initialize Langfuse client
    langfuse = Langfuse()
    
    # Check current prompt
    try:
        current_prompt = langfuse.get_prompt("gtd-coach-system", label="production")
        result = current_prompt.get_langchain_prompt()
        
        print(f"Current prompt type: {type(result).__name__}")
        if isinstance(result, list):
            print(f"  ⚠️  Prompt is currently a CHAT prompt with {len(result)} messages")
            print("  Will re-upload as TEXT prompt...")
        else:
            print(f"  ✅ Prompt is already a TEXT prompt")
            
    except Exception as e:
        print(f"Could not fetch current prompt: {e}")
    
    # Read the system prompt from local file
    prompts_dir = Path.home() / "gtd-coach" / "config" / "prompts"
    system_prompt_file = prompts_dir / "system.txt"
    
    if not system_prompt_file.exists():
        print(f"❌ System prompt file not found: {system_prompt_file}")
        exit(1)
    
    with open(system_prompt_file, 'r') as f:
        system_prompt = f.read()
    
    print(f"\nRead system prompt from: {system_prompt_file}")
    print(f"Prompt length: {len(system_prompt)} characters")
    
    # Re-create as text prompt (not chat)
    try:
        langfuse.create_prompt(
            name="gtd-coach-system",
            type="text",  # Explicitly set as text
            prompt=system_prompt,
            labels=["production"],
            config={"model": "gpt-4o", "temperature": 0.7}
        )
        print("\n✅ Successfully re-uploaded gtd-coach-system as TEXT prompt")
        
        # Verify the fix
        new_prompt = langfuse.get_prompt("gtd-coach-system", label="production")
        new_result = new_prompt.get_langchain_prompt()
        
        if isinstance(new_result, str):
            print("✅ Verified: Prompt is now a TEXT prompt")
        else:
            print(f"⚠️  Warning: Prompt is still type {type(new_result).__name__}")
            
    except Exception as e:
        print(f"❌ Failed to re-upload prompt: {e}")
        exit(1)
    
    print("\n" + "=" * 60)
    print("Fix complete! The prompt manager should now work correctly.")
    print("You can test with: ./scripts/deployment/docker-run.sh")

if __name__ == "__main__":
    main()