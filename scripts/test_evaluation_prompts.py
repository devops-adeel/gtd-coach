#!/usr/bin/env python3
"""
Test that the evaluation system can fetch and use its prompts
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ['LANGFUSE_HOST'] = 'http://langfuse-prod-langfuse-web-1.orb.local'
os.environ['LANGFUSE_PUBLIC_KEY'] = 'pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed'
os.environ['LANGFUSE_SECRET_KEY'] = 'sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9'

def test_evaluation_prompts():
    """Test that evaluation prompts can be fetched and formatted"""
    
    print("Testing evaluation prompt fetching...")
    print("=" * 50)
    
    from gtd_coach.prompts.manager import get_prompt_manager
    
    prompt_manager = get_prompt_manager()
    
    # Test each evaluation prompt
    evaluation_prompts = [
        ("gtd-evaluation-task-extraction", {
            "user_input": "I need to call the dentist and finish the report",
            "extracted_tasks": '["Call dentist", "Finish report"]'
        }),
        ("gtd-evaluation-memory-relevance", {
            "phase": "MIND_SWEEP",
            "user_input": "I also need to review the project",
            "retrieved_memories": '["Previous project review notes"]',
            "coach_response": "I see you have a project review. Let me help you capture that."
        }),
        ("gtd-evaluation-coaching-quality", {
            "phase": "PRIORITIZATION",
            "time_remaining": "5",
            "user_input": "Too many things to do",
            "coach_response": "Let's focus on your top 3 for today. What feels most urgent?"
        })
    ]
    
    successful = []
    failed = []
    
    for prompt_name, variables in evaluation_prompts:
        try:
            # Format the prompt with variables
            formatted = prompt_manager.format_prompt(prompt_name, variables)
            
            # Check that variables were replaced
            if "{{" in formatted:
                raise Exception(f"Variables not properly replaced in {prompt_name}")
            
            successful.append(prompt_name)
            print(f"✅ {prompt_name}: Successfully fetched and formatted")
            print(f"   Preview: {formatted[:100]}...")
            
        except Exception as e:
            failed.append((prompt_name, str(e)))
            print(f"❌ {prompt_name}: Failed - {e}")
    
    print("\n" + "=" * 50)
    print(f"Summary: {len(successful)}/{len(evaluation_prompts)} evaluation prompts working")
    
    if failed:
        print("\nFailed prompts:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return False
    else:
        print("\n✅ All evaluation prompts are working correctly!")
        print("\nThe evaluation system is ready to use:")
        print("- Task extraction evaluation")
        print("- Memory relevance evaluation")
        print("- Coaching quality evaluation")
        return True

if __name__ == "__main__":
    success = test_evaluation_prompts()
    exit(0 if success else 1)