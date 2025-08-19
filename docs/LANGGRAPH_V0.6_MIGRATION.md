# LangGraph v0.6 Migration Guide

## Overview
This document outlines the breaking changes and migration patterns when upgrading from LangGraph v0.2 to v0.6. Many test failures in the GTD Coach codebase are due to test implementation issues rather than production code bugs.

## Breaking Changes

### 1. Tool Invocation API
**Old (v0.2):**
```python
result = tool.run({"query": "test"}, state)  # State passed explicitly
```

**New (v0.6):**
```python
result = tool.invoke({"query": "test"})  # State injected automatically via InjectedState
```

**Key Points:**
- Tools no longer have a `.run()` method - use `.invoke()` instead
- The `.run()` method was deprecated in v0.1.47 and removed in langchain-core 1.0
- Tools can be sync or async - both use `.invoke()` (or `.ainvoke()` for async)

### 2. State Injection with InjectedState

**Old Pattern (v0.2):**
```python
@tool
def my_tool(query: str, state: dict) -> str:
    """Tool that receives state explicitly"""
    user_id = state.get("user_id")
    return f"Result for {user_id}"

# In tests:
result = my_tool.run({"query": "test"}, {"user_id": "123"})
```

**New Pattern (v0.6):**
```python
from typing import Annotated
from langgraph.prebuilt import InjectedState

@tool
def my_tool(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Tool with injected state - state not exposed to LLM"""
    user_id = state.get("user_id")
    return f"Result for {user_id}"

# In tests - state is injected by framework:
result = my_tool.invoke({"query": "test"})  # No state parameter!
```

**Important:**
- InjectedState parameters are NOT exposed in the tool's schema to the LLM
- State is automatically injected by LangGraph during execution
- Tests need proper graph context for state injection to work

### 3. Interrupt and Resume Pattern

**Old Pattern (v0.2):**
```python
from langgraph.errors import NodeInterrupt

def my_node(state):
    # Old way - throwing exception
    raise NodeInterrupt("Need user input")
    
# In tests - expecting exception:
with pytest.raises(NodeInterrupt):
    my_node(state)
```

**New Pattern (v0.6):**
```python
from langgraph.types import interrupt, Command

def my_node(state):
    # New way - using interrupt function
    user_input = interrupt("Need user input")
    return {"value": user_input}

# In tests - check __interrupt__ field:
result = graph.invoke(state, config)
assert "__interrupt__" in result
assert result["__interrupt__"][0]["resumable"] == True

# Resume with Command:
resumed = graph.invoke(Command(resume="user_value"), config)
```

**Key Changes:**
- Import from `langgraph.types` not `langgraph.errors`
- `interrupt()` is a function that pauses execution, not an exception
- Check `__interrupt__` field in result, not exception
- Resume using `Command(resume=value)` pattern

### 4. Workflow Compilation and Execution

**Old Pattern (v0.2):**
```python
workflow = WeeklyReviewWorkflow()
result = workflow.run(initial_state)
```

**New Pattern (v0.6):**
```python
from langgraph.checkpoint.memory import InMemorySaver

workflow = WeeklyReviewWorkflow()
checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "unique_id"}}
result = graph.invoke(initial_state, config)
```

**Requirements:**
- Always compile workflows to graphs before execution
- Provide a checkpointer (e.g., InMemorySaver) for state persistence
- Include config with thread_id for state management

### 5. Checkpointing Configuration

**Required for all graphs with interrupts or state persistence:**
```python
from langgraph.checkpoint.memory import InMemorySaver

# Create checkpointer
checkpointer = InMemorySaver()

# Compile with checkpointer
graph = builder.compile(checkpointer=checkpointer)

# Always provide config with thread_id
config = {
    "configurable": {
        "thread_id": "unique_thread_id",
        "checkpoint_ns": "namespace"  # Optional
    }
}

# Invoke with config
result = graph.invoke(state, config)
```

## Test Pattern Updates

### 1. Mocking Tools

**Wrong:**
```python
mock_tool = AsyncMock()
mock_tool.run = AsyncMock(return_value="result")
```

**Correct:**
```python
mock_tool = Mock()
mock_tool.name = "my_tool"
mock_tool.invoke = Mock(return_value="result")  # or AsyncMock for async tools
mock_tool.get_input_schema = Mock(return_value={
    "properties": {"query": {"type": "string"}},
    "required": ["query"]
})
```

### 2. Testing Interrupts

**Wrong:**
```python
with pytest.raises(NodeInterrupt):
    result = workflow.run(state)
```

**Correct:**
```python
# Setup
checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "test"}}

# Run until interrupt
result = graph.invoke(state, config)

# Check interrupt
assert "__interrupt__" in result
interrupt_data = result["__interrupt__"][0]
assert interrupt_data["resumable"] == True

# Resume
from langgraph.types import Command
resumed = graph.invoke(Command(resume="user_input"), config)
```

### 3. Testing with InjectedState

**Setup proper context in tests:**
```python
@pytest.fixture
def langgraph_config():
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "checkpoint_ns": "test"
        }
    }

@pytest.fixture
def mock_checkpointer():
    from langgraph.checkpoint.memory import InMemorySaver
    return InMemorySaver()

# In test:
def test_with_injected_state(langgraph_config, mock_checkpointer):
    graph = builder.compile(checkpointer=mock_checkpointer)
    result = graph.invoke(initial_state, langgraph_config)
```

### 4. Stream-based Testing

For step-by-step testing and debugging:
```python
# Stream execution for detailed testing
for chunk in graph.stream(state, config, stream_mode="values"):
    if "__interrupt__" in chunk:
        # Handle interrupt
        break
    # Validate intermediate states
    assert chunk["current_phase"] == expected_phase
```

## Common Issues and Solutions

### Issue 1: AttributeError: 'StructuredTool' object has no attribute 'run'
**Solution:** Replace all `.run()` calls with `.invoke()`

### Issue 2: State not available in tool
**Solution:** Use `InjectedState` annotation and ensure proper graph context

### Issue 3: Tests expecting NodeInterrupt exception
**Solution:** Check for `__interrupt__` field instead of exception

### Issue 4: Workflow.run() not working
**Solution:** Compile workflow to graph and use graph.invoke()

### Issue 5: No thread_id error
**Solution:** Always provide config with thread_id

## Known Limitations

1. **ToolNode with Pydantic schemas**: There are reported issues with ToolNode not detecting InjectedState annotations when tools use Pydantic args_schema
2. **Direct tool testing**: Tools with InjectedState cannot be easily tested in isolation - they need graph context
3. **Migration complexity**: Some tests may need complete rewriting rather than simple updates

## Best Practices

1. **Always use checkpointers** for graphs with state or interrupts
2. **Provide thread_id** in config for all graph invocations
3. **Mock .invoke() method** not the entire tool
4. **Use Command pattern** for resume operations
5. **Test with graph context** for InjectedState tools
6. **Use stream mode** for debugging complex workflows

## References

- [LangGraph v0.6 Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Migration Notes](https://github.com/langchain-ai/langgraph/releases)
- [Tool Calling Guide](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/)
- [Human-in-the-Loop Guide](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)