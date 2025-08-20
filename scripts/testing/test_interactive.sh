#!/bin/bash
# Interactive test of the interrupt pattern

echo "=============================================="
echo "INTERACTIVE TEST - GTD Coach with Interrupts"
echo "=============================================="
echo ""
echo "This is an INTERACTIVE test. You will need to:"
echo "1. Type: Let's start the GTD weekly review"
echo "2. Answer questions as they appear"
echo "3. Observe the interrupt behavior"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Run interactively with TTY allocation
# -it flags are crucial for proper interrupt handling
docker compose run -it --rm gtd-coach python -m gtd_coach