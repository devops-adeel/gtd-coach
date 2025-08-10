#!/usr/bin/env python3
"""
End-to-end test script for GTD Coach
Simulates a complete review session with automated inputs
"""

import subprocess
import time
import os
import json
from datetime import datetime
from pathlib import Path

# Test data
TEST_INPUTS = {
    "startup": "\n",  # Just press enter to acknowledge
    "mindsweep": [
        "Update project documentation",
        "Review team performance metrics", 
        "Fix bug in authentication module",
        "Schedule dentist appointment",
        "Plan vacation for next month",
        "Review and update budget",
        "Call mom about birthday plans",
        "",  # Empty line
        "y"  # Yes to finish early
    ],
    "projects": [
        "Research new framework options",
        "Create technical spec document",
        "Review pull requests from team"
    ],
    "priorities": [
        ("Fix authentication bug", "A"),
        ("Update documentation", "B"),
        ("Review team metrics", "B"),
        ("", "")  # Empty to finish
    ]
}

def run_test_review():
    """Run a simulated GTD review with test inputs"""
    print("🧪 Starting automated GTD review test...")
    print("=" * 50)
    
    # Create input string
    inputs = []
    
    # Startup phase
    inputs.append(TEST_INPUTS["startup"])
    
    # Mind sweep phase
    inputs.extend(TEST_INPUTS["mindsweep"])
    
    # Project review phase (simplified - just 3 projects)
    inputs.extend(TEST_INPUTS["projects"])
    
    # Prioritization phase
    for action, priority in TEST_INPUTS["priorities"]:
        if action:
            inputs.append(action)
            inputs.append(priority)
        else:
            inputs.append("")  # Empty to finish
    
    # Join all inputs
    full_input = "\n".join(inputs) + "\n"
    
    # Run the review with piped input
    print("\n📋 Running GTD review with test data...")
    print("-" * 50)
    
    # Use docker-compose directly for better control
    cmd = [
        "docker", "compose", "run", "--rm", 
        "-e", "PYTHONUNBUFFERED=1",
        "gtd-coach"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Send all inputs at once
    stdout, _ = process.communicate(input=full_input)
    
    # Print the output
    print(stdout)
    
    return process.returncode == 0

def check_data_files():
    """Check that data files were created"""
    print("\n📁 Checking data persistence...")
    print("-" * 50)
    
    data_dir = Path.home() / "gtd-coach" / "data"
    logs_dir = Path.home() / "gtd-coach" / "logs"
    
    # Find most recent files
    now = datetime.now()
    today = now.strftime("%Y%m%d")
    
    found_files = {
        "mindsweep": False,
        "priorities": False,
        "review_log": False,
        "graphiti_batch": False
    }
    
    # Check mindsweep files
    for f in data_dir.glob(f"mindsweep_{today}*.json"):
        if (now - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 300:  # Within 5 minutes
            print(f"✅ Found recent mindsweep: {f.name}")
            found_files["mindsweep"] = True
            # Print content
            with open(f, 'r') as file:
                data = json.load(file)
                print(f"   Items captured: {len(data.get('items', []))}")
    
    # Check priorities files
    for f in data_dir.glob(f"priorities_{today}*.json"):
        if (now - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 300:
            print(f"✅ Found recent priorities: {f.name}")
            found_files["priorities"] = True
            # Print content
            with open(f, 'r') as file:
                data = json.load(file)
                print(f"   Priorities set: {len(data.get('priorities', []))}")
    
    # Check review logs
    for f in logs_dir.glob(f"review_{today}*.json"):
        if (now - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 300:
            print(f"✅ Found recent review log: {f.name}")
            found_files["review_log"] = True
    
    # Check Graphiti batch files
    for f in data_dir.glob(f"graphiti_batch_{today}*.json"):
        if (now - datetime.fromtimestamp(f.stat().st_mtime)).seconds < 300:
            print(f"✅ Found recent Graphiti batch: {f.name}")
            found_files["graphiti_batch"] = True
            # Print episode count
            with open(f, 'r') as file:
                data = json.load(file)
                print(f"   Episodes captured: {len(data.get('episodes', []))}")
    
    return all(found_files.values())

def test_summary_generation():
    """Test weekly summary generation"""
    print("\n📊 Testing summary generation...")
    print("-" * 50)
    
    cmd = ["./docker-run.sh", "summary"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Summary generation completed")
        
        # Check if summary file was created
        summaries_dir = Path.home() / "gtd-coach" / "summaries"
        today = datetime.now().strftime("%Y%m%d")
        
        for f in summaries_dir.glob(f"weekly_summary_{today}*.md"):
            print(f"✅ Found summary file: {f.name}")
            # Print first few lines
            with open(f, 'r') as file:
                lines = file.readlines()[:10]
                print("\n📄 Summary preview:")
                print("".join(lines))
            return True
    else:
        print("❌ Summary generation failed")
        print(f"Error: {result.stderr}")
    
    return False

def main():
    """Run all end-to-end tests"""
    print("🚀 GTD Coach End-to-End Test Suite")
    print("=" * 50)
    
    results = {
        "review": False,
        "data_persistence": False,
        "summary": False
    }
    
    # Test 1: Run automated review
    try:
        results["review"] = run_test_review()
    except Exception as e:
        print(f"❌ Review test failed: {e}")
    
    # Give system time to flush files
    time.sleep(2)
    
    # Test 2: Check data persistence
    try:
        results["data_persistence"] = check_data_files()
    except Exception as e:
        print(f"❌ Data persistence test failed: {e}")
    
    # Test 3: Generate summary
    try:
        results["summary"] = test_summary_generation()
    except Exception as e:
        print(f"❌ Summary test failed: {e}")
    
    # Final report
    print("\n" + "=" * 50)
    print("📊 END-TO-END TEST RESULTS")
    print("=" * 50)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test.replace('_', ' ').title():<30} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print("-" * 50)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All end-to-end tests passed!")
        print("\n💡 Next: Check Langfuse UI at http://localhost:3000 for traces")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())