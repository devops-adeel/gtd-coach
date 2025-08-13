#!/usr/bin/env python3
"""
Command to test agent integration
Part of the commands subsystem for todoist integration
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import and run the test
from test_coach_integration import main

if __name__ == "__main__":
    main()