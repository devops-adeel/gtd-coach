#!/usr/bin/env python3
"""
Realistic test for pattern detector with actual recurring items
"""

import json
import tempfile
from pathlib import Path
from gtd_coach.patterns.detector import PatternDetector

def create_realistic_mindsweep_data(temp_dir: Path):
    """Create realistic mindsweep files with clear recurring patterns"""
    
    # Create 4 weeks of data with obvious recurring items
    test_sessions = [
        {
            "timestamp": "20250810_100000",
            "items": [
                "Review monthly budget report",  # Recurring: budget
                "Email Sarah about project update",  # Recurring: email sarah
                "Clean garage this weekend",  # Recurring: clean garage
                "Schedule team meeting",
                "Buy groceries"
            ]
        },
        {
            "timestamp": "20250803_100000", 
            "items": [
                "Review budget for August",  # Recurring: budget
                "Email Sarah regarding timeline",  # Recurring: email sarah
                "Clean garage shelves",  # Recurring: clean garage
                "Doctor appointment",
                "Fix printer"
            ]
        },
        {
            "timestamp": "20250727_100000",
            "items": [
                "Review budget categories",  # Recurring: budget
                "Email Sarah with status",  # Recurring: email sarah
                "Organize meeting notes",
                "Call insurance company",
                "Update resume"
            ]
        },
        {
            "timestamp": "20250720_100000",
            "items": [
                "Review quarterly budget",  # Recurring: budget
                "Clean garage floor",  # Recurring: clean garage
                "Plan vacation",
                "Submit expense report",
                "Read industry article"
            ]
        }
    ]
    
    # Save test files
    for session in test_sessions:
        filename = f"mindsweep_{session['timestamp']}.json"
        filepath = temp_dir / filename
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": session['timestamp'],
                "items": session['items'],
                "count": len(session['items'])
            }, f, indent=2)
    
    return test_sessions

def test_realistic_patterns():
    """Test with realistic recurring patterns"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create realistic test data
        print("Creating realistic mindsweep data...")
        test_sessions = create_realistic_mindsweep_data(temp_path)
        
        # Initialize pattern detector
        detector = PatternDetector(data_dir=temp_path)
        
        # Find patterns
        print("\n" + "="*50)
        print("REALISTIC PATTERN DETECTION TEST")
        print("="*50)
        
        patterns = detector.find_recurring_patterns(weeks_back=4)
        
        if patterns:
            print(f"\n✅ Found {len(patterns)} recurring patterns:")
            for i, pattern in enumerate(patterns, 1):
                print(f"\n{i}. Pattern: '{pattern['pattern']}'")
                print(f"   Frequency: {pattern['count']} times")
                print(f"   Weeks seen: {pattern['weeks_seen']}")
                print(f"   Example: '{pattern['example'][:50]}...'")
            
            # Save context for "next session"
            context = {
                'patterns': patterns,
                'last_session': '20250810_100000',
                'timestamp': '2025-08-10T10:00:00'
            }
            detector.save_context(context)
            
            # Simulate startup display
            print("\n" + "="*50)
            print("SIMULATED STARTUP DISPLAY")
            print("="*50)
            
            loaded = detector.load_context()
            if loaded and loaded.get('patterns'):
                print("\n💭 On your mind lately:")
                for p in loaded['patterns'][:3]:
                    print(f"   • {p['pattern']} (seen {p['weeks_seen']} weeks)")
                print("\n✨ These recurring items have been automatically identified")
                print("   from your previous weekly reviews.")
            
        else:
            print("\n⚠️ No patterns found - check pattern detection logic")
        
        # Test insights
        print("\n" + "="*50)
        print("SESSION INSIGHTS")
        print("="*50)
        
        current_items = [
            "Review budget report again",
            "Email Sarah about deadline",
            "Clean garage this weekend"
        ]
        
        insights = detector.get_simple_insights(current_items)
        print(f"\nCurrent session insights:")
        print(f"  Items: {insights['item_count']}")
        if insights.get('themes'):
            print(f"  Themes: {', '.join(insights['themes'])}")

if __name__ == "__main__":
    test_realistic_patterns()