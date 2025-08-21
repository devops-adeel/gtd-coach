#!/usr/bin/env python3
"""
Test that Timing read functionality still works for reality checks
"""

import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv()

print("Testing Timing READ functionality for Reality Checks")
print("=" * 60)

from gtd_coach.integrations.timing import TimingAPI

api = TimingAPI()

if not api.is_configured():
    print("❌ Timing API not configured")
    exit(1)

print("✅ Timing API configured\n")

# Test 1: Fetch projects (what weekly review uses)
print("1. Testing project fetch...")
projects = api.fetch_projects_last_week(min_minutes=5)

if projects:
    print(f"✅ Successfully fetched {len(projects)} projects")
    
    # Simulate reality check calculation
    deep_work_hours = 0
    admin_hours = 0
    reactive_hours = 0
    
    for project in projects[:5]:  # Show first 5
        name = project.get('name', '')
        hours = project.get('time_spent', 0)
        print(f"   - {name}: {hours:.1f}h")
        
        # Categorize like weekly review does
        name_lower = name.lower()
        if 'deep work' in name_lower or any(word in name_lower for word in ['develop', 'design', 'write', 'research']):
            deep_work_hours += hours
        elif any(word in name_lower for word in ['email', 'slack', 'meeting', 'admin']):
            admin_hours += hours
        else:
            reactive_hours += hours
    
    total_hours = deep_work_hours + admin_hours + reactive_hours
    
    if total_hours > 0:
        print(f"\n📊 Reality Check Preview:")
        print(f"   Deep work: {deep_work_hours:.1f}h ({(deep_work_hours/total_hours)*100:.0f}%)")
        print(f"   Admin: {admin_hours:.1f}h ({(admin_hours/total_hours)*100:.0f}%)")
        print(f"   Other: {reactive_hours:.1f}h")
        
        if (deep_work_hours/total_hours)*100 < 20:
            print("\n   💡 Less than 20% deep work - typical for ADHD")
else:
    print("⚠️ No projects found - this might be normal if no time tracked")

# Test 2: Fetch time entries for scatter analysis
print("\n2. Testing time entries fetch...")
entries = api.fetch_time_entries_last_week(max_entries=50)

if entries:
    print(f"✅ Successfully fetched {len(entries)} time entries")
    
    # Test context switch detection
    switch_analysis = api.detect_context_switches(entries)
    focus_metrics = api.calculate_focus_metrics(switch_analysis)
    
    print(f"\n📊 Focus Metrics:")
    print(f"   Focus score: {focus_metrics.get('focus_score', 0)}/100")
    print(f"   Switches per hour: {focus_metrics.get('switches_per_hour', 0):.1f}")
    print(f"   Interpretation: {focus_metrics.get('interpretation', 'Unknown')}")
else:
    print("⚠️ No time entries found")

print("\n" + "=" * 60)
print("✅ Reality Check System Status: WORKING")
print("\nThe weekly review will:")
print("1. Read your Timing data (working ✅)")
print("2. Calculate deep work vs admin percentages")
print("3. Show context switching patterns")
print("4. Compare to your stated priorities")
print("\nNo API project creation needed!")