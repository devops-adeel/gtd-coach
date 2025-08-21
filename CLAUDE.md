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

### Test Debugging with Langfuse Traces (MANDATORY)

When running tests that involve agent behavior or model interactions:

1. **ALWAYS query Langfuse traces for failing tests** to understand agent behavior
2. **Use the permanent analysis script** at `scripts/analyze_langfuse_traces.py`
3. **Environment setup required:**
   ```bash
   # Set to enable real Langfuse (not mocked) for agent tests
   export ANALYZE_AGENT_BEHAVIOR=true
   
   # API keys needed (check ~/.env for real keys)
   export LANGFUSE_PUBLIC_KEY=...
   export LANGFUSE_SECRET_KEY=...
   ```

4. **Test failure analysis:**
   - For PASSING tests: No trace output needed
   - For FAILING tests: Automatic trace analysis will display:
     - Complete agent conversation flow
     - Tool calls and responses
     - Interrupt patterns
     - State transitions
     - Error messages and stack traces

5. **Using the analysis script directly:**
   ```bash
   # Analyze recent traces (last hour)
   python scripts/analyze_langfuse_traces.py
   
   # Analyze specific session
   python scripts/analyze_langfuse_traces.py --session SESSION_ID
   
   # Analyze test failure automatically
   python scripts/analyze_langfuse_traces.py --test-failure SESSION_ID
   ```

6. **In pytest tests:**
   - Tests will automatically analyze traces on failure when `ANALYZE_AGENT_BEHAVIOR=true`
   - The `langfuse_analyzer` fixture handles this automatically
   - No code changes needed in individual tests

See full documentation in `docs/` directory.

## Recent Fixes and Maintenance (January 2025)

### Critical Issues Resolved

1. **Docker Disk Space Management**
   - Added log rotation to all services in `docker-compose.yml` (max-size: 10m, max-file: 3)
   - Created `scripts/docker_maintenance.sh` for automated cleanup
   - Implemented disk space monitoring in `gtd_coach/utils/disk_monitor.py`
   - Pre-flight disk space checks in agent runner

2. **Async/Await Compatibility**
   - Fixed `TracedOpenAIEmbedder` to use `LangfuseAsyncOpenAI` for proper async support
   - Resolved "object CreateEmbeddingResponse can't be used in 'await' expression" error

3. **Dynamic Prompt Content**
   - Replaced literal "Project X" with `{project_name}` placeholder in system prompt
   - Allows dynamic injection of actual project names at runtime

### Maintenance Scripts

**Docker Cleanup** (`scripts/docker_maintenance.sh`):
```bash
# Manual cleanup
sudo ./scripts/docker_maintenance.sh

# Setup automated daily cleanup at 2 AM
./scripts/setup_maintenance_cron.sh
```

**Emergency Disk Recovery**:
```bash
# If disk space critical
docker system prune -a --volumes -f
sudo sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'
```

### Monitoring Recommendations

Consider deploying Netdata for real-time monitoring:
```bash
docker run -d --name=netdata \
  -p 19999:19999 \
  -v /etc/passwd:/host/etc/passwd:ro \
  -v /etc/group:/host/etc/group:ro \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --cap-add SYS_PTRACE \
  --security-opt apparmor=unconfined \
  netdata/netdata
```

### Error Prevention

- Docker logs are now automatically rotated
- Disk space is checked before starting reviews
- Async/await operations properly handle Langfuse tracing
- System prompts use dynamic placeholders instead of literal examples