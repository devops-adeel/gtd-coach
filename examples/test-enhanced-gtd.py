#!/usr/bin/env python3
"""
Test script for enhanced GTD review with new error handling and logging
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import from the script directly
import importlib.util
spec = importlib.util.spec_from_file_location("gtd_review", "gtd-review.py")
gtd_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gtd_review)

GTDCoach = gtd_review.GTDCoach
check_server = gtd_review.check_server
validate_mindsweep_items = gtd_review.validate_mindsweep_items
validate_priority = gtd_review.validate_priority

def test_validation_functions():
    """Test the validation functions"""
    print("Testing validation functions...")
    
    # Test mindsweep validation
    test_items = ["  Task 1  ", "", None, "Task 2", "   ", "Task 3"]
    validated = validate_mindsweep_items(test_items)
    print(f"Mindsweep validation: {test_items} -> {validated}")
    assert validated == ["Task 1", "Task 2", "Task 3"]
    
    # Test priority validation
    test_priorities = ["a", "B", " c ", "X", "", None]
    for p in test_priorities:
        result = validate_priority(p)
        print(f"Priority validation: '{p}' -> '{result}'")
    
    print("✓ Validation tests passed\n")

def test_server_check():
    """Test enhanced server checking"""
    print("Testing server check...")
    server_ok, message = check_server()
    print(f"Server status: {server_ok}")
    print(f"Message: {message}")
    
    if not server_ok:
        print("\n⚠️  LM Studio server is not running. Some tests will be skipped.")
        return False
    
    print("✓ Server check passed\n")
    return True

def test_mini_review():
    """Run a minimal review session to test functionality"""
    print("Testing mini review session...")
    
    # Create coach instance
    coach = GTDCoach()
    print(f"Session ID: {coach.session_id}")
    
    # Test phase settings
    print("\nPhase settings:")
    for phase, settings in coach.phase_settings.items():
        print(f"  {phase}: temp={settings['temperature']}, tokens={settings['max_tokens']}")
    
    # Test logging
    coach.logger.info("Test log message")
    
    # Test send_message with retry (if server is running)
    if test_server_check():
        print("\nTesting LLM communication...")
        response = coach.send_message("Say 'Hello, test successful!' in 5 words or less.", phase_name='STARTUP')
        if response:
            print(f"LLM Response: {response}")
            print("✓ LLM communication test passed")
        else:
            print("❌ LLM communication failed")
    
    # Test data saving
    print("\nTesting data persistence...")
    test_items = ["Test item 1", "Test item 2", ""]
    coach.save_mindsweep_items(test_items)
    
    test_priorities = [
        {"action": "Test action 1", "priority": "A"},
        {"action": "Test action 2", "priority": "B"}
    ]
    coach.save_priorities(test_priorities)
    
    coach.save_review_log()
    print("✓ Data persistence test passed")
    
    # Check log file
    log_dir = Path.home() / "gtd-coach" / "logs"
    log_files = list(log_dir.glob(f"session_{coach.session_id}.log"))
    if log_files:
        print(f"\n✓ Log file created: {log_files[0].name}")
        # Show first few lines
        with open(log_files[0], 'r') as f:
            lines = f.readlines()[:5]
            print("First few log entries:")
            for line in lines:
                print(f"  {line.strip()}")
    
    print("\n✓ All tests completed!")

def main():
    """Run all tests"""
    print("="*50)
    print("GTD Coach Enhancement Test Suite")
    print("="*50)
    
    # Run tests
    test_validation_functions()
    
    if test_server_check():
        test_mini_review()
    else:
        print("\nSkipping tests that require LM Studio server.")
        print("To run all tests:")
        print("1. Start LM Studio server: lms server start")
        print("2. Load model: lms load meta-llama-3.1-8b-instruct")

if __name__ == "__main__":
    main()