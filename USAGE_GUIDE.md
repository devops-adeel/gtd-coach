# GTD Coach Usage Guide

A complete guide to using your ADHD-optimized GTD weekly review system.

## Table of Contents
1. [Before Your Review](#before-your-review)
2. [Starting the Coach](#starting-the-coach)
3. [The Review Process](#the-review-process)
4. [Interacting with the Coach](#interacting-with-the-coach)
5. [Understanding Your Data](#understanding-your-data)
6. [Troubleshooting](#troubleshooting)
7. [ADHD Success Tips](#adhd-success-tips)

---

## Before Your Review

### Preparation Checklist
- [ ] Block 30 uninterrupted minutes
- [ ] Phone in another room or airplane mode
- [ ] Glass of water nearby
- [ ] Standing desk raised (optional but helpful)
- [ ] Close unnecessary browser tabs
- [ ] Have your calendar open in another window
- [ ] Notebook for physical capture (if preferred)

### Timing Recommendations
- **Best times**: Morning (9-11am) or early afternoon (2-4pm)
- **Avoid**: Late evening, right after meals, when medication is wearing off
- **Consistency**: Same day and time each week builds habit

---

## Starting the Coach

### Method 1: Full Startup (Recommended First Time)
```bash
~/gtd-coach/start-coach.sh
```
This will:
1. Check if LM Studio server is running
2. Load the model if needed
3. Ask if you want to start the review immediately

### Method 2: Direct Review (If Server Already Running)
```bash
python3 ~/gtd-coach/gtd-review.py
```

### What You'll See
```
GTD Weekly Review Coach for ADHD
================================

✓ LM Studio server is running

Press Enter when ready to start your 30-minute review...
```

---

## The Review Process

### Phase 1: STARTUP (2 minutes)
**What happens:**
- Timer starts automatically
- Coach welcomes you and sets expectations
- Quick check-in on your readiness

**Your role:**
- Simply acknowledge you're ready
- No deep thinking yet
- Just get into the review mindset

**Example interaction:**
```
Coach: Welcome to your weekly review! We have 30 minutes together...
You: [Just press Enter or type a brief acknowledgment]
```

### Phase 2: MIND SWEEP (10 minutes)
**What happens:**
- 5 minutes for brain dump
- 5 minutes for coach processing
- Audio alert at 1 minute remaining

**Your role:**
- Type everything on your mind, one item per line
- Don't edit or judge - just dump
- Include personal and professional items
- Press Enter after each item

**Example items:**
```
> finish project report
> call dentist
> mom's birthday gift
> fix leaky faucet
> review team proposals
> [press Enter with empty line when done]
```

**Coach response:**
- Acknowledges number of items
- May flag if list seems too long/short
- Provides encouragement

### Phase 3: PROJECT REVIEW (12 minutes)
**What happens:**
- Reviews up to 10 projects
- 45 seconds per project for next action
- Shows time spent last week (when integrated)

**Your role:**
- Quickly identify ONE next action per project
- Don't overthink - first reasonable action
- Type action and press Enter

**Example:**
```
[1/10] Project: Website Redesign
Last week time: 8.5 hours
Next action (45 sec): draft new homepage wireframe
✓ Recorded
```

**Time pressure is intentional** - prevents analysis paralysis

### Phase 4: PRIORITIZATION (5 minutes)
**What happens:**
- Coach guides ABC prioritization
- Focus on next 7 days only
- Maximum 5-7 priority items

**Your role:**
- List your must-do actions
- Assign A/B/C priorities quickly
- A = Must do this week
- B = Should do if time
- C = Would be nice

**Example:**
```
Action 1: finish quarterly report
Priority (A/B/C): A

Action 2: organize desk drawer
Priority (A/B/C): C
```

### Phase 5: WRAP-UP (3 minutes)
**What happens:**
- Summary of accomplishments
- Data automatically saved
- Celebration message

**Your role:**
- Acknowledge completion
- Note any final thoughts
- CELEBRATE that you finished!

---

## Interacting with the Coach

### Communication Style
- **Be brief**: Short responses work best
- **Trust the process**: Don't negotiate with time limits
- **Stay in phase**: Coach will redirect if you drift

### Keyboard Commands
- **Enter**: Submit current input
- **Ctrl+C**: Emergency stop (progress saved)
- No special commands needed during normal use

### Coach Personality
- Direct but encouraging
- Time-focused reminders
- ADHD-aware language
- Celebrates done over perfect

---

## Understanding Your Data

### Where Data Lives
```
~/gtd-coach/data/
├── mindsweep_20250102_143022.json    # Items from brain dump
└── priorities_20250102_145522.json    # Your ABC priorities

~/gtd-coach/logs/
└── review_20250102_143022.json        # Complete session log
```

### Viewing Your History
```bash
# See recent mind sweep items
cat ~/gtd-coach/data/mindsweep_*.json | jq

# Check your last priorities
ls -la ~/gtd-coach/data/priorities_*.json
```

### Tracking Patterns
Look for:
- Recurring items in mind sweeps
- Projects that never get next actions
- Consistent number of captured items
- Time taken for decisions

---

## Troubleshooting

### "LM Studio server is not running"
```bash
lms server start
~/gtd-coach/start-coach.sh
```

### "Read timeout" errors
- Model may be loading slowly first time
- Try again after 30 seconds
- Check `KNOWN_ISSUES.md` for details

### Coach seems unresponsive
1. Check server: `lms server status`
2. Check model: `lms ps`
3. Restart if needed: `lms server restart`

### Timer not working
- Ensure script is executable: `chmod +x ~/gtd-coach/scripts/timer.sh`
- Test manually: `~/gtd-coach/scripts/timer.sh 1 "test"`

---

## ADHD Success Tips

### Before Review
1. **Medication timing**: Do review when meds are effective
2. **Environment**: Standing > sitting for focus
3. **Hydration**: Water prevents fatigue
4. **Movement**: Quick walk before starting

### During Review
1. **Trust the timer**: It's your external executive function
2. **Capture everything**: Judgment comes later
3. **First thought best thought**: For next actions
4. **Progress not perfection**: 70% review > 0% review

### Common ADHD Challenges & Solutions

**"I forgot what I was doing"**
- Coach keeps you on track
- Timer shows phase progress
- Just follow the prompts

**"Too many thoughts at once"**
- Mind sweep captures everything
- One item at a time
- Brain dump prevents overwhelm

**"Can't decide on priorities"**
- 45-second limit forces decision
- First instinct is usually right
- Can always adjust later

**"Getting distracted"**
- 30-minute limit maintains focus
- Audio alerts bring attention back
- Phases create mini-goals

### After Review
1. **Immediate reward**: Planned treat/activity
2. **Quick win**: Do one A-priority item
3. **Calendar block**: Next week's review
4. **Share success**: Tell someone you completed it

---

## Advanced Usage

### Custom Timers
```bash
# Pomodoro work session after review
~/gtd-coach/scripts/timer.sh 25 "Take a break!"

# Quick 5-minute task
~/gtd-coach/scripts/timer.sh 5 "Task complete!"
```

### Modifying Phases
Edit `~/gtd-coach/gtd-review.py` to adjust:
- Phase durations (keep total ≤30 min)
- Number of projects reviewed
- Prompt styles

### Integration Ideas
- Export Timing app data before review
- Use mind sweep items for Things/Todoist
- Share priorities with accountability partner

---

## Quick Reference Card

```
START SESSION
$ ~/gtd-coach/start-coach.sh

PHASES (30 min total)
1. STARTUP      2 min   Get ready
2. MIND SWEEP   10 min  Brain dump
3. PROJECTS     12 min  Next actions  
4. PRIORITIES   5 min   ABC ranking
5. WRAP-UP      3 min   Celebrate!

EMERGENCY STOP
Ctrl+C (progress saved)

GET HELP
cat ~/gtd-coach/USAGE_GUIDE.md
```

---

Remember: The goal is COMPLETION, not perfection. Your future self will thank you for any review, even a messy one! 🎯