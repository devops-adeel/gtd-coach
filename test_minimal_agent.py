#!/usr/bin/env python3
"""Test minimal ReAct agent with meta-llama model"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
import logging

logging.basicConfig(level=logging.INFO)

# Create a simple tool
@tool
def simple_tool(query: str) -> str:
    """A simple test tool"""
    return f"Result: {query}"

# Test with meta-llama model (as configured in Docker)
print("Testing minimal ReAct agent with meta-llama-3.1-8b-instruct...")
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    model="meta-llama-3.1-8b-instruct",
    temperature=0.7,
    max_tokens=100,
    streaming=True,
    timeout=30,
)

# Create agent with minimal setup
agent = create_react_agent(llm, [simple_tool])

# Test with minimal state - just messages
state = {
    "messages": [
        HumanMessage(content="Hello")
    ]
}

config = {"configurable": {"thread_id": "test"}}

print("Testing minimal agent...")
try:
    # Test invoke first (non-streaming)
    print("\n1. Testing invoke (non-streaming)...")
    result = agent.invoke(state, config)
    print(f"Success! Got {len(result.get('messages', []))} messages")
    
    # Then test streaming
    print("\n2. Testing stream...")
    chunks = []
    for chunk in agent.stream(state, config, stream_mode="values"):
        chunks.append(chunk)
    print(f"Success! Got {len(chunks)} chunks")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()