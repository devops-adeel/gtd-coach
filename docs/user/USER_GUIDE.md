# GTD Coach User Guide

**30-minute ADHD-friendly weekly reviews that actually work**

## Quick Start Checklist

□ **LM Studio** running (port 1234) with Llama 3.1 8B loaded  
□ **30 minutes** blocked - no interruptions  
□ **Phone** in another room  
□ **Water** ready  

```bash
# Start your review
./scripts/deployment/docker-run.sh
```

---

## Common Tasks

### 📅 Weekly Review
**Command:** `./scripts/deployment/docker-run.sh`  
**Time:** 30 minutes  
**Phases:** 
- STARTUP (2m) → Welcome & setup
- MIND SWEEP (10m) → Dump everything 
- PROJECTS (12m) → One next action each
- PRIORITIES (5m) → ABC ranking
- WRAP-UP (3m) → Save & celebrate

**During review:**
- Type `skip` to skip items
- Type `help` for assistance
- Empty line + `y` to finish early

### 🎯 Daily Capture
**Command:** `python -m gtd_coach capture`  
**Time:** 10 minutes  
**Purpose:** Quick brain dump & clarify  

Options:
- `--skip-timing` - Skip Timing app data
- `--voice` - Enable voice capture

### ⏰ Test Timer
**Command:** `./scripts/timer.sh 5 "Time's up!"`  
**Purpose:** Test audio alerts work  

Audio alerts:
- 50% → Gentle chime
- 20% → Warning bell  
- 10% → Urgent alert

### 📊 Check Timing Alignment
**Command:** `python -m gtd_coach daily`  
**Purpose:** See if your time matches GTD priorities  

Options:
- `--notify` - macOS notification
- `--email` - Send report

### 🔧 Setup Timing Projects
**Command:** `python -m gtd_coach setup-timing`  
**Purpose:** Create GTD projects in Timing app  
**Options:** `--include-contexts` for @contexts

---

## Commands Reference

| Task | Command | Time | Notes |
|------|---------|------|-------|
| **Weekly Review** | `./scripts/deployment/docker-run.sh` | 30m | Main GTD review |
| **Daily Capture** | `python -m gtd_coach capture` | 10m | Quick clarify |
| **Test Timer** | `./scripts/timer.sh 5 "Done"` | 5m | Audio check |
| **Resume Session** | `python -m gtd_coach --resume` | Varies | After interrupt |
| **Docker Shell** | `./scripts/deployment/docker-run.sh shell` | - | Debug access |
| **Run Tests** | `./scripts/test-orbstack.sh` | - | In container |

---

## Integration Setup

<details>
<summary>🕐 Timing App (Focus Metrics)</summary>

```bash
# Add to .env
TIMING_API_KEY=your-key-here
TIMING_MIN_MINUTES=30

# Test connection
./scripts/deployment/docker-run.sh timing
```
Get key from: https://web.timingapp.com
</details>

<details>
<summary>📊 Langfuse (Observability)</summary>

```bash
# Add to .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Test connection
./scripts/deployment/docker-run.sh test
```
Sign up at: https://cloud.langfuse.com
</details>

<details>
<summary>🧠 FalkorDB/Graphiti (Memory)</summary>

```bash
# Add to .env
FALKORDB_HOST=localhost
FALKORDB_PORT=6380
FALKORDB_DATABASE=shared_gtd_knowledge
OPENAI_API_KEY=your-key

# Test connection
python3 scripts/maintenance/check_neo4j_state.py
```
Shared knowledge persists across sessions
</details>

<details>
<summary>✅ Todoist (Task Sync)</summary>

```bash
# Add to .env
TODOIST_API_KEY=your-token
TODOIST_PROJECT_ID=project-id  # Optional

# Syncs during WRAP-UP phase
```
Get token from: https://todoist.com/app/settings/integrations
</details>

---

## Troubleshooting

### LM Studio not responding?
```bash
# Check if running
curl http://localhost:1234/v1/models

# Restart LM Studio
# Load model: meta-llama-3.1-8b-instruct
```

### Audio alerts not working?
- **macOS:** System Preferences → Security → Privacy → Allow terminal
- **Linux:** `sudo apt-get install sox`
- **Windows:** Visual alerts only

### Review interrupted?
```bash
# Resume where you left off
python -m gtd_coach --resume
```

### Docker issues?
```bash
# Rebuild clean
docker compose build --no-cache

# Check logs
docker compose logs -f gtd-coach
```

### Can't find your data?
- Mind sweeps: `data/mindsweep_*.json`
- Priorities: `data/priorities_*.json`  
- Session logs: `logs/review_*.json`
- Summaries: `summaries/week_*.md`

---

## ADHD Tips

### Before Starting
✓ **Block time** - Full 30 minutes, no exceptions  
✓ **Remove distractions** - Phone away, notifications off  
✓ **Stand up** - Movement helps focus  
✓ **Timer visible** - External time awareness  

### During Review
✓ **Trust the timer** - Don't fight it  
✓ **Quantity over quality** - More is better in mind sweep  
✓ **One decision** - Each project needs ONE next action  
✓ **Skip is OK** - Better to skip than get stuck  

### After Review
✓ **Check summary** - `summaries/` folder  
✓ **Calendar block** - Schedule A priorities NOW  
✓ **Celebrate** - You did it!  
✓ **Same time next week** - Consistency matters  

---

## Emergency Commands

**Pause everything:** `Ctrl+C`  
**Skip current item:** Type `skip`  
**Get help:** Type `help`  
**Finish phase early:** Empty line then `y`  

---

*Remember: Done is better than perfect. Every completed review is a win!*