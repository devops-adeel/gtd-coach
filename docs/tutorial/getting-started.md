# Getting Started with GTD Coach

This tutorial walks you through your first weekly review with GTD Coach.

## Prerequisites

Before starting, ensure you have:
- LM Studio running with Llama 3.1 8B model loaded
- 30 minutes of uninterrupted time
- Docker or Python 3.11+ installed

## Your First Review

### Step 1: Start the Coach

```bash
# Using Docker (recommended)
./scripts/deployment/docker-run.sh

# Or using Python directly
python -m gtd_coach
```

### Step 2: The Five Phases

The coach will guide you through:

1. **STARTUP (2 min)**: System checks and welcome
2. **MIND SWEEP (10 min)**: Capture everything on your mind
3. **PROJECT REVIEW (12 min)**: Review and update projects  
4. **PRIORITIZATION (5 min)**: Set ABC priorities
5. **WRAP-UP (3 min)**: Save and celebrate

### Step 3: Follow the Timer

Audio alerts will notify you at:
- 50% time remaining (gentle chime)
- 20% time remaining (stronger alert)
- 10% time remaining (urgent notification)

### What to Expect

- The coach will prompt you at each phase
- Type your thoughts naturally - no special formatting needed
- Say "done" or "next" to move forward
- The system saves everything automatically

### After Your Review

Find your data in:
- `data/mindsweep_*.json` - Your captured thoughts
- `data/priorities_*.json` - Your ABC priorities
- `logs/review_*.json` - Complete session transcript

## Next Steps

- [Configure integrations](../how-to/configure-integrations.md) for enhanced features
- [Customize ADHD features](../how-to/customize-adhd-features.md) for your needs
- [Understand the architecture](../explanation/architecture.md) to learn how it works