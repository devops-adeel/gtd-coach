# Known Issues and Workarounds

## 1. Timeout with Large System Prompts (RESOLVED)

**Previous Issue**: The full system prompt in `prompts/system-prompt.txt` could cause timeouts when sent to the LLM.

**Resolution Implemented**:
The system now includes robust error handling with automatic retry logic and fallback to a simpler prompt:

1. **Automatic Retry**: Failed requests are retried up to 3 times with exponential backoff
2. **Fallback Prompt**: On the final retry attempt, the system automatically switches to `system-prompt-simple.txt`
3. **Connection Reuse**: HTTP keep-alive connections improve performance
4. **Phase-Specific Settings**: Each phase has optimized temperature and token limits

**New Behavior**:
- If a timeout occurs, you'll see: `⏱️ Timeout on attempt X/3`
- On final attempt: `Switching to simple prompt for final attempt...`
- The review continues normally with the simpler prompt

No manual intervention required!

## 2. Interactive Input in Non-TTY Environment

**Issue**: The script expects interactive input which fails in automated/scripted environments.

**Workaround**: Run the script directly in a terminal, not through automation tools.

## 3. Python Package Installation

**Issue**: macOS requires `--break-system-packages` flag for pip installs.

**Solution**:
```bash
pip3 install --user --break-system-packages requests
```

## Testing the System

For a quick connectivity test:
```bash
python3 ~/gtd-coach/quick-test.py
```

For a non-interactive demo:
```bash
python3 ~/gtd-coach/demo-review.py
```

For the full interactive experience:
```bash
# In a terminal window:
python3 ~/gtd-coach/gtd-review.py
```

## Recent Enhancements (August 2025)

### Error Handling Improvements
1. **Automatic Retry Logic**: LLM requests retry up to 3 times with exponential backoff
2. **Fallback System Prompt**: Automatically switches to simple prompt on final retry
3. **Enhanced Server Checking**: Detailed status messages about LM Studio server and loaded models
4. **Connection Pooling**: HTTP keep-alive for better performance

### Logging System
- Session logs are automatically created in `~/gtd-coach/logs/`
- Each session has a unique ID and detailed logging
- Console shows warnings/errors while file logs contain full details
- Log format: `session_YYYYMMDD_HHMMSS.log`

### Data Validation
- Automatic validation of mind sweep items (removes empty entries)
- Priority validation with fallback to 'C' for invalid inputs
- Session data validation ensures all required fields exist

### Phase Optimization
Each phase now has optimized settings:
- **Startup**: temperature=0.8, max_tokens=300 (warm, welcoming)
- **Mind Sweep**: temperature=0.7, max_tokens=300 (focused capture)
- **Project Review**: temperature=0.8, max_tokens=500 (balanced)
- **Prioritization**: temperature=0.6, max_tokens=400 (deterministic)
- **Wrap-up**: temperature=0.9, max_tokens=400 (celebratory)

### Testing
Run the enhanced test suite:
```bash
python3 ~/gtd-coach/test-enhanced-gtd.py
```

This tests all new features including validation, error handling, and logging.