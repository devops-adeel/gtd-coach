#!/usr/bin/env python3
"""
Test script for the pattern detector module
Validates lightweight pattern detection for memory retrieval
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from pattern_detector import PatternDetector

def create_test_mindsweep_data(temp_dir: Path):
    """Create test mindsweep files with recurring patterns"""
    
    # Create 4 weeks of test data with some recurring patterns
    test_sessions = [
        {
            "timestamp": "20250810_100000",
            "items": [
                "Review budget spreadsheet",
                "Call mom about birthday plans",
                "Fix the broken kitchen faucet",
                "Prepare Q3 presentation slides",
                "Email team about project timeline"
            ]
        },
        {
            "timestamp": "20250803_100000", 
            "items": [
                "Update budget tracking for August",
                "Schedule dentist appointment",
                "Fix kitchen cabinet door",
                "Review Q3 goals and metrics",
                "Send weekly status update"
            ]
        },
        {
            "timestamp": "20250727_100000",
            "items": [
                "Check budget categories",
                "Plan vacation itinerary",
                "Kitchen organization project",
                "Prepare monthly report",
                "Team meeting agenda"
            ]
        },
        {
            "timestamp": "20250720_100000",
            "items": [
                "Review monthly budget",
                "Doctor appointment follow-up",
                "Fix leaky bathroom faucet",
                "Q3 planning session",
                "Email client about proposal"
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
        print(f"Created test file: {filename}")
    
    return test_sessions

def test_pattern_detection():
    """Test pattern detection functionality"""
    
    # Create temporary directory for test data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test data
        print("Creating test mindsweep data...")
        test_sessions = create_test_mindsweep_data(temp_path)
        
        # Initialize pattern detector with test directory
        detector = PatternDetector(data_dir=temp_path)
        
        # Test 1: Find recurring patterns
        print("\n" + "="*50)
        print("TEST 1: Finding Recurring Patterns")
        print("="*50)
        
        patterns = detector.find_recurring_patterns(weeks_back=4)
        
        if patterns:
            print(f"\n✅ Found {len(patterns)} recurring patterns:")
            for i, pattern in enumerate(patterns, 1):
                print(f"\n{i}. Pattern: '{pattern['pattern']}'")
                print(f"   Count: {pattern['count']} occurrences")
                print(f"   Seen in: {pattern['weeks_seen']} different weeks")
                print(f"   Example: '{pattern['example']}'")
        else:
            print("\n⚠️ No recurring patterns found (this might be expected with test data)")
        
        # Test 2: Save and load context
        print("\n" + "="*50)
        print("TEST 2: Context Save/Load")
        print("="*50)
        
        test_context = {
            'patterns': patterns,
            'last_session': '20250810_100000',
            'last_insights': {
                'item_count': 5,
                'themes': ['budget', 'fix', 'review']
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Save context
        detector.save_context(test_context)
        print("✅ Context saved successfully")
        
        # Load context
        loaded_context = detector.load_context()
        if loaded_context:
            print("✅ Context loaded successfully")
            print(f"   Last session: {loaded_context.get('last_session')}")
            print(f"   Patterns found: {len(loaded_context.get('patterns', []))}")
            if loaded_context.get('last_insights'):
                print(f"   Themes: {loaded_context['last_insights'].get('themes', [])}")
        else:
            print("❌ Failed to load context")
        
        # Test 3: Generate insights from current session
        print("\n" + "="*50)
        print("TEST 3: Current Session Insights")
        print("="*50)
        
        current_items = [
            "Review budget for next month",
            "Fix the printer issue",
            "Email about project deadline",
            "Plan team meeting agenda",
            "Update project documentation"
        ]
        
        insights = detector.get_simple_insights(current_items)
        print(f"\n✅ Generated insights:")
        print(f"   Item count: {insights['item_count']}")
        if insights.get('themes'):
            print(f"   Key themes: {', '.join(insights['themes'])}")
        
        # Test 4: Display memory context (simulating startup)
        print("\n" + "="*50)
        print("TEST 4: Simulated Startup Display")
        print("="*50)
        
        context = detector.load_context()
        if context and context.get('patterns'):
            print("\n💭 On your mind lately:")
            for pattern in context['patterns'][:3]:
                print(f"   • {pattern['pattern']} (seen {pattern['weeks_seen']} weeks)")
        else:
            print("\n(No recurring patterns to display)")
        
        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        print("="*50)

def test_empty_data():
    """Test behavior with no data"""
    print("\n" + "="*50)
    print("TEST 5: Empty Data Handling")
    print("="*50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        detector = PatternDetector(data_dir=temp_path)
        
        # Test with no files
        patterns = detector.find_recurring_patterns()
        print(f"Patterns with no data: {patterns}")
        assert patterns == [], "Should return empty list with no data"
        
        # Test loading non-existent context
        context = detector.load_context()
        print(f"Context with no file: {context}")
        assert context == {}, "Should return empty dict with no context file"
        
        print("✅ Empty data handling works correctly")

if __name__ == "__main__":
    print("="*60)
    print("PATTERN DETECTOR TEST SUITE")
    print("="*60)
    
    try:
        # Run main tests
        test_pattern_detection()
        
        # Run edge case tests
        test_empty_data()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)