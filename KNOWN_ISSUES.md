# Known Issues and Workarounds

## 1. Timeout with Large System Prompts

**Issue**: The full system prompt in `prompts/system-prompt.txt` may cause timeouts when sent to the LLM, especially on first load.

**Symptoms**:
- `requests.exceptions.ReadTimeout` errors
- Script hangs when starting review

**Workarounds**:
1. **Use shorter system prompt**: Edit `prompts/system-prompt.txt` to be more concise
2. **Increase timeout**: In `gtd-review.py`, change line 64 from `timeout=30` to `timeout=60`
3. **Pre-warm the model**: Send a simple request first before the full prompt

**Temporary Fix Applied**:
```python
# In gtd-review.py, you can modify the load_system_prompt method:
def load_system_prompt(self):
    # Use a simplified prompt for now
    system_prompt = """You are an ADHD-specialized GTD coach. 
    Guide the user through a structured 30-minute weekly review.
    Be direct, time-aware, and focused on action."""
    self.messages.append({"role": "system", "content": system_prompt})
```

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