# GTD Coach User Guide

**Your ADHD-friendly guide to weekly reviews that actually work**

> 🎯 **TL;DR**: Run `python -m gtd_coach` and follow the prompts for 30 minutes.

## Quick Start (2 minutes)

### Prerequisites Checklist
- [ ] **LM Studio** running with Llama model loaded
- [ ] **30 minutes** blocked with no interruptions
- [ ] **Phone** in another room (seriously!)
- [ ] **Water/coffee** ready
- [ ] **Standing** or able to move around

### Start Your Review
```bash
# Option 1: Using Python module
python -m gtd_coach

# Option 2: Using shell script (if available)
./scripts/start-coach.sh
```

## The 30-Minute Journey

Your review follows a strict phase-based structure designed for ADHD brains:

```
STARTUP (2 min) → MIND SWEEP (10 min) → PROJECT REVIEW (12 min) → PRIORITIZATION (5 min) → WRAP-UP (3 min)
```

### Phase 1: STARTUP (2 minutes)
- Coach welcomes you and loads any previous context
- Timing app fetches your project data (if configured)
- You just need to say "yes" when ready

### Phase 2: MIND SWEEP (10 minutes)
Split into two parts:

**Part A: Capture (5 minutes)**
- Type EVERYTHING on your mind
- One thought per line, press Enter after each
- Don't filter or organize - just dump
- Timer gives audio alerts at 50%, 20%, 10% remaining

**Part B: Processing (5 minutes)**
- Coach helps you process what you captured
- Groups related items
- Identifies patterns (task switching, unfinished items)
- No judgment, just organization

### Phase 3: PROJECT REVIEW (12 minutes)
- Review each project (~45 seconds each)
- Define ONE next action per project
- Coach keeps you moving - no analysis paralysis
- Skip projects with "skip" command

### Phase 4: PRIORITIZATION (5 minutes)
- Assign A/B/C priorities
- A = Must do this week
- B = Should do if time
- C = Nice to have
- Coach prevents over-committing

### Phase 5: WRAP-UP (3 minutes)
- Save all data automatically
- Generate focus metrics (if Timing configured)
- Celebrate completion!
- View summary of decisions

## ADHD-Specific Features

### Time Boxing
Every phase has strict time limits with audio alerts:
- 🔔 50% time remaining - gentle chime
- ⚠️ 20% time remaining - warning bell
- 🚨 10% time remaining - urgent alert

### External Executive Function
The coach acts as your external brain:
- Keeps track of time
- Prevents rabbit holes
- Makes transitions between phases
- Saves everything automatically

### Pattern Detection
The system tracks your ADHD patterns:
- Task switching frequency
- Hyperfocus periods
- Incomplete task accumulation
- Context switching costs

### No Shame, Just Support
- Firm but kind coaching tone
- Acknowledges ADHD challenges
- Celebrates small wins
- Focuses on progress, not perfection

## Commands During Review

- `skip` - Skip current item/project
- `pause` - Pause timer (emergency only!)
- `help` - Get context-sensitive help
- Empty line + `y` - Finish current section early

## Configuration

### Environment Variables
Create a `.env` file in the project root:

```bash
# LM Studio settings
LM_STUDIO_URL=http://localhost:1234/v1

# Optional: Timing app integration
TIMING_API_KEY=your-key-here

# Optional: Langfuse observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Optional: Graphiti memory
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
```

### Customize Coaching Tone
Two coaching styles available:
- **Firm**: Direct, time-focused (default)
- **Gentle**: Supportive, flexible

Set in `.env`:
```bash
COACHING_STYLE=firm  # or 'gentle'
```

## Troubleshooting

### LM Studio Not Responding
1. Check if LM Studio is running: `lms ps`
2. Verify model is loaded (Llama 3.1 8B recommended)
3. Check URL in `.env` matches LM Studio settings

### Timer Not Working
- macOS: Ensure terminal has audio permissions
- Linux: Install `sox` for audio: `sudo apt-get install sox`
- Windows: Audio alerts may not work (visual only)

### Review Interrupted
Don't worry! All data is saved continuously:
- Check `data/` folder for your captures
- Run `python -m gtd_coach --resume` to continue

### Focus Metrics Not Showing
Timing app integration requires:
1. Timing Connect subscription
2. API key in `.env` file
3. Timing app running during review

## Tips for Success

### Before You Start
- **Block time**: Full 30 minutes, no exceptions
- **Remove distractions**: Phone away, notifications off
- **Stand up**: Movement helps ADHD focus
- **Have water**: Hydration improves cognition

### During the Review
- **Trust the process**: Don't fight the timer
- **Quantity over quality**: More is better in mind sweep
- **One decision**: Each project needs ONE next action
- **Be honest**: Real priorities, not wishful thinking

### After the Review
- **Review summary**: Check `summaries/` folder
- **Calendar blocking**: Schedule your A priorities
- **Share wins**: Tell someone you completed it
- **Same time next week**: Consistency is key

## Weekly Summary

After each review, find your summary in `summaries/` folder:
- Mind sweep patterns
- Focus metrics (if Timing configured)
- Priority distribution
- ADHD pattern insights
- Suggested adjustments

## Getting Help

- **In-review help**: Type `help` anytime
- **Documentation**: This guide and `docs/DEVELOPER.md`
- **Issues**: Check `docs/TROUBLESHOOTING.md`
- **Community**: Share experiences and tips

Remember: **Done is better than perfect.** The goal is consistency, not perfection. Every completed review is a win!