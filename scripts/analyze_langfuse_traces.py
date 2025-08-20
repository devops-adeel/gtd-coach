#!/usr/bin/env python3
"""
Analyze Langfuse traces to understand interrupt behavior in GTD Coach
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/Users/adeel/.env")

# Import Langfuse client
try:
    from langfuse import Langfuse
except ImportError:
    print("Error: langfuse package not installed")
    print("Install with: pip install langfuse")
    sys.exit(1)


def analyze_recent_traces(hours_back: int = 1, session_id: Optional[str] = None):
    """
    Analyze recent Langfuse traces to understand interrupt patterns
    
    Args:
        hours_back: How many hours back to look for traces
        session_id: Optional specific session ID to analyze
    """
    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if not public_key or not secret_key:
        print("Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY not found in environment")
        return
    
    # Initialize client
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    print(f"Fetching traces from Langfuse...")
    print(f"Host: {host}")
    print(f"Looking back {hours_back} hours")
    print("-" * 80)
    
    # Get recent traces
    from_timestamp = datetime.now() - timedelta(hours=hours_back)
    
    # Fetch traces - using the simple client interface
    traces = langfuse.get_traces(
        from_timestamp=from_timestamp,
        limit=10  # Get last 10 traces
    )
    
    if not traces:
        print("No traces found in the specified time range")
        return
    
    print(f"Found {len(traces)} traces")
    print("-" * 80)
    
    # Analyze each trace
    for i, trace in enumerate(traces, 1):
        print(f"\nTrace {i}: {trace.id}")
        print(f"  Name: {trace.name}")
        print(f"  Session ID: {trace.session_id}")
        print(f"  Timestamp: {trace.timestamp}")
        print(f"  User ID: {trace.user_id}")
        
        # Check if this trace matches our session filter
        if session_id and trace.session_id != session_id:
            print(f"  Skipping (not matching session {session_id})")
            continue
        
        # Get observations for this trace
        observations = langfuse.get_observations(
            trace_id=trace.id
        )
        
        print(f"  Observations: {len(observations)}")
        
        # Look for conversation tools and interrupts
        interrupt_found = False
        conversation_tools = []
        
        for obs in observations:
            # Check if this is a tool call
            if obs.name and "check_in_with_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")
                
                # Check input/output for interrupt patterns
                if obs.input:
                    print(f"      Input: {json.dumps(obs.input, indent=2)[:200]}")
                if obs.output:
                    print(f"      Output: {json.dumps(obs.output, indent=2)[:200]}")
                    
                    # Look for interrupt indicators
                    output_str = str(obs.output)
                    if "__interrupt__" in output_str:
                        interrupt_found = True
                        print(f"      🔔 INTERRUPT FOUND in output!")
            
            elif obs.name and "wait_for_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")
            
            elif obs.name and "confirm_with_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")
        
        # Summary for this trace
        print(f"  Summary:")
        print(f"    - Conversation tools called: {len(conversation_tools)}")
        print(f"    - Interrupt detected: {'Yes' if interrupt_found else 'No'}")
        
        # Check for scores (might indicate completion or errors)
        scores = langfuse.get_scores(trace_id=trace.id)
        if scores:
            print(f"    - Scores: {len(scores)}")
            for score in scores:
                print(f"      • {score.name}: {score.value}")
        
        print("-" * 80)
    
    # Flush any pending events
    langfuse.flush()
    print("\nAnalysis complete!")


def get_trace_details(trace_id: str):
    """
    Get detailed information about a specific trace
    
    Args:
        trace_id: The trace ID to analyze
    """
    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    print(f"Fetching trace {trace_id}...")
    
    # Get the trace
    trace = langfuse.get_trace(trace_id)
    
    if not trace:
        print(f"Trace {trace_id} not found")
        return
    
    print(f"Trace: {trace.name}")
    print(f"Session: {trace.session_id}")
    print(f"Timestamp: {trace.timestamp}")
    
    # Get all observations
    observations = langfuse.get_observations(trace_id=trace_id)
    
    print(f"\nObservations ({len(observations)}):")
    for obs in observations:
        print(f"  - {obs.name}")
        print(f"    Type: {obs.type}")
        print(f"    Start: {obs.start_time}")
        print(f"    End: {obs.end_time}")
        
        if obs.input:
            print(f"    Input: {json.dumps(obs.input, indent=4)[:500]}")
        if obs.output:
            print(f"    Output: {json.dumps(obs.output, indent=4)[:500]}")
        
        if obs.metadata:
            print(f"    Metadata: {json.dumps(obs.metadata, indent=4)[:500]}")
        
        print()
    
    langfuse.flush()


def analyze_test_failure(session_id: str, return_data: bool = False):
    """
    Analyze Langfuse traces for a failed test session - AI-optimized output
    
    Args:
        session_id: The test session ID to analyze
        return_data: If True, return data instead of printing (for fixture use)
    
    Returns:
        Dict with analysis data if return_data=True, None otherwise
    """
    # Load real API keys from ~/.env if available
    home_env = os.path.expanduser("~/.env")
    if os.path.exists(home_env):
        load_dotenv(home_env)
    
    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if not public_key or not secret_key:
        msg = "ERROR: Langfuse API keys not found. Check ~/.env or environment variables."
        if return_data:
            return {"error": msg}
        print(msg)
        return
    
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    analysis = {
        "session_id": session_id,
        "traces": [],
        "errors": [],
        "tool_calls": [],
        "interrupts": [],
        "state_transitions": []
    }
    
    # Fetch traces for this session
    traces = langfuse.get_traces(
        session_id=session_id,
        limit=50  # Get up to 50 traces for comprehensive analysis
    )
    
    if not traces:
        msg = f"No traces found for session {session_id}"
        if return_data:
            analysis["error"] = msg
            return analysis
        print(msg)
        return
    
    # Analyze each trace
    for trace in traces:
        trace_data = {
            "id": trace.id,
            "name": trace.name,
            "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
            "observations": []
        }
        
        # Get observations for detailed analysis
        observations = langfuse.get_observations(trace_id=trace.id)
        
        for obs in observations:
            obs_data = {
                "name": obs.name,
                "type": obs.type,
                "start": obs.start_time.isoformat() if obs.start_time else None,
                "end": obs.end_time.isoformat() if obs.end_time else None
            }
            
            # Extract key information for AI analysis
            if obs.input:
                obs_data["input"] = obs.input
                
            if obs.output:
                obs_data["output"] = obs.output
                
                # Detect errors
                output_str = str(obs.output)
                if "error" in output_str.lower() or "exception" in output_str.lower():
                    analysis["errors"].append({
                        "trace": trace.name,
                        "observation": obs.name,
                        "details": obs.output
                    })
                
                # Detect interrupts
                if "__interrupt__" in output_str:
                    analysis["interrupts"].append({
                        "trace": trace.name,
                        "observation": obs.name,
                        "interrupt_data": obs.output
                    })
            
            # Track tool calls
            if obs.name and ("tool" in obs.name.lower() or "check_in" in obs.name or "wait_for" in obs.name):
                analysis["tool_calls"].append({
                    "trace": trace.name,
                    "tool": obs.name,
                    "input": obs.input if obs.input else {},
                    "output": obs.output if obs.output else {}
                })
            
            # Track state transitions
            if obs.metadata and "state" in str(obs.metadata):
                analysis["state_transitions"].append({
                    "trace": trace.name,
                    "observation": obs.name,
                    "metadata": obs.metadata
                })
            
            trace_data["observations"].append(obs_data)
        
        analysis["traces"].append(trace_data)
    
    langfuse.flush()
    
    if return_data:
        return analysis
    
    # Print AI-optimized analysis
    print("\n" + "="*80)
    print(f"TEST FAILURE ANALYSIS FOR SESSION: {session_id}")
    print("="*80)
    
    print(f"\n📊 TRACE SUMMARY:")
    print(f"  Total traces: {len(analysis['traces'])}")
    print(f"  Errors found: {len(analysis['errors'])}")
    print(f"  Tool calls: {len(analysis['tool_calls'])}")
    print(f"  Interrupts: {len(analysis['interrupts'])}")
    print(f"  State transitions: {len(analysis['state_transitions'])}")
    
    if analysis["errors"]:
        print(f"\n❌ ERRORS DETECTED:")
        for error in analysis["errors"]:
            print(f"  - {error['trace']} → {error['observation']}")
            print(f"    {json.dumps(error['details'], indent=4)[:500]}")
    
    if analysis["interrupts"]:
        print(f"\n🔔 INTERRUPT PATTERNS:")
        for interrupt in analysis["interrupts"]:
            print(f"  - {interrupt['trace']} → {interrupt['observation']}")
            print(f"    {json.dumps(interrupt['interrupt_data'], indent=4)[:500]}")
    
    if analysis["tool_calls"]:
        print(f"\n🔧 TOOL CALL SEQUENCE:")
        for tool in analysis["tool_calls"][:10]:  # Show first 10
            print(f"  - {tool['tool']}")
            if tool['input']:
                print(f"    Input: {json.dumps(tool['input'], indent=4)[:200]}")
            if tool['output']:
                print(f"    Output: {json.dumps(tool['output'], indent=4)[:200]}")
    
    # Detailed trace flow for AI debugging
    print(f"\n📝 DETAILED TRACE FLOW:")
    for trace in analysis["traces"][:5]:  # Show first 5 traces in detail
        print(f"\n  Trace: {trace['name']} (ID: {trace['id'][:8]}...)")
        print(f"  Time: {trace['timestamp']}")
        print(f"  Observations:")
        for obs in trace["observations"][:10]:  # Show first 10 observations
            print(f"    • {obs['name']} ({obs['type']})")
            if 'input' in obs and obs['input']:
                print(f"      Input: {json.dumps(obs['input'])[:150]}")
            if 'output' in obs and obs['output']:
                print(f"      Output: {json.dumps(obs['output'])[:150]}")
    
    print("\n" + "="*80)
    print("END OF ANALYSIS")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze Langfuse traces for GTD Coach")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back (default: 1)")
    parser.add_argument("--session", type=str, help="Specific session ID to analyze")
    parser.add_argument("--trace", type=str, help="Specific trace ID to get details")
    parser.add_argument("--test-failure", type=str, help="Analyze a test failure session with AI-optimized output")
    
    args = parser.parse_args()
    
    if args.test_failure:
        analyze_test_failure(args.test_failure)
    elif args.trace:
        get_trace_details(args.trace)
    else:
        analyze_recent_traces(hours_back=args.hours, session_id=args.session)