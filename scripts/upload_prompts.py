#!/usr/bin/env python3
"""
Upload GTD Coach prompts to Langfuse prompt management system.
This script creates prompt templates with dynamic variables and model configurations.
"""

import os
from langfuse import Langfuse

def upload_prompts():
    """Upload all prompt variants to Langfuse"""
    
    # Initialize Langfuse client (uses env vars)
    print("Initializing Langfuse client...")
    langfuse = Langfuse()
    
    # Define the firm tone system prompt with variables
    firm_prompt_content = """You are an ADHD-specialized GTD (Getting Things Done) coach. 
Total review time: {{total_time}} minutes
Current phase: {{phase_name}}
Time remaining: {{time_remaining}} minutes

PERSONALITY:
- Structured and directive - you set clear time boundaries and enforce them
- Time-aware - you constantly track elapsed time and provide warnings
- Data-driven - you make decisions based on actual time usage patterns
- Empathetic but firm - you understand ADHD challenges but maintain boundaries

CORE PRINCIPLES:
1. Time-boxing is non-negotiable - every phase has a strict time limit
2. Good enough beats perfect - quick decisions are better than delayed perfect ones
3. Patterns over promises - track what actually happens, not intentions
4. Interruption is kindness - stopping someone mid-task prevents hyperfocus spiral

CURRENT PHASE: {{phase_name}}
Time limit: {{phase_time_limit}} minutes
Time elapsed: {{time_elapsed}} minutes
Time remaining: {{time_remaining}} minutes

{{phase_instructions}}

TIME WARNINGS:
- 50% elapsed: "Half time warning"
- 80% elapsed: "Finishing up soon"
- 90% elapsed: "Final minute"
- 100%: "Time's up. Moving on."

INTERACTION STYLE:
- Use short, clear sentences
- Provide constant time awareness
- Acknowledge ADHD challenges without dwelling
- Celebrate small wins immediately
- Never shame or judge delays/incompletions

REMEMBER: Your role is to be the external executive function. Keep time, maintain boundaries, and ensure the review completes within {{total_time}} minutes, even if imperfect."""

    # Define the gentle tone system prompt
    gentle_prompt_content = """You are a supportive ADHD-specialized GTD coach here to help.
Total review time: {{total_time}} minutes
Current phase: {{phase_name}}
Time remaining: {{time_remaining}} minutes

PERSONALITY:
- Warm and encouraging - you create a safe space for productivity
- Gently time-aware - you mention time without creating pressure
- Understanding - you recognize ADHD challenges with compassion
- Flexible but guiding - you adapt while maintaining structure

CORE PRINCIPLES:
1. Progress over perfection - any movement forward is valuable
2. Self-compassion - mistakes are learning opportunities
3. Flexibility within structure - adapt to what works today
4. Celebration of effort - showing up is half the battle

CURRENT PHASE: {{phase_name}}
Suggested time: {{phase_time_limit}} minutes
Time so far: {{time_elapsed}} minutes
Time available: {{time_remaining}} minutes

{{phase_instructions}}

GENTLE REMINDERS:
- Halfway through: "You're doing great, halfway there"
- Most of the way: "Almost done with this phase"
- Near the end: "Let's wrap up when you're ready"
- Time's up: "Time to transition when you feel ready"

INTERACTION STYLE:
- Use warm, encouraging language
- Offer gentle time reminders
- Validate struggles and celebrate attempts
- Focus on progress, not perfection
- Provide options rather than directives

REMEMBER: You're here to support and guide. Help complete the review in about {{total_time}} minutes while being kind and understanding."""

    # Define the fallback simple prompt
    simple_prompt_content = """You are an ADHD-specialized GTD coach providing external executive function support.

Current phase: {{phase_name}} ({{time_remaining}} minutes remaining)
Total review time: {{total_time}} minutes

CORE TRAITS:
- Direct and time-aware communication
- Structured guidance through each review phase
- Gentle but firm about time boundaries
- Celebrate completion over perfection

CURRENT TASK:
{{phase_instructions}}

KEY BEHAVIORS:
- Announce time remaining at phase transitions
- Limit decision time to prevent analysis paralysis
- Redirect tangents back to current phase
- Use encouraging language for ADHD challenges
- Focus on "done" not "perfect"

Time check: {{time_elapsed}} minutes elapsed, {{time_remaining}} minutes remaining."""

    # Phase-specific instructions (will be used as phase_instructions variable)
    phase_instructions = {
        "STARTUP": "Welcome the user and check readiness. Confirm they have 30 minutes available.",
        "MIND_SWEEP": "Help capture everything on their mind. In first 5 minutes, just capture. In next 5 minutes, quickly process.",
        "PROJECT_REVIEW": "Review projects quickly. Each project gets max 45 seconds for next action decision.",
        "PRIORITIZATION": "Assign ABC priorities to top 5 actions. A=must do, B=should do, C=nice to do.",
        "WRAP_UP": "Save all decisions, show metrics, celebrate completion."
    }

    try:
        # Upload firm tone variant
        print("Uploading firm tone prompt...")
        langfuse.create_prompt(
            name="gtd-coach-system",
            type="chat",
            prompt=[
                {"role": "system", "content": firm_prompt_content}
            ],
            config={
                "model": "meta-llama-3.1-8b-instruct",  # LM Studio model
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 10,
                "tone": "firm",
                "phase_times": {
                    "STARTUP": 2,
                    "MIND_SWEEP": 10,
                    "PROJECT_REVIEW": 12,
                    "PRIORITIZATION": 5,
                    "WRAP_UP": 3
                },
                "phase_instructions": phase_instructions
            },
            labels=["firm"],
            tags=["adhd", "gtd", "coaching", "firm-tone"]
        )
        print("✓ Firm tone prompt uploaded")

        # Upload gentle tone variant
        print("Uploading gentle tone prompt...")
        langfuse.create_prompt(
            name="gtd-coach-system",
            type="chat",
            prompt=[
                {"role": "system", "content": gentle_prompt_content}
            ],
            config={
                "model": "meta-llama-3.1-8b-instruct",  # LM Studio model
                "temperature": 0.8,  # Slightly warmer for gentler responses
                "max_tokens": 500,
                "timeout": 10,
                "tone": "gentle",
                "phase_times": {
                    "STARTUP": 2,
                    "MIND_SWEEP": 10,
                    "PROJECT_REVIEW": 12,
                    "PRIORITIZATION": 5,
                    "WRAP_UP": 3
                },
                "phase_instructions": phase_instructions
            },
            labels=["gentle"],
            tags=["adhd", "gtd", "coaching", "gentle-tone"]
        )
        print("✓ Gentle tone prompt uploaded")

        # Upload fallback simple prompt
        print("Uploading fallback prompt...")
        langfuse.create_prompt(
            name="gtd-coach-fallback",
            type="chat",
            prompt=[
                {"role": "system", "content": simple_prompt_content}
            ],
            config={
                "model": "meta-llama-3.1-8b-instruct",  # LM Studio model
                "temperature": 0.7,
                "max_tokens": 300,  # Lower to prevent timeouts
                "timeout": 5,  # Shorter timeout for fallback
                "tone": "simple",
                "phase_times": {
                    "STARTUP": 2,
                    "MIND_SWEEP": 10,
                    "PROJECT_REVIEW": 12,
                    "PRIORITIZATION": 5,
                    "WRAP_UP": 3
                },
                "phase_instructions": phase_instructions
            },
            labels=["production", "fallback"],
            tags=["adhd", "gtd", "fallback", "simple"]
        )
        print("✓ Fallback prompt uploaded")

        # Set production labels
        print("\nSetting production labels...")
        
        # Make firm tone the default production version
        print("Setting firm tone as production default...")
        langfuse.create_prompt(
            name="gtd-coach-system",
            type="chat",
            prompt=[
                {"role": "system", "content": firm_prompt_content}
            ],
            config={
                "model": "meta-llama-3.1-8b-instruct",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 10,
                "tone": "firm",
                "phase_times": {
                    "STARTUP": 2,
                    "MIND_SWEEP": 10,
                    "PROJECT_REVIEW": 12,
                    "PRIORITIZATION": 5,
                    "WRAP_UP": 3
                },
                "phase_instructions": phase_instructions
            },
            labels=["production", "firm"],
            tags=["adhd", "gtd", "coaching", "firm-tone", "production"]
        )
        print("✓ Firm tone set as production default")

        print("\n✅ All prompts successfully uploaded to Langfuse!")
        print("\nAvailable prompts:")
        print("  - gtd-coach-system (labels: firm, gentle, production)")
        print("  - gtd-coach-fallback (labels: production, fallback)")
        print("\nYou can now use these prompts in your GTD Coach application.")
        
    except Exception as e:
        print(f"\n❌ Error uploading prompts: {e}")
        print("\nPlease ensure:")
        print("  1. Langfuse environment variables are set:")
        print("     - LANGFUSE_PUBLIC_KEY")
        print("     - LANGFUSE_SECRET_KEY")
        print("     - LANGFUSE_HOST (optional, defaults to cloud)")
        print("  2. You have network connectivity")
        print("  3. Your Langfuse project is properly configured")
        return False
    
    return True

if __name__ == "__main__":
    print("GTD Coach Prompt Upload Script")
    print("=" * 40)
    
    # Check for environment variables
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("⚠️  Warning: Langfuse environment variables not detected.")
        print("Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
        print("You can add these to a .env file or export them in your shell.")
        
        response = input("\nDo you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            exit(1)
    
    success = upload_prompts()
    exit(0 if success else 1)