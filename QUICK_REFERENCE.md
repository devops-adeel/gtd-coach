# 📋 GTD Coach Quick Reference

**Print this page and keep it handy during reviews!**

---

## 🚀 Start Commands

```bash
# Full startup (checks everything)
./start-coach.sh

# Docker commands
./docker-run.sh          # Run review
./docker-run.sh timing   # Test Timing
./docker-run.sh summary  # Weekly insights
./docker-run.sh build    # Rebuild after changes
```

---

## ⏱️ Phase Timeline (30 Minutes)

```
┌─────────────────────────────────────┐
│ PHASE          TIME   YOUR JOB      │
├─────────────────────────────────────┤
│ 1. Startup     2 min  Say "ready"   │
│ 2. Mind Sweep  10 min Brain dump    │
│    - Capture   5 min  Type all      │
│    - Process   5 min  Review        │
│ 3. Projects    12 min Next actions  │
│ 4. Prioritize  5 min  A/B/C rank    │
│ 5. Wrap-up     3 min  Celebrate!    │
└─────────────────────────────────────┘
```

---

## ⌨️ During Review

### Mind Sweep Commands
- **Type item** + `Enter` = Add item
- **Empty line** + `Enter` = Offer to exit
- **`Ctrl+C`** = Force end phase

### Project Review
- **Type action** = Set next action
- **`skip`** = Skip this project
- **45 seconds** = Auto-advance

### Priorities
- **`A,B,C`** = Enter as comma-separated
- **A** = Must do this week
- **B** = Should do
- **C** = Nice to have

---

## 📊 Metrics Explained

### Focus Score (0-100)
```
90-100 🟢 Excellent - Minimal switching
70-89  🟢 Good - Well managed
50-69  🟡 Moderate - Room to improve
30-49  🟠 Scattered - Need strategies
0-29   🔴 Crisis - Major intervention
```

### Alignment Score (%)
```
70%+ ✅ Great - Time matches priorities
40-69% ⚠️ Drift - Some adjustment needed
<40% ❌ Misaligned - Reality check time
```

### Context Switches/Hour
```
<3    🟢 Low - Great focus
3-6   🟡 Normal - Manageable
6-10  🟠 High - Feeling scattered
>10   🔴 Very high - Intervention needed
```

---

## 🔧 Configuration Files

```bash
# Timing API setup
.env
├── TIMING_API_KEY=your-key
└── TIMING_MIN_MINUTES=30

# Coach personality
prompts/system-prompt.txt

# Phase timings
gtd-review.py (line ~420)
```

---

## 📁 Data Locations

```
~/gtd-coach/
├── data/
│   ├── mindsweep_*.json      # Brain dumps
│   ├── priorities_*.json     # A/B/C items
│   └── graphiti_batch_*.json # Memory
├── logs/
│   └── review_*.json          # Full sessions
└── summaries/
    └── weekly_summary_*.md    # Insights
```

---

## 🆘 Quick Fixes

| Problem | Solution |
|---------|----------|
| **LM Studio not running** | `lms server start` |
| **Model not loaded** | `lms load meta-llama-3.1-8b-instruct` |
| **No Timing data** | Check `.env` has API key |
| **Python errors** | Use Docker: `./docker-run.sh` |
| **Timeout errors** | Try again in 30 seconds |

---

## 🎯 ADHD Success Tips

### Before Starting
- ☕ Caffeine ready
- 📱 Phone away
- 🚶 Stand up
- 💧 Water nearby

### During Review
- ⏰ Trust the timer
- 📝 Don't filter thoughts
- 🎯 First instinct = best
- ✅ Done > Perfect

### After Review
- 🎉 Celebrate!
- 📊 Check summary
- 📅 Schedule next
- 🏃 Quick walk

---

## 📈 Weekly Summary

```bash
# Generate insights
./docker-run.sh summary

# View results
cat ~/gtd-coach/summaries/weekly_summary_*.md
```

**What you'll see:**
- Focus score trends
- Alignment analysis
- Time sinks
- ADHD patterns
- Recommendations

---

## 🔄 Timing Integration

### Setup (Once)
1. Get API key: https://web.timingapp.com
2. Add to `.env`: `TIMING_API_KEY=xxx`
3. Test: `./docker-run.sh timing`

### What It Tracks
- Context switches (<5 min)
- Focus periods (>30 min)
- Scatter periods (3+ switches/15min)
- Project alignment
- Time sinks

---

## 💡 Remember

**The best review is a done review!**

- ✅ Messy completion > Perfect procrastination
- ✅ 70% accurate > 0% done
- ✅ Weekly habit > Daily perfection
- ✅ Progress > Perfection

---

## 🔗 Help & Support

- **Full guide**: [USAGE_GUIDE.md](USAGE_GUIDE.md)
- **Troubleshooting**: [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- **Timing setup**: [TIMING_SETUP.md](TIMING_SETUP.md)
- **GitHub**: https://github.com/devops-adeel/gtd-coach

---

*GTD Coach v2.0 - Built for ADHD brains* 🧠