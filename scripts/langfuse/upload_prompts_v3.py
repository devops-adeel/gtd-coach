#!/usr/bin/env python3
"""
Upload updated GTD Coach prompts (v3) to Langfuse prompt management system.
This version includes fixed instructions for proper interrupt handling and data persistence.
"""

import os
from pathlib import Path
from langfuse import Langfuse

def upload_prompts_v3():
    """Upload updated prompt variants to Langfuse"""
    
    # Initialize Langfuse client (uses env vars)
    print("Initializing Langfuse client...")
    langfuse = Langfuse()
    
    # Read base prompt files
    # Use /app directory when running in Docker
    if os.path.exists("/app"):
        prompts_dir = Path("/app") / "config" / "prompts"
    else:
        prompts_dir = Path.home() / "gtd-coach" / "config" / "prompts"
    
    # System prompt (main) - WITH FIXED INSTRUCTIONS
    with open(prompts_dir / "system.txt", 'r') as f:
        base_system_prompt = f.read()
    
    # Add FIXED critical instructions for proper LangGraph agent behavior
    critical_instructions = """

CRITICAL INSTRUCTIONS FOR CONVERSATION FLOW (v3):

1. SINGLE INTERRUPT RULE:
   - Each conversation tool handles ONLY ONE interrupt
   - Never call a tool that has multiple questions in a loop
   - Call ask_question_v3 or ask_yes_no_v3 for EACH question separately

2. DATA PERSISTENCE REQUIREMENT:
   - After EVERY user response, immediately save the data using appropriate capture tools
   - Do not proceed to next question until current response is saved
   - Use these persistence tools:
     * save_user_response_v2(phase, question, response) - for general responses
     * save_mind_sweep_item_v2(item, category) - for mind sweep items
     * save_weekly_priority_v2(priority, rank, commitment) - for priorities
     * save_project_update_v2(project, status, next_action) - for project updates

3. PHASE-SPECIFIC BEHAVIOR:

STARTUP Phase:
   1. Call transition_phase_v2("STARTUP")
   2. Call ask_question_v3("How's your energy level today on a scale of 1-10?", "STARTUP")
   3. Call save_user_response_v2("STARTUP", "Energy level", <response>)
   4. Call ask_question_v3("Do you have any concerns or blockers before we begin?", "STARTUP")
   5. Call save_user_response_v2("STARTUP", "Concerns", <response>)
   6. Call ask_yes_no_v3("Are you ready to start the mind sweep phase?", True, "STARTUP")
   7. If yes, proceed to MIND_SWEEP

MIND_SWEEP Phase:
   1. Call transition_phase_v2("MIND_SWEEP")
   2. Call ask_question_v3("What's been on your mind this week?", "MIND_SWEEP")
   3. Parse the response to extract individual items:
      - If response contains commas, split by comma
      - Trim whitespace from each item
      - Each item is a separate mind sweep entry
   4. For each item: call save_mind_sweep_item_v2(item)
   5. Confirm items were captured before proceeding

PROJECT_REVIEW Phase:
   1. Call transition_phase_v2("PROJECT_REVIEW")
   2. Call ask_question_v3("What project would you like to review first?", "PROJECT_REVIEW")
   3. Call save_project_update_v2(project_name, status, next_action)
   4. Ask about additional projects as time permits

PRIORITIZATION Phase:
   1. Call transition_phase_v2("PRIORITIZATION")
   2. Call ask_question_v3("What are your top 3 priorities for the week?", "PRIORITIZATION")
   3. Parse response to extract priorities:
      - If response contains commas, split by comma
      - Trim whitespace from each priority
      - Assign rank 1, 2, 3 in order
   4. For each priority: call save_weekly_priority_v2(priority, rank)
   5. Call ask_question_v3("How will you ensure these tasks get done?", "PRIORITIZATION")
   6. Update priorities with commitment strategies

WRAP_UP Phase:
   1. Call transition_phase_v2("WRAP_UP")
   2. Call ask_yes_no_v3("Are you ready to wrap up the review?", True, "WRAP_UP")
   3. Evaluate the response:
      - If response is TRUE/YES:
        * Say "Great! The GTD weekly review is now complete."
        * Show summary of captured items and priorities
        * Celebrate completion with encouragement
      - If response is FALSE/NO:
        * DO NOT say the review is complete
        * DO NOT save the yes/no response as an answer to a different question
        * MUST call ask_question_v3("What else would you like to cover before we finish?", "WRAP_UP")
        * Wait for and handle the user's response
        * After handling the topic, return to step 2

4. AVAILABLE TOOLS (v3):

Conversation Tools (use these for user interaction):
   - ask_question_v3(question, context): Ask a single open-ended question
   - ask_yes_no_v3(question, default, context): Ask a yes/no question
   - DO NOT USE: check_in_with_user_v2, wait_for_user_input_v2, confirm_with_user_v2

Data Persistence Tools (use these IMMEDIATELY after getting responses):
   - save_user_response_v2(phase, question, response): Save general responses
   - save_mind_sweep_item_v2(item, category): Save mind sweep items
   - save_weekly_priority_v2(priority, rank, commitment): Save priorities
   - save_project_update_v2(project, status, next_action): Save project updates
   - batch_save_mind_sweep_v2(items): Save multiple items at once

Time Management Tools:
   - transition_phase_v2(phase): Transition to next phase
   - check_time_v2(): Check remaining time
   - send_alert_v2(type): Send audio alert

5. CRITICAL RULES:
   - NEVER proceed without saving user data
   - ALWAYS use v3 conversation tools (single interrupt pattern)
   - COMPLETE all 5 phases in order
   - SAVE data immediately after collection
   - Track progress through proper phase transitions

IMPORTANT: The v3 tools fix the interrupt state pollution issue. Each tool handles exactly one interrupt, avoiding LangGraph's re-execution problems."""
    
    complete_system_prompt = base_system_prompt + critical_instructions
    
    # Create new version with fixed instructions
    langfuse.create_prompt(
        name="gtd-coach-system-v3",
        type="text",  # Must be TEXT format, not chat
        prompt=complete_system_prompt,
        labels=["production"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-coach-system-v3 (with fixed interrupt handling)")
    
    # Also create a concise version for testing
    concise_instructions = """

CORE RULES FOR GTD COACH v3:

1. Use ONLY these conversation tools (one interrupt per tool):
   - ask_question_v3(question, context) - for open questions
   - ask_yes_no_v3(question, default, context) - for yes/no

2. IMMEDIATELY after EVERY response, save data:
   - save_user_response_v2() - general responses
   - save_mind_sweep_item_v2() - mind sweep items
   - save_weekly_priority_v2() - priorities
   - save_project_update_v2() - project updates

3. Phase flow: STARTUP → MIND_SWEEP → PROJECT_REVIEW → PRIORITIZATION → WRAP_UP

4. NEVER skip data persistence. ALWAYS save before proceeding."""
    
    langfuse.create_prompt(
        name="gtd-coach-system-v3-concise",
        type="text",
        prompt=base_system_prompt + concise_instructions,
        labels=["production", "concise"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-coach-system-v3-concise")
    
    # Upload other prompts (unchanged)
    # Firm tone prompt
    with open(prompts_dir / "firm.txt", 'r') as f:
        firm_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-firm-v3",
        prompt=firm_prompt,
        labels=["production", "firm"],
        config={"model": "gpt-4o", "temperature": 0.6}
    )
    print("✅ Uploaded: gtd-coach-firm-v3")
    
    # Simple prompt
    with open(prompts_dir / "simple.txt", 'r') as f:
        simple_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-simple-v3",
        prompt=simple_prompt,
        labels=["production", "simple"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-coach-simple-v3")
    
    print("\n✅ All v3 prompts uploaded successfully!")
    print("These prompts fix the interrupt state pollution issue.")
    print("\nTo use these prompts, update the agent to use 'gtd-coach-system-v3' instead of 'gtd-coach-system-v2'")

if __name__ == "__main__":
    upload_prompts_v3()