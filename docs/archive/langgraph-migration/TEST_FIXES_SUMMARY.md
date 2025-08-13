# Test Fixes Summary for LangGraph Migration

## Completed Fixes (Phase 1)

### 1. Tool Import Fixes
**File:** `tests/agent/test_async_patterns.py`
- ✅ Fixed incorrect tool imports:
  - `CaptureFromInbox` → `scan_inbox_tool` from `gtd_coach.agent.tools.capture`
  - `ProcessCaptures` → `clarify_items_tool` from `gtd_coach.agent.tools.gtd`
  - `SearchGraphitiMemory` → `search_memory_tool` from `gtd_coach.agent.tools.memory`
  - Removed `CalculateFocusScore` (doesn't exist)

### 2. State Validation Fixes
**File:** `tests/agent/test_state.py`
- ✅ Fixed default workflow_type expectation: `'daily_capture'` → `'ad_hoc'`
- ✅ Fixed StateValidator.validate_phase_transition API:
  - Changed from `(state, from_phase, to_phase)` to `(state, next_phase)`
- ✅ Replaced non-existent `validate_captures` test with `validate_state_consistency` test

### 3. Tool Return Value Fixes
**File:** `tests/agent/test_tools.py`

#### Capture Tools:
- ✅ `scan_inbox_tool`: Fixed expected keys
  - `'questions'` → `'prompts'`
  - Added checks for `'example_items'`, `'capture_instruction'`
  
- ✅ `brain_dump_tool`: Fixed expected return structure
  - Removed `'timer_minutes'`, `'technique'`
  - Added `'suggestions'`, `'capture_instruction'`, `'voice_option'`, `'pattern_tracking'`
  
- ✅ `capture_item_tool`: Fixed return expectations
  - `'captured'` is now a dict (not boolean)
  - Removed `'item_id'`
  - Added `'quick_categorization'`, `'patterns_detected'`, `'capture_count'`
  
- ✅ `detect_capture_patterns_tool`: Fixed return structure
  - `'recommendations'` → `'adaptive_recommendation'`
  - Added `'total_captures'`, `'topic_switches'`

#### GTD Tools:
- ✅ `clarify_items_tool`: Added missing return keys
  - Added `'insights'`, `'next_step'`
  
- ✅ `organize_tool`: Fixed expected return structure
  - Fixed state setup (using `captures` with `clarified=True` instead of `processed_items`)
  - Added `'by_priority'`, `'quick_wins'`, `'recommendations'`
  
- ✅ `create_project_tool`: Fixed parameter names and return structure
  - `'name'` → `'title'`
  - `'first_action'` → `'next_action'`
  - Returns `'project'` dict instead of `'created'` boolean
  
- ✅ `prioritize_actions_tool`: Fixed parameters and return values
  - `'method'` → `'criteria'`
  - Fixed return keys to match actual implementation
  - Changed state setup to use `'processed_items'`

### 4. Validation Script Updates
**File:** `validate_langgraph_migration.py`
- ✅ Fixed tool names: `time_check_tool` → `check_time_tool`
- ✅ Fixed tool names: `capture_from_inbox_tool` → `scan_inbox_tool`
- ✅ Fixed StateValidator API usage

## Remaining Issues

### Environment Setup
- ❌ Need to install langgraph dependencies to run tests
- Options:
  1. Use Docker environment with dependencies installed
  2. Create virtual environment with requirements
  3. Update CI/CD to include proper test environment

### Test Execution Command
To run tests when environment is ready:
```bash
# In Docker
scripts/docker-run.sh shell
python3 -m pytest tests/agent/test_tools.py -xvs

# Or with virtual environment
python3 -m venv test_venv
source test_venv/bin/activate
pip install -r requirements.txt
python3 -m pytest tests/agent/test_tools.py -xvs
```

## Summary of Changes

### Files Modified:
1. `/tests/agent/test_async_patterns.py` - Fixed tool imports
2. `/tests/agent/test_state.py` - Fixed state validation expectations
3. `/tests/agent/test_tools.py` - Fixed all tool test expectations
4. `/validate_langgraph_migration.py` - Fixed tool names and API usage

### Key Patterns Fixed:
1. **Tool Naming**: Old test names vs actual implementation names
2. **API Signatures**: Function parameters changed in implementation
3. **Return Values**: Tests expected different keys than tools actually return
4. **State Structure**: Tests used wrong state field names
5. **Default Values**: Tests expected wrong defaults (e.g., workflow_type)

## Next Steps (Phases 2-5)

### Phase 2: Fix test infrastructure (CURRENT)
- [ ] Set up proper test environment with dependencies
- [ ] Fix state injection patterns in remaining test files
- [ ] Update mock configurations

### Phase 3: Fix test expectations
- [ ] Review remaining test files for similar issues
- [ ] Update conditional assertions
- [ ] Fix default value expectations

### Phase 4: Refactor for maintainability
- [ ] Create test fixtures for common patterns
- [ ] Add integration test suite
- [ ] Document test patterns

### Phase 5: Validation and cleanup
- [ ] Run full test suite
- [ ] Fix any remaining failures
- [ ] Update documentation

## Testing Strategy

The fixes follow these principles:
1. **Match Reality**: Tests now match actual tool implementations
2. **Explicit Contracts**: Clear expectations about tool inputs/outputs
3. **Minimal Mocking**: Reduce complexity by testing real behavior
4. **Progressive Enhancement**: Fix foundational issues first