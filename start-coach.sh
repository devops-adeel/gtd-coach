#!/bin/bash
# Start GTD Coach - Launches LM Studio server and loads model

echo "🚀 Starting GTD Coach Setup..."
echo "=============================="

# Check if server is already running
if lms server status 2>/dev/null | grep -q "running"; then
    echo "✓ LM Studio server is already running"
else
    echo "Starting LM Studio server..."
    lms server start
    sleep 3  # Give server time to start
fi

# Check if model is already loaded
echo -e "\nChecking loaded models..."
LOADED_MODELS=$(lms ps --json 2>/dev/null || echo "[]")

if echo "$LOADED_MODELS" | grep -q "llama-3.1-8b"; then
    echo "✓ Llama 3.1 8B model is already loaded"
else
    echo "Loading Llama 3.1 8B model..."
    # Try to load the model - adjust the exact name based on what was downloaded
    lms load "meta-llama-3.1-8b-instruct" \
        --gpu max \
        --context-length 32768 \
        --identifier "gtd-coach" \
        --ttl 7200  # Auto-unload after 2 hours idle
    
    if [ $? -eq 0 ]; then
        echo "✓ Model loaded successfully"
    else
        echo "❌ Failed to load model. Please check the model name with: lms ls"
        echo "Then manually load with: lms load <model-name>"
        exit 1
    fi
fi

# Check Langfuse connectivity (optional)
echo -e "\nChecking Langfuse observability..."
if [ -n "$LANGFUSE_HOST" ]; then
    # Use environment variable if set
    LANGFUSE_URL="$LANGFUSE_HOST"
else
    # Default to local instance
    LANGFUSE_URL="http://localhost:3000"
fi

# Try to reach Langfuse health endpoint
if curl -s --connect-timeout 2 "$LANGFUSE_URL/api/public/health" > /dev/null 2>&1; then
    echo "✓ Langfuse is accessible at $LANGFUSE_URL"
    echo "  Performance tracking will be enabled"
else
    echo "⚠️  Langfuse not accessible at $LANGFUSE_URL"
    echo "  Continuing without performance tracking"
    echo "  To enable: ensure Langfuse is running and update langfuse_tracker.py with your keys"
fi

echo -e "\n✅ GTD Coach is ready!"
echo "===================="
echo ""
echo "To start your weekly review, run:"
echo "  python3 ~/gtd-coach/gtd-review.py"
echo ""
echo "Or for a quick timer test:"
echo "  ~/gtd-coach/scripts/timer.sh 1 'Test complete!'"
echo ""
echo "Server running at: http://localhost:1234"
echo "Models loaded:"
lms ps

# Optional: Launch the review immediately
echo ""
echo -n "Start weekly review now? (y/n) "
read -n 1 REPLY
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ~/gtd-coach
    python3 gtd-review.py
fi