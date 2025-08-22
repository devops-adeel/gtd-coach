# Getting Started with GTD Coach

## Before You Begin (Checklist)

### ✅ You'll Need:
- [ ] **30 minutes** of uninterrupted time
- [ ] **LM Studio** running with Llama 3.1 8B model
- [ ] **Quiet space** without distractions  
- [ ] **Notebook** for extra thoughts
- [ ] **Phone on silent** (trust the timer instead)

---

## Your Weekly Review Timeline

### 📊 The 30-Minute Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
|🚀 STARTUP | 🧠 MIND SWEEP | 📋 PROJECTS | ⭐ PRIORITIES |✅ WRAP|
|  2 min    |    10 min     |   12 min    |    5 min     | 3 min |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 Audio alerts help you stay on track
```

---

## Starting Your Review

### Step 1: Launch GTD Coach

```bash
# If using Docker (recommended)
./scripts/deployment/docker-run.sh

# If running locally
python gtd_coach/main.py
```

### Step 2: What You'll See

```
========================================
🎯 GTD WEEKLY REVIEW - ADHD OPTIMIZED
========================================
Welcome! This is your structured weekly review.
We'll work through 5 phases in 30 minutes.

Ready to start? The timer begins now!
[Phase: STARTUP - 2 minutes remaining]

How's your energy level today (1-10)?
> 
```

**Just type a number and press Enter.**

---

## What Happens in Each Phase

### 🚀 **Phase 1: Startup** (2 minutes)

**You'll be asked:**
- Your energy level (1-10)
- Any concerns before starting

**Audio alerts:**
- 🔔 One beep at 1 minute left

**Why this matters:**  
Sets the baseline. Low energy? Coach adapts.

---

### 🧠 **Phase 2: Mind Sweep** (10 minutes)

**You'll do:**
- Brain dump EVERYTHING on your mind
- No filtering, no judging
- Just get it out

**Example response:**
```
> finish project report, call mom, fix printer, 
  buy groceries, gym membership, that email to boss,
  birthday gift for Sam, clean desk, backup photos
```

**Audio alerts:**
- 🔔 At 5 minutes (halfway)
- 🔔🔔 At 8 minutes (speed up!)
- 🔔🔔🔔 At 9 minutes (last minute!)

**Why this matters:**  
Clears mental RAM. Can't organize what you can't see.

---

### 📋 **Phase 3: Project Review** (12 minutes)

**You'll review:**
- Current projects progress
- What's stuck or needs attention
- Next actions for each

**Coach will ask:**
```
What project would you like to review first?
> Website redesign

What's the current status?
> Mockups done, waiting on feedback

What's the next action?
> Schedule review meeting with team
```

**Audio alerts:**
- 🔔 At 6 minutes
- 🔔🔔 At 10 minutes
- 🔔🔔🔔 At 11 minutes

**Why this matters:**  
Keeps projects moving. Identifies blockers early.

---

### ⭐ **Phase 4: Prioritization** (5 minutes)

**You'll choose:**
- Your TOP 3 priorities for the week
- Only 3. Not 5. Not 10. Just 3.

**Coach will ask:**
```
What are your top 3 priorities for this week?
> 1. Finish project report
  2. Prepare presentation
  3. Clear email backlog
```

**Audio alerts:**
- 🔔 At 3 minutes
- 🔔🔔 At 4 minutes

**Why this matters:**  
ADHD brains need focus. Three is manageable.

---

### ✅ **Phase 5: Wrap Up** (3 minutes)

**What happens:**
- Review saved automatically
- Summary displayed
- Celebration moment! 🎉

**You'll see:**
```
Great! The GTD weekly review is now complete.

📊 Review Summary:
- Mind sweep items: 12 captured
- Projects reviewed: 3
- Weekly priorities: 3 set

Your data is saved in: data/reviews/2025-W04/
```

**Why this matters:**  
Closure is important. You did the thing!

---

## Common Questions

### "The timer keeps beeping!"

**This is good!** The beeps are your external executive function.
- They prevent hyperfocus on one topic
- They keep you moving through all phases
- They ensure you finish in 30 minutes

### "I got interrupted during my review"

**No problem:**
1. Type `pause` or just close the window
2. Your progress is saved automatically
3. Restart when ready - you'll resume where you left off

### "The AI doesn't understand me"

**Try:**
- Shorter, clearer responses
- One topic at a time
- If stuck, just move on (progress > perfection)

### "I ran out of time in a phase"

**That's OK!** The timer ensures you cover everything.
- Better to touch all areas than perfect one
- You can always add notes after
- Next week you'll be faster

---

## After Your Review

### 📍 Where's My Data?

Your review is saved in:
```
data/
└── reviews/
    └── 2025-W04/
        ├── summary.json
        ├── mind_sweep.json
        ├── projects.json
        └── priorities.json
```

### 🎯 What Now?

1. **Put your top 3 priorities somewhere visible**
2. **Schedule time blocks for priority #1**
3. **Set a reminder for next week's review**

---

## Quick Tips for Success

### 🌟 Best Practices
- Same time each week builds habit
- Sunday evening or Monday morning work well
- Treat it like an important meeting

### ⚠️ Common Mistakes
- Don't skip the timer (it's helping you!)
- Don't judge your mind sweep items
- Don't try to solve problems during review (capture only)

---

## Need More Help?

- **ADHD-specific tips**: See [ADHD Success Guide](./adhd-guide.md)
- **Technical issues**: See [Troubleshooting](../tutorial/getting-started.md#troubleshooting)
- **Customization**: See [Configuration Guide](../reference/configuration.md)

---

## You're Ready! 🚀

Remember: **Done is better than perfect.**

The review works even if you:
- Zone out sometimes
- Give short answers
- Feel rushed

Just showing up is 80% of success.

**Start your first review now:**
```bash
./scripts/deployment/docker-run.sh
```