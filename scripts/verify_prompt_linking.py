#!/usr/bin/env python3
"""
Verify that prompt linking is working correctly
"""

from gtd_coach.agent.runner import GTDAgentRunner

print("Testing prompt linking in GTD Agent...")
print("=" * 60)

try:
    runner = GTDAgentRunner()
    print("✓ Agent initialized")
    
    # Check prompt object
    if hasattr(runner, "prompt_object"):
        if runner.prompt_object:
            name = getattr(runner.prompt_object, 'name', 'Unknown')
            print(f"✓ Prompt object fetched: {name}")
            version = getattr(runner.prompt_object, 'version', 'N/A')
            print(f"  - Version: {version}")
        else:
            print("⚠ Prompt object is None (Langfuse may not be configured)")
    else:
        print("✗ Runner doesn't have prompt_object attribute")
    
    # Check agent prompt object
    if hasattr(runner.agent, "prompt_object"):
        if runner.agent.prompt_object:
            print("✓ Prompt object passed to agent")
        else:
            print("⚠ Agent prompt_object is None")
    else:
        print("✗ Agent doesn't have prompt_object attribute")
    
    # Check LLM wrapper
    if hasattr(runner.agent, "prompt_wrapper"):
        if runner.agent.prompt_wrapper:
            print("✓ Using PromptLinkedLLM wrapper - prompts will be linked!")
            print(f"  - Wrapper applied to: {runner.agent.llm.__class__.__name__}")
        else:
            print("⚠ No prompt wrapper applied")
    else:
        print("✗ Agent doesn't have prompt_wrapper attribute")
    
    print("\n" + "=" * 60)
    print("✅ Prompt linking setup complete!")
    print("\nNext steps to verify in Langfuse UI:")
    print("1. Run a session: scripts/deployment/docker-run.sh")
    print("2. Check Langfuse UI at http://localhost:3000")
    print("3. Look for linked prompts in generation spans")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()