#!/usr/bin/env python3
import requests

print("Quick test...")
response = requests.post("http://localhost:1234/v1/chat/completions", 
    json={
        "model": "meta-llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": "Say 'test ok' if you receive this"}],
        "temperature": 0.1,
        "max_tokens": 10
    }, 
    timeout=5)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()['choices'][0]['message']['content']}")