#!/usr/bin/env python3
"""
Test script for Todoist integration
Run this after installing todoist-api-python
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("GTD Coach - Todoist Integration Test")
print("=" * 60)

# Test 1: Check if API key is configured
api_key = os.getenv('TODOIST_API_KEY')
if api_key:
    print("✅ TODOIST_API_KEY found in environment")
    print(f"   Key starts with: {api_key[:10]}...")
else:
    print("❌ TODOIST_API_KEY not found in .env file")
    sys.exit(1)

# Test 2: Try to import and use Todoist client
try:
    from gtd_coach.integrations.todoist import TodoistClient, get_mock_tasks
    print("✅ Todoist client module imported successfully")
    
    # Test with mock data first
    print("\n📝 Testing with mock data:")
    mock_tasks = get_mock_tasks()
    for task in mock_tasks[:3]:
        print(f"   - {task['content']}")
    
    # Try to initialize real client
    print("\n🔌 Attempting to connect to Todoist API...")
    client = TodoistClient()
    
    if client.is_configured():
        print("✅ Todoist API client initialized")
        
        # Try to fetch inbox tasks
        print("\n📥 Fetching inbox tasks...")
        tasks = client.get_inbox_tasks()
        
        if tasks:
            print(f"✅ Found {len(tasks)} tasks in inbox:")
            for task in tasks[:3]:
                print(f"   - {task['content']}")
        else:
            print("ℹ️  Inbox is empty (or no tasks match filter)")
        
        # Try to fetch today's tasks
        print("\n📅 Fetching today's tasks...")
        today_tasks = client.get_today_tasks()
        print(f"   Found {len(today_tasks)} tasks scheduled for today")
        
    else:
        print("⚠️  Todoist client not configured")
        print("   This usually means todoist-api-python is not installed")
        print("   To install: pip install todoist-api-python")
        print("\n   The integration will work once the package is installed.")
        
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("   The Todoist integration module exists but dependencies are missing")

print("\n" + "=" * 60)
print("Test complete!")
print("\nNext steps:")
print("1. Install todoist-api-python: pip install todoist-api-python")
print("2. Run: python gtd_coach/commands/daily_capture.py")
print("3. The coach will pull from your Todoist inbox and organize your day")
print("=" * 60)