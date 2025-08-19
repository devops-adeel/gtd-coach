#\!/usr/bin/env python3
"""Test xLAM model directly"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import time

# Test with xLAM model
print("Testing xLAM-7b-fc-r model streaming...")
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    model="xlam-7b-fc-r",
    temperature=0.7,
    max_tokens=50,
    streaming=True,
    timeout=60,
)

try:
    start = time.time()
    chunks = []
    for chunk in llm.stream([HumanMessage(content="Say hello in 3 words")]):
        print(f"Chunk: {chunk.content}")
        chunks.append(chunk)
    
    elapsed = time.time() - start
    print(f"\nReceived {len(chunks)} chunks in {elapsed:.2f} seconds")
    
except Exception as e:
    print(f"Error: {e}")
EOF < /dev/null