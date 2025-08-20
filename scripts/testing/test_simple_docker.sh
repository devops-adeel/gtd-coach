#!/bin/bash
# Simple test to verify Docker GTD Coach works

echo "🧪 Testing GTD Coach in Docker..."
echo "================================"

# Create a temporary input file with test data
cat > /tmp/gtd_test_input.txt << 'EOF'


Finish quarterly report
Call dentist for appointment
Review team performance
Update project documentation
Buy birthday gift for mom

y
Research new framework
Create spec document
Review pull requests
Update quarterly report
B
Review team performance  
B

EOF

echo "✅ Test input created"
echo ""
echo "🚀 Running GTD Coach with test data..."
echo "======================================"

# Run the coach with input
docker compose run --rm gtd-coach < /tmp/gtd_test_input.txt

# Check if files were created
echo ""
echo "📁 Checking created files..."
echo "============================"

TODAY=$(date +%Y%m%d)
ls -la ~/gtd-coach/data/mindsweep_${TODAY}*.json 2>/dev/null && echo "✅ Mindsweep file created"
ls -la ~/gtd-coach/data/priorities_${TODAY}*.json 2>/dev/null && echo "✅ Priorities file created"
ls -la ~/gtd-coach/logs/review_${TODAY}*.json 2>/dev/null && echo "✅ Review log created"

# Cleanup
rm -f /tmp/gtd_test_input.txt

echo ""
echo "✅ Test complete!"