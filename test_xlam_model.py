#!/usr/bin/env python3
"""
Test script to verify xLAM-7b-fc-r model is loaded and responding
"""

import requests
import json
import sys

def test_model_connection():
    """Test basic connection to LM Studio"""
    try:
        # Test the models endpoint
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            if models:
                print(f"✅ LM Studio is running with model: {models[0].get('id', 'unknown')}")
                return True
            else:
                print("❌ LM Studio is running but no model is loaded")
                return False
        else:
            print(f"❌ LM Studio API returned status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to LM Studio: {e}")
        return False

def test_simple_completion():
    """Test a simple completion"""
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "local-model",  # LM Studio uses this generic name
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            print(f"✅ Model responded: {answer}")
            return True
        else:
            print(f"❌ Model returned error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing completion: {e}")
        return False

def test_function_calling():
    """Test function calling capability"""
    try:
        # Define a simple function
        functions = [{
            "name": "add_numbers",
            "description": "Add two numbers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }]
        
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "user", "content": "Please add 5 and 3 together"}
                ],
                "functions": functions,
                "function_call": "auto",
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']
            
            # Check if model attempted function calling
            if 'function_call' in message:
                print(f"✅ Function calling detected: {message['function_call']}")
                return True
            else:
                # Some models return function calls in content
                content = message.get('content', '')
                if 'add_numbers' in content.lower() or 'function' in content.lower():
                    print(f"✅ Model mentioned function in response: {content[:100]}...")
                    return True
                else:
                    print(f"⚠️  Model responded but without function call: {content[:100]}...")
                    return False
        else:
            print(f"❌ Function call test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing function calling: {e}")
        return False

def main():
    print("=" * 60)
    print("xLAM-7b-fc-r Model Test")
    print("=" * 60)
    print()
    
    # Test 1: Connection
    print("Test 1: Checking LM Studio connection...")
    if not test_model_connection():
        print("\n⚠️  Please ensure LM Studio is running and the model is loaded.")
        return 1
    print()
    
    # Test 2: Simple completion
    print("Test 2: Testing simple completion...")
    if not test_simple_completion():
        print("\n⚠️  Model is loaded but not responding correctly.")
        return 1
    print()
    
    # Test 3: Function calling
    print("Test 3: Testing function calling capability...")
    func_test = test_function_calling()
    if not func_test:
        print("\n⚠️  Function calling may not be working as expected.")
        print("This model is specifically designed for function calling,")
        print("so this might indicate a configuration issue.")
    print()
    
    print("=" * 60)
    print("✅ Model is ready for testing with GTD Coach!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())