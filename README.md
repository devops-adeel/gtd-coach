# GTD Coach - ADHD-Optimized Weekly Review System

> 🧠 **Transform ADHD chaos into clarity in 30 minutes**  
> A phase-based coaching system that acts as your external executive function

## Quick Start (2 minutes)

```bash
# Clone and setup
git clone https://github.com/yourusername/gtd-coach.git
cd gtd-coach
pip install -r requirements.txt

# Configure
cp config/.env.example .env
# Edit .env with your LM Studio URL

# Run your review
python -m gtd_coach
```

**That's it!** Follow the coach for 30 minutes.

## 📚 Documentation

| Audience | Guide | Description |
|----------|-------|-------------|
| **Users** | [USER_GUIDE.md](docs/USER_GUIDE.md) | How to run weekly reviews |
| **Developers** | [DEVELOPER.md](docs/DEVELOPER.md) | Architecture & contributing |
| **Everyone** | [CONFIGURATION.md](docs/CONFIGURATION.md) | All settings explained |

### Integration Guides
- [Langfuse Setup](docs/integrations/langfuse.md) - LLM observability
- [Graphiti Memory](docs/integrations/graphiti.md) - Knowledge graph
- [Timing App](docs/integrations/timing.md) - Time tracking

## ✨ Features

### Core Functionality
- **30-minute time-boxed reviews** - Five phases with strict timing
- **ADHD-specific coaching** - External executive function support
- **Local LLM integration** - Privacy-first with LM Studio
- **Audio alerts** - Stay on track with timer notifications
- **Pattern detection** - Track ADHD behaviors over time

### Optional Integrations
- **Timing App** - Real project time tracking
- **Langfuse** - LLM performance monitoring
- **Graphiti** - Long-term memory with knowledge graphs

## How It Works

```
STARTUP → MIND SWEEP → PROJECT REVIEW → PRIORITIZATION → WRAP-UP
(2 min)   (10 min)      (12 min)         (5 min)          (3 min)
```

Each phase has:
- ⏰ Strict time limits with audio alerts
- 🎯 Clear objectives
- 🤖 AI coaching support
- 📊 Progress tracking

## Requirements

### Essential
- Python 3.10+
- [LM Studio](https://lmstudio.ai/) with Llama 3.1 8B model
- 30 minutes of uninterrupted time

### Optional
- Docker for containerized deployment
- Neo4j for Graphiti memory
- Timing app subscription for time tracking

## Installation

### Basic Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example .env
nano .env  # Add your settings

# Test the installation
python -m gtd_coach --check-config
```

### Docker Setup

```bash
# Build and run with Docker
docker compose up gtd-coach

# Or use the convenience script
./scripts/docker-run.sh
```

## Project Structure

```
gtd_coach/              # Main application package
├── coach.py            # Core GTD coach orchestrator
├── evaluation/         # LLM-as-a-Judge evaluation system
├── experiments/        # N-of-1 experiment framework
├── integrations/       # External service integrations
├── metrics/            # North Star metrics & adaptive thresholds
└── patterns/           # ADHD pattern detection & analysis

config/                 # Configuration files
├── evaluation/        # Judge configuration
├── experiments/       # N-of-1 experiment schedules
└── pattern_learning/  # Pattern detection settings

docs/                   # Documentation
├── development/        # Development & implementation docs
└── integrations/       # Integration guides

scripts/                # Utility scripts
├── analysis/          # Data analysis tools
├── maintenance/       # Cleanup & maintenance scripts
└── validation/        # Testing & validation tools

tests/                  # Test suite
├── unit/              # Unit tests
└── integration/       # Integration tests

data/                   # Session data (gitignored)
logs/                   # Session logs (gitignored)
summaries/             # Weekly summaries (gitignored)
```

## Configuration

Create a `.env` file:

```bash
# Required
LM_STUDIO_URL=http://localhost:1234/v1

# Optional integrations
TIMING_API_KEY=your-key
LANGFUSE_PUBLIC_KEY=pk-lf-...
NEO4J_PASSWORD=your-password

# Customization
COACHING_STYLE=firm  # or 'gentle'
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

## Usage Examples

### Basic Review
```bash
python -m gtd_coach
```

### With Debug Logging
```bash
LOG_LEVEL=DEBUG python -m gtd_coach
```

### Resume Interrupted Session
```bash
python -m gtd_coach --resume
```

### Generate Weekly Summary
```bash
python scripts/generate_summary.py
```

## Development

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=gtd_coach

# Format code
black gtd_coach/
```

See [DEVELOPER.md](docs/DEVELOPER.md) for architecture details.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LM Studio not responding | Check model is loaded, verify URL in `.env` |
| No audio alerts | macOS: Check terminal permissions, Linux: Install `sox` |
| Review interrupted | Data auto-saved, run with `--resume` flag |

## Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Write tests for new code
4. Submit a pull request

See [DEVELOPER.md](docs/DEVELOPER.md#contributing) for guidelines.

## Why GTD Coach?

Traditional GTD tools fail for ADHD because they:
- Require self-directed executive function
- Allow infinite time for tasks
- Don't prevent hyperfocus traps
- Lack external accountability

GTD Coach solves this by:
- ✅ Providing external executive function
- ✅ Enforcing time boundaries
- ✅ Preventing analysis paralysis
- ✅ Creating completion momentum

## Community & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/gtd-coach/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/gtd-coach/discussions)
- **Email**: support@example.com

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Built for the ADHD community
- Powered by Llama 3.1 via LM Studio
- Inspired by David Allen's GTD methodology

---

**Remember**: Done is better than perfect. Every completed review is a win! 🎉