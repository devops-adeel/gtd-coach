#!/usr/bin/env python3
"""
Upload ALL GTD Coach prompts to Langfuse prompt management system.
This includes prompts from text files and embedded prompts from Python files.
"""

import os
from pathlib import Path
from langfuse import Langfuse

def upload_prompts():
    """Upload all prompt variants to Langfuse"""
    
    # Initialize Langfuse client (uses env vars)
    print("Initializing Langfuse client...")
    langfuse = Langfuse()
    
    # =====================================================
    # 1. Upload existing prompts from config/prompts/
    # =====================================================
    
    # Read prompt files
    prompts_dir = Path.home() / "gtd-coach" / "config" / "prompts"
    
    # System prompt (main)
    with open(prompts_dir / "system.txt", 'r') as f:
        system_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-system",
        prompt=system_prompt,
        labels=["production"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-coach-system")
    
    # Firm tone prompt
    with open(prompts_dir / "firm.txt", 'r') as f:
        firm_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-firm",
        prompt=firm_prompt,
        labels=["production", "firm"],
        config={"model": "gpt-4o", "temperature": 0.6}
    )
    print("✅ Uploaded: gtd-coach-firm")
    
    # Simple prompt
    with open(prompts_dir / "simple.txt", 'r') as f:
        simple_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-simple",
        prompt=simple_prompt,
        labels=["production", "simple"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-coach-simple")
    
    # Fallback prompt
    with open(prompts_dir / "fallback.txt", 'r') as f:
        fallback_prompt = f.read()
    
    langfuse.create_prompt(
        name="gtd-coach-fallback",
        prompt=fallback_prompt,
        labels=["production", "fallback"],
        config={"model": "gpt-4o", "temperature": 0.5}
    )
    print("✅ Uploaded: gtd-coach-fallback")
    
    # =====================================================
    # 2. Upload embedded prompts from Python files
    # =====================================================
    
    # Task extraction evaluation prompt
    task_extraction_prompt = """You are evaluating task extraction accuracy for an ADHD coaching session.

User said: {{user_input}}

Tasks extracted by system: {{extracted_tasks}}

Questions:
1. Are all tasks mentioned by the user captured? (List any missed tasks)
2. Are there any incorrectly extracted items that aren't tasks?
3. Overall accuracy score (0.0 to 1.0)?

Respond in JSON format:
{{"score": 0.0-1.0, "missed_tasks": [], "incorrect_extractions": [], "reasoning": "brief explanation"}}"""
    
    langfuse.create_prompt(
        name="gtd-evaluation-task-extraction",
        prompt=task_extraction_prompt,
        labels=["production", "evaluation"],
        config={"model": "gpt-4o", "temperature": 0, "response_format": {"type": "json_object"}}
    )
    print("✅ Uploaded: gtd-evaluation-task-extraction")
    
    # Memory relevance evaluation prompt
    memory_relevance_prompt = """You are evaluating memory relevance for an ADHD coaching session.

Current context: {{phase}} phase
User input: {{user_input}}
Retrieved memories: {{retrieved_memories}}
Coach response: {{coach_response}}

Questions:
1. Were the retrieved memories relevant to the current context?
2. Did the coach actually use the memories in the response?
3. Relevance score (0.0 to 1.0)?

Respond in JSON format:
{{"score": 0.0-1.0, "memories_used": true/false, "reasoning": "brief explanation"}}"""
    
    langfuse.create_prompt(
        name="gtd-evaluation-memory-relevance",
        prompt=memory_relevance_prompt,
        labels=["production", "evaluation"],
        config={"model": "gpt-4o", "temperature": 0, "response_format": {"type": "json_object"}}
    )
    print("✅ Uploaded: gtd-evaluation-memory-relevance")
    
    # Coaching quality evaluation prompt
    coaching_quality_prompt = """You are evaluating coaching quality for ADHD users.

Phase: {{phase}}
Time remaining: {{time_remaining}}
User input: {{user_input}}
Coach response: {{coach_response}}

Evaluate for ADHD appropriateness:
1. Is the response concise and clear? (ADHD needs brevity)
2. Does it provide structure and time awareness?
3. Is it encouraging without being patronizing?
4. Does it respect time boundaries?
5. Overall quality score (0.0 to 1.0)?

Respond in JSON format:
{{"score": 0.0-1.0, "is_concise": true/false, "has_structure": true/false, "is_encouraging": true/false, "respects_time": true/false, "reasoning": "brief explanation"}}"""
    
    langfuse.create_prompt(
        name="gtd-evaluation-coaching-quality",
        prompt=coaching_quality_prompt,
        labels=["production", "evaluation"],
        config={"model": "gpt-4o", "temperature": 0, "response_format": {"type": "json_object"}}
    )
    print("✅ Uploaded: gtd-evaluation-coaching-quality")
    
    # Phase completion confirmation prompt
    phase_completion_prompt = """Phase Complete: {{phase}}
{{separator}}
{{summary}}

Time remaining: {{time_remaining}} minutes

Ready to continue to next phase?"""
    
    langfuse.create_prompt(
        name="gtd-phase-completion",
        prompt=phase_completion_prompt,
        labels=["production", "interaction"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-phase-completion")
    
    # Weekly review system message
    weekly_review_system = """You are a GTD coach helping with a weekly review process that has 5 phases: STARTUP, MIND_SWEEP, PROJECT_REVIEW, PRIORITIZATION, and WRAP_UP.

Current phase: {{current_phase}}
Time elapsed: {{time_elapsed}} minutes
Time remaining: {{time_remaining}} minutes

Your role:
1. Guide the user through the current phase
2. Keep strict time boundaries
3. Use tools to capture and organize information
4. Interrupt for user input when needed
5. Transition between phases smoothly

Remember: You are providing external executive function support for someone with ADHD. Be structured, time-aware, and encouraging."""
    
    langfuse.create_prompt(
        name="gtd-weekly-review-system",
        prompt=weekly_review_system,
        labels=["production", "agent"],
        config={"model": "gpt-4o", "temperature": 0.7}
    )
    print("✅ Uploaded: gtd-weekly-review-system")
    
    # Daily capture prompt
    daily_capture_prompt = """You are guiding a daily GTD capture session.

Time limit: {{time_limit}} minutes
Current items captured: {{items_count}}

Focus areas:
1. Quick brain dump - no filtering
2. Capture everything on your mind
3. Projects, tasks, ideas, concerns
4. We'll process these later

{{additional_guidance}}

What's on your mind right now?"""
    
    langfuse.create_prompt(
        name="gtd-daily-capture",
        prompt=daily_capture_prompt,
        labels=["production", "daily"],
        config={"model": "gpt-4o", "temperature": 0.8}
    )
    print("✅ Uploaded: gtd-daily-capture")
    
    # ADHD intervention prompt
    adhd_intervention_prompt = """ADHD pattern detected: {{pattern_type}}

Severity: {{severity}}
Context: {{context}}

Suggested intervention:
{{intervention_text}}

Would you like to:
1. Take a short break
2. Continue with modified approach
3. Switch to a different task
4. End session early

What feels right for you now?"""
    
    langfuse.create_prompt(
        name="gtd-adhd-intervention",
        prompt=adhd_intervention_prompt,
        labels=["production", "intervention"],
        config={"model": "gpt-4o", "temperature": 0.6}
    )
    print("✅ Uploaded: gtd-adhd-intervention")
    
    # LLM evaluation prompt for self-assessment
    llm_evaluation_prompt = """Evaluate the following response:

Context: {{context}}
User Input: {{user_input}}
Response: {{response}}

Criteria:
- Relevance: Does the response address the prompt?
- Clarity: Is it clear and understandable?
- ADHD-appropriate: Is it concise and structured?
- Time-aware: Does it respect time boundaries?
- Actionable: Does it provide clear next steps?

Score (0.0-1.0): """
    
    langfuse.create_prompt(
        name="gtd-llm-self-evaluation",
        prompt=llm_evaluation_prompt,
        labels=["production", "evaluation"],
        config={"model": "gpt-4o", "temperature": 0}
    )
    print("✅ Uploaded: gtd-llm-self-evaluation")
    
    print("\n✅ All prompts uploaded successfully!")
    print(f"Total prompts uploaded: 12")
    print("\nYou can now manage these prompts in the Langfuse UI")
    print("and update them without changing code.")

if __name__ == "__main__":
    upload_prompts()