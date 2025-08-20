#!/usr/bin/env python3
"""
Test script to verify prompt linking works with Langfuse
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_prompt_linking():
    """Test that prompts are properly linked in both coach.py and agent"""
    print("Testing Langfuse prompt linking...")
    print("=" * 60)
    
    # Test 1: Check coach.py integration
    print("\n1. Testing coach.py prompt linking...")
    try:
        from gtd_coach.coach import GTDCoach
        coach = GTDCoach(model_name="meta-llama-3.1-8b-instruct")
        
        # Check if langfuse_prompts is initialized
        if hasattr(coach, 'langfuse_prompts') and coach.langfuse_prompts:
            print("✓ Langfuse prompts initialized in coach.py")
            
            # Check if OpenAI client is the Langfuse wrapper
            if hasattr(coach, 'openai_client'):
                client_module = coach.openai_client.__class__.__module__
                if 'langfuse' in client_module:
                    print("✓ Using Langfuse OpenAI wrapper in coach.py")
                else:
                    print("✗ Not using Langfuse OpenAI wrapper in coach.py")
        else:
            print("✗ Langfuse prompts not initialized in coach.py")
    except Exception as e:
        print(f"✗ Error testing coach.py: {e}")
    
    # Test 2: Check agent integration
    print("\n2. Testing agent prompt linking...")
    try:
        from gtd_coach.agent.runner import GTDAgentRunner
        runner = GTDAgentRunner()
        
        # Check if prompt object was fetched
        if hasattr(runner, 'prompt_object') and runner.prompt_object:
            print("✓ Prompt object fetched in agent runner")
            print(f"  - Prompt name: {runner.prompt_object.name}")
            if hasattr(runner.prompt_object, 'version'):
                print(f"  - Prompt version: {runner.prompt_object.version}")
        else:
            print("⚠ Prompt object not fetched (Langfuse might not be configured)")
        
        # Check if agent has prompt object
        if hasattr(runner.agent, 'prompt_object'):
            if runner.agent.prompt_object:
                print("✓ Prompt object passed to agent")
            else:
                print("⚠ Prompt object is None in agent")
        else:
            print("✗ Agent doesn't have prompt_object attribute")
        
        # Check if LLM is wrapped
        if hasattr(runner.agent, 'llm'):
            llm_class = runner.agent.llm.__class__.__name__
            if llm_class == 'PromptLinkedLLM':
                print("✓ Using PromptLinkedLLM wrapper in agent")
            else:
                print(f"✗ Using {llm_class} instead of PromptLinkedLLM")
    except Exception as e:
        print(f"✗ Error testing agent: {e}")
    
    # Test 3: Check prompt manager
    print("\n3. Testing prompt manager...")
    try:
        from gtd_coach.prompts.manager import get_prompt_manager
        prompt_manager = get_prompt_manager()
        
        if hasattr(prompt_manager, 'langfuse') and prompt_manager.langfuse:
            print("✓ Langfuse client initialized in prompt manager")
            
            # Try fetching a prompt
            try:
                test_prompt = prompt_manager.get_prompt("gtd-weekly-review-system")
                if test_prompt:
                    print("✓ Successfully fetched prompt from Langfuse")
            except Exception as e:
                print(f"⚠ Could not fetch prompt: {e}")
        else:
            print("⚠ Langfuse not configured in prompt manager")
    except Exception as e:
        print(f"✗ Error testing prompt manager: {e}")
    
    print("\n" + "=" * 60)
    print("Prompt linking test complete!")
    print("\nNOTE: Full verification requires:")
    print("1. Langfuse API keys configured in environment")
    print("2. Running an actual session and checking Langfuse UI")
    print("3. Verifying prompts appear linked in generation spans")

if __name__ == "__main__":
    test_prompt_linking()