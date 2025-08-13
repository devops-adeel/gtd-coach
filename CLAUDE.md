# CLAUDE.md - AI Assistant Guidance

## Quick Reference for AI Assistants

When working with this codebase:

### Critical ADHD Features (DO NOT REMOVE)
- **30-minute time limit** - Non-negotiable for ADHD brain
- **Audio alerts** - Essential for time blindness
- **Phase structure** - Provides external executive function
- **Automatic saves** - Compensates for working memory issues

### Docker-First Execution
```bash
# ALWAYS use Docker for Python scripts
./scripts/deployment/docker-run.sh

# Timer is native bash (no Docker needed)
./scripts/timer.sh 1 "Test"
```

### Main Documentation
- [Getting Started Tutorial](docs/tutorial/getting-started.md)
- [Setup Guide](docs/how-to/setup.md)
- [Architecture Overview](docs/explanation/architecture.md)
- [Configuration Reference](docs/reference/configuration.md)

### When Modifying Code
1. Preserve time-boxing functionality
2. Maintain audio alert system
3. Keep phases under time limits
4. Test with `demo-review.py` first

See full documentation in `docs/` directory.