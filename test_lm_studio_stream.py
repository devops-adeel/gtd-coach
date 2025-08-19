#!/usr/bin/env python3
"""Test LM Studio streaming directly"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import logging

logging.basicConfig(level=logging.DEBUG)

# Test with the configured model
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    model="meta-llama-3.1-8b-instruct",
    temperature=0.7,
    max_tokens=100,
    streaming=True,
    timeout=30,
)

print("Testing streaming with meta-llama-3.1-8b-instruct...")
try:
    chunks = []
    for chunk in llm.stream([HumanMessage(content="Say hello in 5 words")]):
        print(f"Chunk: {chunk}")
        chunks.append(chunk)
    
    if chunks:
        print(f"\nReceived {len(chunks)} chunks")
    else:
        print("\nNo chunks received!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()