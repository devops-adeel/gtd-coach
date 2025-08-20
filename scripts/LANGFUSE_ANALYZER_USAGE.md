# Enhanced Langfuse Analyzer - Quick Reference

## Purpose
This enhanced analyzer helps debug GTD Coach agent failures by analyzing:
- Phase transitions and state loss
- Prompt performance and correlations with scores
- Conversation flow with metadata
- State continuity validation

## Quick Commands

### 1. Debug Everything (My Go-To Command)
```bash
# Comprehensive debug of a session
python3 scripts/analyze_langfuse_traces.py --debug SESSION_ID

# Example output shows:
# - Phase transitions with state loss warnings
# - Prompt usage and score correlations
# - Conversation flow
# - State validation results
# - Suggested fixes for issues found
```

### 2. Focus on Phase Transitions
```bash
# When users report lost tasks during phase changes
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --show-transitions

# Shows:
# - MIND_SWEEP → PROJECT_REVIEW transitions
# - ❌ STATE LOST: tasks, projects
# - Score drops at transitions
```

### 3. Analyze Prompt Performance
```bash
# When scores are consistently low
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --prompt-analysis

# Shows:
# - Which prompts were used (gtd-coach-firm, gtd-coach-gentle)
# - Prompt versions and variables
# - Average scores per prompt
# - Correlation with failures
```

### 4. View Conversation Flow
```bash
# To understand what the agent actually said
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --show-conversation

# Shows:
# - 👤 User messages
# - 🤖 Agent responses
# - 🔔 Interrupts
# - 📍 Phase context
# - ⏱️ Time remaining
```

### 5. Validate State Continuity
```bash
# When state seems to disappear
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --validate-state

# Shows:
# - ❌ Lost tasks at timestamp
# - ⚠️ Low memory relevance warnings
# - State inconsistencies
```

### 6. Combined Analysis
```bash
# Multiple focus areas
python3 scripts/analyze_langfuse_traces.py --debug SESSION_ID --show-transitions --prompt-analysis
```

## Common Debugging Scenarios

### "Agent lost my tasks when changing phases"
```bash
python3 scripts/analyze_langfuse_traces.py --debug SESSION_ID --show-transitions
# Look for: STATE LOST warnings, missing state variables in prompts
```

### "Agent quality degraded during session"
```bash
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --prompt-analysis
# Look for: Low average scores, prompt version issues
```

### "Agent gave weird responses"
```bash
python3 scripts/analyze_langfuse_traces.py --session SESSION_ID --show-conversation
# Look for: Context issues, interrupt patterns, time pressure effects
```

### Test failure analysis
```bash
# For pytest test failures with Langfuse traces
python3 scripts/analyze_langfuse_traces.py --test-failure SESSION_ID
```

## Environment Setup
```bash
# Required environment variables (usually in ~/.env)
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=http://langfuse-prod-langfuse-web-1.orb.local  # or cloud URL
```

## Key Indicators to Watch For

### ❌ Critical Issues
- STATE LOST: tasks/projects/priorities disappearing
- Score < 0.3: Very poor agent performance
- Memory relevance < 0.5: Retrieved memories not relevant

### ⚠️ Warnings
- Score 0.3-0.5: Degraded performance
- Frequent interrupts: Agent confusion
- Time pressure: time_remaining < 2 minutes

### ✅ Good Signs
- Score > 0.7: Good agent performance
- State maintained across phases
- Smooth phase transitions

## Suggested Fixes Reference

### State Loss Issues
- Check prompt templates for missing {{tasks}}, {{projects}}, {{priorities}} variables
- Verify LangGraph checkpoint/persistence configuration
- Ensure state is passed in phase transition prompts

### Low Score Issues
- Review temperature settings (lower for more consistency)
- Check if prompt version matches the phase requirements
- Verify model selection (gpt-4o vs llama3)

### Memory Relevance Issues
- Review memory retrieval query construction
- Check phase-specific filtering logic
- Verify embedding quality and similarity thresholds

## Testing the Analyzer
```bash
# Run unit tests
python3 scripts/test_enhanced_langfuse_analyzer.py
```