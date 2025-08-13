#!/usr/bin/env python3
"""
Test LLM integration with LM Studio
"""

import sys
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

def test_llm_connection():
    """Test actual LLM connectivity and response generation"""
    
    print("Testing LM Studio LLM connection...")
    print("="*50)
    
    try:
        # Create client
        llm = ChatOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="not-needed",
            model="gtd-coach",  # Use the loaded model identifier
            temperature=0.7,
            max_tokens=200
        )
        
        # Test with a simple prompt
        messages = [
            SystemMessage(content="You are a helpful ADHD coach for GTD weekly reviews."),
            HumanMessage(content="What are the 5 phases of a GTD weekly review? List them briefly.")
        ]
        
        print("Sending test prompt to LLM...")
        response = llm.invoke(messages)
        
        print("\n✅ LLM Response:")
        print("-"*50)
        print(response.content)
        print("-"*50)
        
        # Test token counting
        from langchain_core.messages.utils import count_tokens_approximately
        tokens = count_tokens_approximately(messages)
        print(f"\nToken count for prompt: {tokens}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_context_trimming():
    """Test context trimming with actual LLM"""
    
    print("\n\nTesting context trimming...")
    print("="*50)
    
    try:
        from langchain_core.messages.utils import trim_messages, count_tokens_approximately
        
        # Create a long conversation
        messages = [
            SystemMessage(content="You are an ADHD coach."),
        ]
        
        # Add many messages to exceed token limit
        for i in range(50):
            messages.append(HumanMessage(content=f"This is test message {i} with some content to fill up the context window."))
            messages.append(SystemMessage(content=f"Response {i}: Acknowledged."))
        
        initial_tokens = count_tokens_approximately(messages)
        print(f"Initial token count: {initial_tokens}")
        
        # Trim to 4000 tokens (GTD Coach limit)
        trimmed = trim_messages(
            messages,
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=4000,
            start_on="human",
            allow_partial=False
        )
        
        final_tokens = count_tokens_approximately(trimmed)
        print(f"After trimming: {final_tokens} tokens")
        print(f"Messages reduced from {len(messages)} to {len(trimmed)}")
        
        if final_tokens <= 4000:
            print("✅ Context trimming successful!")
            return True
        else:
            print("❌ Context still exceeds limit")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_agent_workflow():
    """Test a simple agent workflow"""
    
    print("\n\nTesting agent workflow...")
    print("="*50)
    
    try:
        from gtd_coach.agent.core import GTDAgent
        from gtd_coach.agent.state import StateValidator
        
        # Create agent
        agent = GTDAgent(use_memory_saver=True)
        
        # Create initial state
        state = StateValidator.ensure_required_fields({
            'session_id': 'test_session',
            'current_phase': 'STARTUP'
        })
        
        print(f"Initial state created with {len(state)} fields")
        print(f"Current phase: {state['current_phase']}")
        print(f"Session ID: {state['session_id']}")
        
        # Test phase guidance
        guidance = agent._get_phase_guidance(state)
        print(f"\nPhase guidance: {guidance}")
        
        # Test system prompt
        prompt = agent._get_system_prompt(state)
        print(f"\nSystem prompt ({len(prompt)} chars): {prompt[:100]}...")
        
        print("\n✅ Agent workflow components working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("GTD Coach LLM Integration Test")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Run tests
    tests = [
        ("LLM Connection", test_llm_connection),
        ("Context Trimming", test_context_trimming),
        ("Agent Workflow", test_agent_workflow)
    ]
    
    for test_name, test_func in tests:
        if not test_func():
            all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL LLM INTEGRATION TESTS PASSED!")
        print("The system is ready for full GTD weekly reviews.")
    else:
        print("❌ Some tests failed - review issues above")
    print("="*60)
    
    sys.exit(0 if all_passed else 1)