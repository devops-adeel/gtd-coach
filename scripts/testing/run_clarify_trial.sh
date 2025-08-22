#!/bin/bash
# Run clarify with automated responses for testing
# This simulates: keep first task, delete second task, then quit

echo "🚀 Starting GTD Coach Clarify (Agent Version)"
echo "============================================"
echo ""
echo "This will process your Todoist inbox with automated test responses."
echo "Responses: Keep first task, Delete second, then quit"
echo ""

# Load environment
source ~/.env

# Create response file
cat > /tmp/clarify_responses.txt << EOF
k
d
q
EOF

echo "Running clarify with test responses..."
python3 -m gtd_coach clarify < /tmp/clarify_responses.txt

echo ""
echo "✅ Test complete! Check TRIAL_LOG.md for results"