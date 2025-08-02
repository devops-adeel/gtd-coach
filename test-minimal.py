#!/usr/bin/env python3
"""
Minimal test for GTD Coach
"""

import requests
import json

# Test basic connectivity
print("Testing basic LM Studio connection...")

try:
    response = requests.post("http://localhost:1234/v1/chat/completions", 
        json={
            "model": "meta-llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "You are a GTD coach."},
                {"role": "user", "content": "Hello, I'd like to start a review."}
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }, 
        timeout=5)
    
    response.raise_for_status()
    result = response.json()
    message = result['choices'][0]['message']['content']
    
    print("✅ Success!")
    print(f"Response: {message}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nDebug info:")
    print("- Check server: lms server status")
    print("- Check models: lms ps")