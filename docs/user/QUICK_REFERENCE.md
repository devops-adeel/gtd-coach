# GTD Coach Quick Reference

## Essential Commands

```bash
# Weekly Review (30 min)
./scripts/deployment/docker-run.sh

# Daily Clarify (5-10 min) - NEW!
python3 -m gtd_coach.commands.daily_clarify

# Test Reality Check (1 min)
python3 test_timing_read.py

# Resume Interrupted Session
python -m gtd_coach --resume

# Test Audio Alerts
./scripts/timer.sh 1 "Test!"
```

## Review Phases & Timing

| Phase | Time | Alert Warnings |
|-------|------|----------------|
| STARTUP | 2m | - |
| MIND SWEEP | 10m | 5m, 2m, 1m |
| PROJECTS | 12m | 6m, 2.5m, 1m |
| PRIORITIES | 5m | 2.5m, 1m, 30s |
| WRAP-UP | 3m | 1.5m, 30s, 15s |

## During Review

| Command | Action |
|---------|--------|
| `skip` | Skip current item |
| `help` | Get help |
| `Ctrl+C` | Emergency stop |
| Empty + `y` | Finish phase early |

## Priority Levels

- **A** = Must do this week (max 3-5)
- **B** = Should do if time 
- **C** = Nice to have

## File Locations

```
data/
├── mindsweep_*.json    # Brain dumps
├── priorities_*.json   # ABC rankings
└── .state.json        # Session state

logs/
└── review_*.json      # Full transcripts

summaries/
└── week_*.md          # Weekly summaries
```

## Environment Setup

```bash
# Minimal .env
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=meta-llama-3.1-8b-instruct

# Optional Integrations
TODOIST_API_KEY=...       # Inbox processing (NEW!)
TIMING_API_KEY=...        # Reality checks (read-only)
LANGFUSE_PUBLIC_KEY=...   # Observability
FALKORDB_HOST=localhost   # Memory graph
```

## Docker Commands

```bash
# Build image
./scripts/deployment/docker-run.sh build

# Open shell
./scripts/deployment/docker-run.sh shell  

# View logs
docker compose logs -f gtd-coach

# Clean rebuild
docker compose build --no-cache
```

## Quick Fixes

**LM Studio down?** → Check port 1234  
**No audio?** → macOS terminal permissions  
**Lost data?** → Check `data/` folder  
**Interrupted?** → Use `--resume` flag  
**Todoist empty?** → Check project ID or use auto-detect  
**Timing 401?** → Normal - create 3 projects manually  
**No reality check?** → Run `test_timing_read.py` to verify  

---
*Keep this handy during reviews!*