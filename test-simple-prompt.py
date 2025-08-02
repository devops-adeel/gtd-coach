#!/usr/bin/env python3
"""Test with simple prompt"""

import requests
from pathlib import Path

# Load simple prompt
with open(Path.home() / "gtd-coach" / "prompts" / "system-prompt-simple.txt", 'r') as f:
    system_prompt = f.read()

print("Testing with simple system prompt...")
print(f"Prompt length: {len(system_prompt)} characters")

response = requests.post("http://localhost:1234/v1/chat/completions", 
    json={
        "model": "meta-llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "I'm ready to start my weekly review."}
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }, 
    timeout=15)

if response.status_code == 200:
    print("\n✅ Success!")
    print("\nCoach response:")
    print("-" * 50)
    print(response.json()['choices'][0]['message']['content'])
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)