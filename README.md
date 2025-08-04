# GTD Coach for ADHD

A structured, time-boxed weekly review system powered by LM Studio and designed specifically for ADHD minds.

## Quick Start

```bash
# Start the coach system
~/gtd-coach/start-coach.sh

# Or manually start review if server is already running
python3 ~/gtd-coach/gtd-review.py

# Generate weekly summary after reviews
python3 ~/gtd-coach/generate_summary.py
```

## Installation

### Core Requirements
- Python 3.8+
- LM Studio with Llama 3.1 8B model
- macOS (for audio alerts)

### Optional Dependencies
```bash
# Install optional Langfuse for LLM performance tracking
pip install -r requirements.txt
```

## Docker/OrbStack Installation (Recommended)

If you encounter "externally managed environment" errors, use the Docker/OrbStack setup:

### Prerequisites
- [OrbStack](https://orbstack.dev/) or Docker Desktop
- LM Studio running on localhost:1234
- (Optional) Langfuse running on localhost:3000

### Quick Start with Docker
```bash
# Run the weekly review
./docker-run.sh

# Test Langfuse integration
./docker-run.sh test

# Generate weekly summary
./docker-run.sh summary

# Build/rebuild the image
./docker-run.sh build
```

The Docker setup:
- ✅ Avoids Python environment issues
- ✅ Uses host networking to connect to LM Studio and Langfuse
- ✅ Preserves all your data in local directories
- ✅ Handles audio alerts gracefully (disabled in container)

## Features

- **Strict 30-minute time limit** with phase-based structure
- **Audio alerts** at key time intervals (50%, 20%, 10% remaining)
- **ADHD-optimized prompting** - directive, structured, time-aware
- **Automatic logging** of all reviews for pattern tracking
- **Graphiti memory integration** - Tracks patterns, behaviors, and productivity insights
- **Weekly summaries** - AI-generated reports with ADHD-specific insights
- **Simple timer utility** for other time-boxing needs

## Directory Structure

```
~/gtd-coach/
├── scripts/
│   └── timer.sh                # Standalone timer with audio alerts
├── prompts/
│   └── system-prompt.txt       # ADHD coach personality
├── data/
│   ├── mindsweep_*.json        # Captured items from reviews
│   ├── priorities_*.json       # Prioritized actions
│   └── graphiti_batch_*.json   # Memory episodes for Graphiti
├── logs/
│   └── review_*.json           # Complete review transcripts
├── summaries/
│   └── weekly_summary_*.md     # AI-generated weekly insights
├── gtd-review.py               # Main review orchestrator
├── graphiti_integration.py     # Memory management interface
├── adhd_patterns.py            # ADHD pattern detection
├── generate_summary.py         # Weekly insights generator
├── start-coach.sh              # One-command startup
└── README.md                   # This file
```

## Review Phases

1. **STARTUP (2 min)** - Welcome and setup
2. **MIND SWEEP (10 min)** - Capture everything on your mind
3. **PROJECT REVIEW (12 min)** - Quick next-action decisions
4. **PRIORITIZATION (5 min)** - ABC priority assignment
5. **WRAP-UP (3 min)** - Save and celebrate

## Memory & Pattern Tracking

The GTD Coach now includes Graphiti memory integration that automatically:

- **Tracks behavioral patterns**: Task switching frequency, focus indicators, coherence scores
- **Captures all interactions**: Every conversation with the coach is stored for analysis
- **Detects ADHD patterns**: Based on linguistic markers from research
- **Generates weekly summaries**: Actionable insights with personalized recommendations

### Viewing Your Insights

```bash
# Generate a weekly summary (analyzes last 7 days)
python3 ~/gtd-coach/generate_summary.py

# View generated summaries
ls ~/gtd-coach/summaries/
```

### What Gets Tracked

1. **Mind Sweep Patterns**
   - Topic distribution and switches
   - Coherence scores (how organized your thoughts are)
   - Common themes and recurring items

2. **Productivity Metrics**
   - Session completion rates
   - Average duration per phase
   - Items captured per session

3. **ADHD Indicators**
   - Task switching frequency
   - Focus quality scores
   - Fragmentation patterns

All tracking happens automatically in the background without impacting your review performance.

## LLM Performance Monitoring (Langfuse)

The GTD Coach now includes optional Langfuse integration for tracking LLM performance:

### What Gets Tracked

- **Response Latency**: Time taken for each LLM response per phase
- **Success/Failure Rates**: Track reliability and retry patterns
- **Quality Scores**: Phase-specific response quality based on latency thresholds

### Setup Langfuse Integration

1. **Run Langfuse locally** (if using self-hosted):
   ```bash
   # With Docker/OrbStack
   docker run -p 3000:3000 langfuse/langfuse
   ```

2. **Configure your keys** in `langfuse_tracker.py`:
   ```python
   LANGFUSE_PUBLIC_KEY = "pk-lf-your-key-here"
   LANGFUSE_SECRET_KEY = "sk-lf-your-key-here"
   ```

3. **Test the integration**:
   ```bash
   python3 ~/gtd-coach/test_langfuse.py
   ```

4. **Start your review** - Langfuse tracking is automatic when configured:
   ```bash
   ~/gtd-coach/start-coach.sh
   ```

### Viewing Performance Data

Access your Langfuse UI at http://localhost:3000 to see:
- Session traces with nested phases
- Latency breakdowns per interaction
- Success/failure patterns
- Quality score trends

The integration gracefully falls back to direct API calls if Langfuse is unavailable.

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
- **[GRAPHITI_INTEGRATION.md](GRAPHITI_INTEGRATION.md)** - Technical details of memory integration
- **[LANGFUSE_INTEGRATION.md](LANGFUSE_INTEGRATION.md)** - LLM performance monitoring setup
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker/OrbStack deployment guide

## Recent Enhancements (August 2025)

- **Robust Error Handling**: Automatic retry with exponential backoff and fallback to simple prompts
- **Comprehensive Logging**: Session-based logging with unique IDs for debugging and tracking
- **Data Validation**: Automatic cleanup of empty entries and validation of priority values
- **Optimized Phase Settings**: Each phase has tuned temperature and token limits for best results
- **Enhanced Server Checks**: Detailed status about LM Studio server and loaded models
- **Connection Pooling**: Better performance through HTTP keep-alive connections
- **Graphiti Memory Integration**: Automatic pattern tracking, ADHD behavior detection, and weekly summaries
- **ADHD Pattern Detection**: Research-based algorithms for task switching and focus analysis
- **Langfuse Observability**: LLM performance tracking with latency monitoring and quality scoring

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md#recent-enhancements-august-2025) for details.

## Future Enhancements

- [ ] Timing app integration for automatic project list
- [x] Graphiti memory for pattern tracking (Implemented August 2025)
- [ ] Review metrics dashboard
- [ ] Custom MCP tools for advanced features
- [ ] Real-time Graphiti MCP integration (currently using batch files)

## Tips for ADHD Success

1. **Same time, same place** - Schedule reviews consistently
2. **Phone in another room** - Eliminate distractions
3. **Stand up during review** - Movement helps focus
4. **Trust the timer** - Let it be your external brain
5. **Celebrate completion** - You showed up, that's what matters!

Remember: A messy completed review beats a perfect abandoned one!