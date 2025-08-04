# GTD Coach for ADHD

A structured, time-boxed weekly review system powered by LM Studio and designed specifically for ADHD minds.

## Quick Start

```bash
# Start the coach system
~/gtd-coach/start-coach.sh

# Or manually start review if server is already running
python3 ~/gtd-coach/gtd-review.py
```

## Features

- **Strict 30-minute time limit** with phase-based structure
- **Audio alerts** at key time intervals (50%, 20%, 10% remaining)
- **ADHD-optimized prompting** - directive, structured, time-aware
- **Automatic logging** of all reviews for pattern tracking
- **Simple timer utility** for other time-boxing needs

## Directory Structure

```
~/gtd-coach/
├── scripts/
│   └── timer.sh          # Standalone timer with audio alerts
├── prompts/
│   └── system-prompt.txt # ADHD coach personality
├── data/
│   ├── mindsweep_*.json  # Captured items from reviews
│   └── priorities_*.json # Prioritized actions
├── logs/
│   └── review_*.json     # Complete review transcripts
├── gtd-review.py         # Main review orchestrator
├── start-coach.sh        # One-command startup
└── README.md            # This file
```

## Review Phases

1. **STARTUP (2 min)** - Welcome and setup
2. **MIND SWEEP (10 min)** - Capture everything on your mind
3. **PROJECT REVIEW (12 min)** - Quick next-action decisions
4. **PRIORITIZATION (5 min)** - ABC priority assignment
5. **WRAP-UP (3 min)** - Save and celebrate

## Manual Timer Usage

```bash
# Basic timer
~/gtd-coach/scripts/timer.sh 5 "Break time!"

# Pomodoro work session
~/gtd-coach/scripts/timer.sh 25 "Take a break!"
```

## Troubleshooting

### "LM Studio server is not running"
```bash
lms server start
```

### "Model not loaded"
```bash
# List available models
lms ls

# Load the model
lms load meta-llama-3.1-8b-instruct --gpu max
```

### Check what's loaded
```bash
lms ps
```

## Customization

- Edit `prompts/system-prompt.txt` to adjust coaching style
- Modify phase durations in `gtd-review.py`
- Add custom sounds by editing `scripts/timer.sh`

## Documentation

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Complete guide on how to use the coach
- **[QUICK_REFERENCE.txt](QUICK_REFERENCE.txt)** - Printable cheat sheet
- **[SETUP_COMPLETE.md](SETUP_COMPLETE.md)** - Setup confirmation and next steps
- **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - Troubleshooting guide

## Recent Enhancements (August 2025)

- **Robust Error Handling**: Automatic retry with exponential backoff and fallback to simple prompts
- **Comprehensive Logging**: Session-based logging with unique IDs for debugging and tracking
- **Data Validation**: Automatic cleanup of empty entries and validation of priority values
- **Optimized Phase Settings**: Each phase has tuned temperature and token limits for best results
- **Enhanced Server Checks**: Detailed status about LM Studio server and loaded models
- **Connection Pooling**: Better performance through HTTP keep-alive connections

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md#recent-enhancements-august-2025) for details.

## Future Enhancements

- [ ] Timing app integration for automatic project list
- [ ] Graphiti memory for pattern tracking
- [ ] Review metrics dashboard
- [ ] Custom MCP tools for advanced features

## Tips for ADHD Success

1. **Same time, same place** - Schedule reviews consistently
2. **Phone in another room** - Eliminate distractions
3. **Stand up during review** - Movement helps focus
4. **Trust the timer** - Let it be your external brain
5. **Celebrate completion** - You showed up, that's what matters!

Remember: A messy completed review beats a perfect abandoned one!