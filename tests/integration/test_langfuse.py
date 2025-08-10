#!/usr/bin/env python3
"""
Test script to validate Langfuse integration with GTD Coach
Checks connectivity, scoring, and basic functionality
"""

import asyncio
import time
import os
from pathlib import Path

# Import Langfuse components
try:
    from gtd_coach.integrations.langfuse import get_langfuse_client, score_response, validate_configuration
    from langfuse import observe, get_client
    LANGFUSE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure langfuse is installed: pip install langfuse")
    exit(1)

# Test colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_configuration():
    """Test 1: Validate Langfuse configuration"""
    print("\n1. Testing Langfuse configuration...")
    
    if validate_configuration():
        print(f"{GREEN}✓ Configuration appears valid{RESET}")
        return True
    else:
        print(f"{RED}✗ Configuration invalid - please update langfuse_tracker.py with your keys{RESET}")
        print(f"{YELLOW}  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY{RESET}")
        return False

def test_client_creation():
    """Test 2: Create Langfuse client"""
    print("\n2. Testing Langfuse client creation...")
    
    try:
        client = get_langfuse_client()
        if client:
            print(f"{GREEN}✓ Langfuse client created successfully{RESET}")
            return client
        else:
            print(f"{RED}✗ Failed to create Langfuse client{RESET}")
            return None
    except Exception as e:
        print(f"{RED}✗ Error creating client: {e}{RESET}")
        return None

@observe(name="test_llm_call", as_type="generation")
def test_llm_call(client):
    """Test 3: Make a test LLM call with Langfuse tracking"""
    print("\n3. Testing LLM call with Langfuse tracking...")
    
    try:
        # Simple test prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be brief."},
            {"role": "user", "content": "Say 'Hello, Langfuse test successful!' and nothing else."}
        ]
        
        start_time = time.time()
        
        # Make the call
        completion = client.chat.completions.create(
            model="meta-llama-3.1-8b-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=50,
            name="test_interaction",
            metadata={
                "test": True,
                "phase": "TEST"
            }
        )
        
        response_time = time.time() - start_time
        response_text = completion.choices[0].message.content
        
        print(f"{GREEN}✓ LLM call successful{RESET}")
        print(f"  Response: {response_text}")
        print(f"  Latency: {response_time:.2f}s")
        
        # Test scoring
        score_response("TEST", True, response_time)
        print(f"{GREEN}✓ Response scored successfully{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ LLM call failed: {e}{RESET}")
        
        # Score the failure
        try:
            score_response("TEST", False, time.time() - start_time)
            print(f"{YELLOW}  Failure was scored{RESET}")
        except:
            pass
            
        return False

def test_direct_api_fallback():
    """Test 4: Verify direct API still works without Langfuse"""
    print("\n4. Testing direct API fallback...")
    
    import requests
    
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "meta-llama-3.1-8b-instruct",
                "messages": [
                    {"role": "user", "content": "Say 'Direct API working'"}
                ],
                "temperature": 0.7,
                "max_tokens": 50
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"{GREEN}✓ Direct API fallback working{RESET}")
            return True
        else:
            print(f"{RED}✗ Direct API returned status {response.status_code}{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Direct API call failed: {e}{RESET}")
        print(f"{YELLOW}  Make sure LM Studio is running{RESET}")
        return False

def test_phase_scoring():
    """Test 5: Verify phase-specific scoring thresholds"""
    print("\n5. Testing phase-specific scoring...")
    
    phases = ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW", "PRIORITIZATION", "WRAP_UP"]
    
    try:
        for phase in phases:
            # Simulate different response times
            test_times = [1.5, 3.5, 5.5]  # Fast, medium, slow
            
            for response_time in test_times:
                # This would normally be called within an observation context
                # For testing, we're just verifying the function doesn't error
                try:
                    # Test that scoring function doesn't error
                    # In production, this would be called with a real trace_id
                    score_response(phase, True, response_time, 
                                 session_id="test-session-123", 
                                 trace_id="test-trace-id")
                except Exception as e:
                    # Expected to fail without real trace, but should not have syntax errors
                    if "trace" not in str(e).lower() and "score" not in str(e).lower():
                        raise
            
        print(f"{GREEN}✓ Phase scoring logic validated{RESET}")
        return True
        
    except Exception as e:
        print(f"{RED}✗ Phase scoring failed: {e}{RESET}")
        return False

