#!/bin/bash
# Test interrupt pattern in Docker environment with automated input

echo "=============================================="
echo "Testing GTD Coach with Interrupt Pattern"
echo "=============================================="
echo ""
echo "This test will provide automated responses to test the interrupt flow:"
echo "1. Start the weekly review"
echo "2. Respond to energy level question (8)"
echo "3. Respond to concerns question (No concerns)"
echo "4. Confirm readiness (yes)"
echo ""
echo "=============================================="
echo ""

# Create a temporary Python script that will provide input
cat > /tmp/test_interrupt_input.py << 'EOF'
#!/usr/bin/env python3
import sys
import time

# Add slight delays to simulate user typing
responses = [
    ("Let's start the GTD weekly review.", 1),
    ("8", 2),  # Energy level
    ("No concerns, ready to go!", 2),  # Concerns
    ("yes", 2),  # Ready for mind sweep
    ("I need to finish the quarterly report", 2),  # Mind sweep item
    ("Review the budget proposal", 2),  # Another item
    ("done", 1),  # Done with mind sweep
]

for response, delay in responses:
    time.sleep(delay)
    print(response)
    sys.stdout.flush()

# Keep script running to see output
time.sleep(5)
EOF

chmod +x /tmp/test_interrupt_input.py

echo "Running GTD Coach with automated input..."
echo ""

# Run the coach with piped input
/tmp/test_interrupt_input.py | docker compose run --rm gtd-coach python -m gtd_coach

echo ""
echo "=============================================="
echo "Test Complete"
echo "=============================================="
echo ""
echo "Expected behavior:"
echo "✅ Agent should have transitioned to STARTUP"
echo "✅ Agent should have asked about energy level"
echo "✅ Agent should have waited for and processed each input"
echo "✅ Conversation should have continued naturally"
echo ""
echo "Check logs for:"
echo "- 'Agent interrupted' messages"
echo "- 'Resuming agent with user input' messages"
echo "- Multiple stream chunks"
echo ""

# Clean up
rm -f /tmp/test_interrupt_input.py