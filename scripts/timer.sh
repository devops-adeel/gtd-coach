#!/bin/bash
# Simple timer for ADHD GTD coaching sessions
# Usage: ./timer.sh <minutes> [message]

# Check if duration is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <minutes> [message]"
    exit 1
fi

DURATION=$1
MESSAGE=${2:-"Time's up!"}

# Convert minutes to seconds (handle decimals)
SECONDS=$(echo "$DURATION * 60" | bc | cut -d. -f1)

echo "⏱️  Timer started for $DURATION minutes"
echo "Starting at: $(date '+%H:%M:%S')"

# Show progress every 20% of the time
INTERVAL=$((SECONDS / 5))
ELAPSED=0

while [ $ELAPSED -lt $SECONDS ]; do
    REMAINING=$((SECONDS - ELAPSED))
    REMAINING_MIN=$((REMAINING / 60))
    REMAINING_SEC=$((REMAINING % 60))
    
    # Calculate percentage
    PERCENT=$((ELAPSED * 100 / SECONDS))
    
    # Show warnings at key intervals
    if [ $PERCENT -eq 50 ] && [ $((ELAPSED % INTERVAL)) -eq 0 ]; then
        echo "⚠️  50% time remaining: ${REMAINING_MIN}m ${REMAINING_SEC}s"
        # Play sound for macOS
        afplay /System/Library/Sounds/Tink.aiff 2>/dev/null || true
    elif [ $PERCENT -eq 80 ] && [ $((ELAPSED % INTERVAL)) -eq 0 ]; then
        echo "⚠️  20% time remaining: ${REMAINING_MIN}m ${REMAINING_SEC}s"
        afplay /System/Library/Sounds/Tink.aiff 2>/dev/null || true
    elif [ $PERCENT -eq 90 ] && [ $((ELAPSED % INTERVAL)) -eq 0 ]; then
        echo "🚨 10% time remaining: ${REMAINING_MIN}m ${REMAINING_SEC}s"
        afplay /System/Library/Sounds/Purr.aiff 2>/dev/null || true
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Time's up!
echo "🔔 $MESSAGE"
echo "Ended at: $(date '+%H:%M:%S')"

# Play completion sound
afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true

# If running from another script, return 0
exit 0