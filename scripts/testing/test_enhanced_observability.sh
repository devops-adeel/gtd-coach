#!/bin/bash
# Test script for enhanced observability and interrupt handling
# This verifies that the LangGraph interrupt pattern works with comprehensive tracing

echo "=============================================="
echo "Testing GTD Coach with Enhanced Observability"
echo "=============================================="
echo ""
echo "This test will verify:"
echo "1. Interrupt detection using __interrupt__ key"
echo "2. Enhanced Langfuse tracing"
echo "3. Interrupt monitoring and debugging"
echo "4. Conversation tool instrumentation"
echo ""
echo "=============================================="
echo ""

# Set environment variables for enhanced logging
export LOG_LEVEL=DEBUG
export LANGFUSE_DEBUG=true

echo "Running GTD Coach with full observability..."
echo ""

# Create a test input script
cat > /tmp/test_observability_input.py << 'EOF'
#!/usr/bin/env python3
import sys
import time

# Test responses for interrupt handling
responses = [
    ("Let's start the GTD weekly review.", 1),
    ("8", 2),  # Energy level when asked
    ("No major concerns, ready to go!", 2),  # Concerns
    ("yes", 2),  # Ready for mind sweep
    ("Finish the observability implementation", 2),  # Mind sweep item
    ("Test the interrupt pattern thoroughly", 2),  # Another item
    ("done", 1),  # Done with mind sweep
]

for response, delay in responses:
    time.sleep(delay)
    print(response)
    sys.stdout.flush()

# Keep running to see final output
time.sleep(5)
EOF

chmod +x /tmp/test_observability_input.py

echo "Starting test with automated input..."
echo ""

# Run with piped input to test the interrupt pattern
/tmp/test_observability_input.py | docker compose run --rm gtd-coach python -m gtd_coach 2>&1 | tee /tmp/observability_test.log

echo ""
echo "=============================================="
echo "Test Complete - Analyzing Results"
echo "=============================================="
echo ""

# Check for key indicators in the log
echo "Checking for interrupt detection..."
if grep -q "Interrupt detected in result" /tmp/observability_test.log; then
    echo "✅ Interrupts detected successfully"
else
    echo "❌ No interrupts detected"
fi

echo ""
echo "Checking for interrupt attempts..."
if grep -q "INTERRUPT CALLED" /tmp/observability_test.log || grep -q "interrupt.attempt" /tmp/observability_test.log; then
    echo "✅ Interrupt attempts tracked"
else
    echo "⚠️ No interrupt attempts found"
fi

echo ""
echo "Checking for enhanced tracing..."
if grep -q "Enhanced observability enabled" /tmp/observability_test.log; then
    echo "✅ Enhanced observability active"
else
    echo "⚠️ Enhanced observability not enabled"
fi

echo ""
echo "Checking for conversation tool calls..."
if grep -q "check_in_with_user_v2" /tmp/observability_test.log; then
    echo "✅ Conversation tools called"
else
    echo "❌ Conversation tools not called"
fi

echo ""
echo "Checking for interrupt bypass warnings..."
if grep -q "INTERRUPT BYPASSED" /tmp/observability_test.log; then
    echo "⚠️ Interrupts were bypassed (expected with piped input)"
else
    echo "✅ No interrupt bypass detected"
fi

echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="
echo ""
echo "Log file saved to: /tmp/observability_test.log"
echo ""
echo "Key findings:"
grep -E "(Interrupt detected|interrupt.attempt|INTERRUPT|Enhanced observability|Session metrics)" /tmp/observability_test.log | head -20

echo ""
echo "To run interactively (for proper interrupt behavior):"
echo "  ./scripts/test_interactive.sh"
echo ""

# Clean up
rm -f /tmp/test_observability_input.py