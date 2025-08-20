#!/bin/bash
# CI/CD test script that works without TTY
# Uses environment variables for mock responses

echo "=============================================="
echo "CI/CD TEST - GTD Coach without TTY"
echo "=============================================="
echo ""
echo "This test runs in non-interactive mode"
echo "Suitable for CI/CD pipelines"
echo ""

# Set environment variables for enhanced logging
export LOG_LEVEL=DEBUG
export LANGFUSE_DEBUG=true

# For CI/CD, we can either:
# 1. Use piped input (interrupts will bypass)
# 2. Run twice - once to interrupt, once to resume
# 3. Use environment variables for mock responses

echo "Option 1: Testing with piped input (interrupts will bypass)"
echo "-------------------------------------------------------------"

# Create automated input
cat > /tmp/ci_test_input.txt << EOF
Let's start the GTD weekly review.
8
No concerns, ready to proceed.
yes
Finish the CI/CD pipeline
Update documentation
done
EOF

# Run with piped input
echo "Running GTD Coach with automated input..."
docker compose run --rm gtd-coach python -m gtd_coach < /tmp/ci_test_input.txt

echo ""
echo "Option 2: Testing with double invocation pattern"
echo "-------------------------------------------------"
echo "This approach is recommended for testing interrupt behavior in CI/CD"
echo ""

# First invocation - will hit interrupt
echo "First invocation (will pause at interrupt)..."
docker compose run --rm \
  -e THREAD_ID="ci_test_$(date +%s)" \
  gtd-coach python -c "
import sys
from gtd_coach import run_weekly_review

# First run - will hit interrupt
result = run_weekly_review(thread_id='ci_test')
print('First invocation complete')
print(f'Result: {result}')
"

# Second invocation - resume with None input
echo "Second invocation (resuming from checkpoint)..."
docker compose run --rm \
  -e THREAD_ID="ci_test_$(date +%s)" \
  gtd-coach python -c "
import sys
from gtd_coach import run_weekly_review

# Resume with None input
result = run_weekly_review(resume=True, thread_id='ci_test')
print('Second invocation complete')
print(f'Result: {result}')
"

echo ""
echo "=============================================="
echo "CI/CD Test Complete"
echo "=============================================="
echo ""
echo "Check logs for:"
echo "  - Interrupt detection patterns"
echo "  - Checkpointer usage"
echo "  - Tool execution flow"
echo ""

# Clean up
rm -f /tmp/ci_test_input.txt