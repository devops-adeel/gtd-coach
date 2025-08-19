#!/usr/bin/env python3
"""Test ReAct agent streaming"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
import logging

logging.basicConfig(level=logging.INFO)

# Create a simple tool
@tool
def test_tool(query: str) -> str:
    """A test tool that echoes the query"""
    return f"Echo: {query}"

# Create LLM
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    model="meta-llama-3.1-8b-instruct",
    temperature=0.7,
    max_tokens=100,
    streaming=True,
    timeout=30,
)

# Create agent
agent = create_react_agent(llm, [test_tool])

# Test streaming
state = {
    "messages": [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello, please respond briefly.")
    ]
}

config = {"configurable": {"thread_id": "test"}}

print("Testing ReAct agent streaming...")
try:
    chunks = []
    for chunk in agent.stream(state, config, stream_mode="values"):
        print(f"Chunk keys: {chunk.keys() if isinstance(chunk, dict) else type(chunk)}")
        chunks.append(chunk)
        if isinstance(chunk, dict) and "messages" in chunk:
            last_msg = chunk["messages"][-1] if chunk["messages"] else None
            if last_msg:
                print(f"  Last message: {type(last_msg).__name__}: {str(last_msg)[:100]}")
    
    print(f"\nReceived {len(chunks)} chunks")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()