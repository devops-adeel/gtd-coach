#!/usr/bin/env python3
"""
Test the LLM client connectivity and basic functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.llm import get_llm_client

def main():
    print("Testing LLM Client")
    print("=" * 50)
    
    # Get client
    client = get_llm_client()
    
    # Test connection
    print("\n1. Testing LM Studio connection...")
    if client.test_connection():
        print("   ✅ Connection successful")
    else:
        print("   ❌ Connection failed")
        return 1
    
    # Test basic completion
    print("\n2. Testing chat completion...")
    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, GTD Coach is working!' in exactly those words."}
            ],
            temperature=0.1,
            max_tokens=20,
            session_id="test_session",
            phase="TEST"
        )
        
        result = response.choices[0].message.content
        print(f"   Response: {result}")
        print("   ✅ Chat completion successful")
        
    except Exception as e:
        print(f"   ❌ Chat completion failed: {e}")
        return 1
    
    # Show statistics
    print("\n3. Client Statistics:")
    stats = client.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ All tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())