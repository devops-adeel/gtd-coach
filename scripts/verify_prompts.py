#!/usr/bin/env python3
"""
Verify that all required prompts are available in Langfuse
"""

import os
from langfuse import Langfuse

# Export environment variables
os.environ['LANGFUSE_HOST'] = 'http://langfuse-prod-langfuse-web-1.orb.local'
os.environ['LANGFUSE_PUBLIC_KEY'] = 'pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed'
os.environ['LANGFUSE_SECRET_KEY'] = 'sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9'

def verify_prompts():
    """Verify all prompts are available"""
    
    langfuse = Langfuse()
    
    # List of all prompts that should exist
    required_prompts = [
        "gtd-coach-system",
        "gtd-coach-fallback",
        "gtd-coach-firm",
        "gtd-coach-simple",
        "gtd-evaluation-task-extraction",
        "gtd-evaluation-memory-relevance",
        "gtd-evaluation-coaching-quality",
        "gtd-phase-completion",
        "gtd-weekly-review-system",
        "gtd-daily-capture",
        "gtd-adhd-intervention",
        "gtd-llm-self-evaluation"
    ]
    
    print("Verifying prompts in Langfuse...")
    print("=" * 50)
    
    successful = []
    failed = []
    
    for prompt_name in required_prompts:
        try:
            # Try to fetch the prompt
            prompt = langfuse.get_prompt(prompt_name)
            successful.append(prompt_name)
            print(f"✅ {prompt_name}: Available (version {prompt.version})")
        except Exception as e:
            failed.append((prompt_name, str(e)))
            print(f"❌ {prompt_name}: Failed - {e}")
    
    print("\n" + "=" * 50)
    print(f"Summary: {len(successful)}/{len(required_prompts)} prompts available")
    
    if failed:
        print("\nMissing or inaccessible prompts:")
        for name, error in failed:
            print(f"  - {name}")
    else:
        print("\n✅ All prompts are available and accessible!")
    
    return len(successful) == len(required_prompts)

if __name__ == "__main__":
    success = verify_prompts()
    exit(0 if success else 1)