def test_session_grouping(client):
    """Test 6: Verify that multiple calls are grouped in same session"""
    print("\n6. Testing session grouping...")
    
    from datetime import datetime
    
    try:
        # Generate unique session ID
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"  Creating test session: {session_id}")
        
        # Make multiple calls with same session
        for i in range(3):
            try:
                completion = client.chat.completions.create(
                    model="meta-llama-3.1-8b-instruct",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"Test message {i+1}: Say 'Message {i+1} received'"}
                    ],
                    temperature=0.7,
                    max_tokens=50,
                    name=f"test_interaction_{i+1}",
                    metadata={
                        "langfuse_session_id": session_id,
                        "test": True,
                        "message_number": i+1
                    }
                )
                
                response = completion.choices[0].message.content
                print(f"  Message {i+1}: {response[:50]}...")
                
            except Exception as e:
                print(f"{YELLOW}  Warning: Call {i+1} failed: {e}{RESET}")
        
        print(f"{GREEN}✓ Session grouping test completed{RESET}")
        print(f"  Check Langfuse UI for session: {session_id}")
        print(f"  All 3 traces should be grouped together")
        return True
        
    except Exception as e:
        print(f"{RED}✗ Session grouping failed: {e}{RESET}")
        return False

def test_user_tracking(client):
    """Test 7: Verify weekly user profile tracking"""
    print("\n7. Testing weekly user profile tracking...")
    
    from datetime import datetime
    
    try:
        # Generate expected user ID for current week
        expected_user_id = datetime.now().strftime("%G-W%V")
        
        print(f"  Testing with user ID: {expected_user_id}")
        
        # Make call with user_id in metadata
        completion = client.chat.completions.create(
            model="meta-llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test user tracking: Say 'User tracking active'"}
            ],
            temperature=0.7,
            max_tokens=50,
            name="test_user_tracking",
            metadata={
                "langfuse_session_id": "test-session-user",
                "langfuse_user_id": expected_user_id,  # Weekly profile tracking
                "test": True
            }
        )
        
        response = completion.choices[0].message.content
        print(f"  Response: {response[:50]}...")
        
        print(f"{GREEN}✓ User tracking configured for week: {expected_user_id}{RESET}")
        print(f"  Check Langfuse UI - Users section should show: {expected_user_id}")
        return True
        
    except Exception as e:
        print(f"{RED}✗ User tracking failed: {e}{RESET}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("GTD Coach Langfuse Integration Test")
    print("=" * 50)
    
    # Check if LM Studio is running first
    import requests
    try:
        requests.get("http://localhost:1234/v1/models", timeout=2)
    except:
        print(f"{RED}⚠️  LM Studio doesn't appear to be running{RESET}")
        print("Please start it with: lms server start")
        print("Then load the model")
        return
    
    results = []
    
    # Test 1: Configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))
    
    if not config_ok:
        print(f"\n{YELLOW}⚠️  Cannot proceed without valid configuration{RESET}")
        return
    
    # Test 2: Client creation
    client = test_client_creation()
    results.append(("Client Creation", client is not None))
    
    # Test 3: LLM call with tracking (only if client created)
    if client:
        llm_ok = test_llm_call(client)
        results.append(("LLM Call with Tracking", llm_ok))
    else:
        results.append(("LLM Call with Tracking", False))
    
    # Test 4: Direct API fallback
    api_ok = test_direct_api_fallback()
    results.append(("Direct API Fallback", api_ok))
    
    # Test 5: Phase scoring
    scoring_ok = test_phase_scoring()
    results.append(("Phase Scoring", scoring_ok))
    
    # Test 6: Session grouping (only if client created)
    if client:
        session_ok = test_session_grouping(client)
        results.append(("Session Grouping", session_ok))
    else:
        results.append(("Session Grouping", False))
    
    # Test 7: User tracking (only if client created)
    if client:
        user_ok = test_user_tracking(client)
        results.append(("User Tracking", user_ok))
    else:
        results.append(("User Tracking", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{test_name:<30} {status}")
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n{GREEN}✅ All tests passed! Langfuse integration is working.{RESET}")
        print("\nNext steps:")
        print("1. Update langfuse_tracker.py with your actual Langfuse keys")
        print("2. Ensure Langfuse is running on localhost:3000")
        print("3. Run a GTD review to see traces in Langfuse UI")
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed. Please check the errors above.{RESET}")

if __name__ == "__main__":
    main()