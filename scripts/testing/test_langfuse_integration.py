#!/usr/bin/env python3
"""
Test script to verify Langfuse integration is working correctly
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add gtd_coach to path
sys.path.insert(0, '/app')

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

def test_langfuse_connection():
    """Test basic Langfuse connection"""
    print("Testing Langfuse connection...")
    try:
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        print("✅ Langfuse client created successfully")
        
        # Test creating a trace
        trace = langfuse.trace(
            name="test-trace",
            session_id="test-session-123",
            user_id="test-user",
            metadata={"test": True}
        )
        print(f"✅ Created test trace with ID: {trace.id}")
        
        # Test callback handler
        handler = CallbackHandler()
        print("✅ CallbackHandler created successfully")
        
        # Flush events
        langfuse.flush()
        print("✅ Events flushed successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_session_tracking():
    """Test session tracking with metadata"""
    print("\nTesting session tracking with metadata...")
    try:
        from langchain_openai import ChatOpenAI
        from langfuse.langchain import CallbackHandler
        
        # Create handler without parameters
        handler = CallbackHandler()
        print("✅ Handler created without parameters")
        
        # Create config with metadata
        config = {
            "callbacks": [handler],
            "metadata": {
                "langfuse_session_id": "test-session-456",
                "user_id": "test-user-2"
            }
        }
        print("✅ Config created with langfuse_session_id in metadata")
        
        # Test with a simple LLM call
        llm = ChatOpenAI(
            base_url=os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1"),
            api_key="not-needed",
            model="test-model",
            temperature=0.7
        )
        
        try:
            # This might fail if LM Studio isn't running, but we're testing the setup
            response = llm.invoke("Say 'test'", config=config)
            print(f"✅ LLM invoked with config: {response.content[:50] if hasattr(response, 'content') else response}")
        except Exception as llm_error:
            print(f"⚠️  LLM call failed (expected if LM Studio not running): {llm_error}")
            print("    But config and handler setup was successful!")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_recent_traces():
    """Check for recent traces with session IDs"""
    print("\nChecking for recent traces...")
    try:
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        
        # Use the api namespace to list traces
        traces_response = langfuse.api.trace.list(limit=5)
        traces = traces_response.data if hasattr(traces_response, 'data') else []
        
        if traces:
            print(f"Found {len(traces)} recent traces:")
            for i, trace in enumerate(traces, 1):
                session_id = getattr(trace, 'session_id', None)
                print(f"  {i}. {trace.name} - Session: {session_id or 'None'}")
        else:
            print("No recent traces found")
        
        # Count traces with session IDs
        with_sessions = sum(1 for t in traces if getattr(t, 'session_id', None))
        print(f"\nTraces with session IDs: {with_sessions}/{len(traces)}")
        
        langfuse.flush()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("LANGFUSE INTEGRATION TEST")
    print("=" * 60)
    
    # Run tests
    results = []
    results.append(("Connection", test_langfuse_connection()))
    results.append(("Session Tracking", test_session_tracking()))
    results.append(("Recent Traces", check_recent_traces()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    # Overall result
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    sys.exit(0 if all_passed else 1)