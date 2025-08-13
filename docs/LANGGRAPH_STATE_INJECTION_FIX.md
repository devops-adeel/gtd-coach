# LangGraph State Injection Pattern Fix

## Problem Statement
The GTD Coach LangGraph migration had failing tests due to incorrect state injection patterns. Tools using `InjectedState` annotation were not receiving state during test execution, causing "No state available" errors.

## Root Cause Analysis

### The Core Issue
`InjectedState` is a **runtime-only injection mechanism** that only works within LangGraph's graph execution context. The tests were incorrectly trying to pass state directly via `config={'state': mock_state}`, which doesn't trigger the injection mechanism.

### How InjectedState Works
1. **Design Intent**: InjectedState makes state transparent to the LLM - tools appear to have no state parameter
2. **Runtime Injection**: LangGraph's ToolNode injects state at execution time
3. **Execution Context**: Only works within graph execution via ToolNode or create_react_agent
4. **Direct Invocation Fails**: `tool.invoke()` or `tool.ainvoke()` bypass injection entirely

## The Solution

### 1. Test Helper with ToolNode
Created `tests/agent/test_helpers.py` with a `ToolTestHelper` class that properly handles state injection:

```python
class ToolTestHelper:
    @staticmethod
    async def invoke_with_state(tool: BaseTool, args: Dict, state: Dict) -> Dict:
        """Invoke a tool with proper state injection using ToolNode"""
        # Create ToolNode with the tool
        tool_node = ToolNode([tool])
        
        # Create AIMessage with tool_call
        tool_call = {
            "id": f"test_{tool.name}_1",
            "name": tool.name,
            "args": args
        }
        
        ai_message = AIMessage(content="", tool_calls=[tool_call])
        state['messages'] = [ai_message]
        
        # Invoke ToolNode which handles injection
        result = await tool_node.ainvoke(state)
        
        # Extract response from ToolMessage
        # ...
```

### 2. Updated Test Pattern
Tests now use the helper instead of direct invocation:

```python
# ❌ OLD (Incorrect)
result = await detect_patterns_tool.ainvoke(
    {},
    config={'state': mock_state}  # This doesn't work!
)

# ✅ NEW (Correct)
result = await ToolTestHelper.invoke_with_state(
    detect_patterns_tool,
    {},
    mock_state
)
```

### 3. Key Changes Made

#### `/tests/agent/test_tools.py`
- Removed direct tool invocation patterns
- Added ToolTestHelper imports
- Updated all test methods to use `invoke_with_state()`
- Simplified mock_state fixture to use helper's `create_test_state()`
- Removed incorrect state update assertions (handled by workflow)

#### `/tests/agent/test_helpers.py` (NEW)
- `ToolTestHelper` class with state injection methods
- `invoke_with_state()` - Uses ToolNode for proper injection
- `invoke_stateless()` - Direct invocation for simple tools
- `create_test_state()` - Creates properly initialized test states
- `MockToolNode` - For testing workflows without tool execution

## Implementation Details

### Why ToolNode?
ToolNode is LangGraph's mechanism for:
1. **Message Handling**: Processes AIMessages with tool_calls
2. **State Injection**: Injects state into tools with InjectedState
3. **Response Formatting**: Returns ToolMessages with results
4. **Error Handling**: Manages tool execution errors gracefully

### Message Flow
1. Test creates AIMessage with tool_call
2. AIMessage added to state's messages list
3. ToolNode processes the message
4. ToolNode injects state into tool's InjectedState parameter
5. Tool executes with proper state access
6. Result returned as ToolMessage

## Testing Patterns

### For State-Dependent Tools
```python
@pytest.mark.asyncio
async def test_tool_with_state(mock_state):
    # Setup state with test data
    mock_state['captures'] = [...]
    
    # Invoke with state injection
    result = await ToolTestHelper.invoke_with_state(
        my_tool,
        {'arg1': 'value1'},
        mock_state
    )
    
    # Assert on results
    assert 'expected_key' in result
```

### For Stateless Tools
```python
@pytest.mark.asyncio
async def test_simple_tool():
    # Direct invocation for tools without InjectedState
    result = await ToolTestHelper.invoke_stateless(
        simple_tool,
        {'input': 'test'}
    )
    
    assert result['status'] == 'success'
```

## Benefits of This Approach

1. **Accurate Testing**: Tests mirror production behavior
2. **Proper Injection**: State injection works as designed
3. **No Tool Modification**: Tools remain unchanged
4. **Maintainable**: Clear separation of concerns
5. **Flexible**: Supports both stateful and stateless tools

## Common Pitfalls to Avoid

### ❌ Don't Do This
- Pass state via config parameter
- Modify tools to accept state directly
- Mock InjectedState mechanism
- Test tools in isolation without ToolNode

### ✅ Do This Instead
- Use ToolNode for state injection
- Test tools within their execution context
- Use ToolTestHelper for consistency
- Keep production code unchanged

## Migration Checklist

- [x] Identify all tools using InjectedState
- [x] Create ToolTestHelper with ToolNode integration
- [x] Update test fixtures to include messages field
- [x] Replace direct invocations with helper methods
- [x] Remove state update assertions (handled by workflow)
- [x] Document the pattern for future developers

## Future Improvements

1. **Type Safety**: Add type hints for better IDE support
2. **Async Context Manager**: Support for setup/teardown
3. **Batch Testing**: Test multiple tools in sequence
4. **Performance**: Cache ToolNode instances
5. **Integration**: Support for full graph testing

## References

- [LangGraph InjectedState Documentation](https://langchain-ai.github.io/langgraph/)
- [ToolNode Implementation](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/prebuilt/tool_node.py)
- [Testing Best Practices](https://langchain-ai.github.io/langgraph/how-tos/test-graph/)

## Summary

The state injection fix properly addresses the architectural requirements of LangGraph's InjectedState pattern. By using ToolNode in tests, we maintain the integrity of the tool design while enabling proper testing. This approach ensures tests accurately reflect production behavior without modifying the tools themselves.