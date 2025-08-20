#!/bin/bash
# Test script to verify Langfuse analyzer integration

set -e

echo "=============================================="
echo "Testing Langfuse Analyzer Integration"
echo "=============================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load API keys from ~/.env if it exists
if [ -f ~/.env ]; then
    echo "Loading API keys from ~/.env..."
    export $(cat ~/.env | grep LANGFUSE | xargs)
fi

# Check if API keys are set
if [ -z "$LANGFUSE_PUBLIC_KEY" ] || [ -z "$LANGFUSE_SECRET_KEY" ]; then
    echo -e "${YELLOW}Warning: LANGFUSE API keys not found${NC}"
    echo "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to test with real API"
    echo
fi

# Test 1: Run without analyzer (mocked mode)
echo -e "${GREEN}Test 1: Running tests in MOCKED mode${NC}"
echo "----------------------------------------"
ANALYZE_AGENT_BEHAVIOR=false pytest tests/test_langfuse_analyzer_example.py::test_normal_unit_test -v
echo

# Test 2: Run with analyzer enabled
echo -e "${GREEN}Test 2: Running tests with ANALYZER enabled${NC}"
echo "--------------------------------------------"
if [ -n "$LANGFUSE_PUBLIC_KEY" ]; then
    ANALYZE_AGENT_BEHAVIOR=true pytest tests/test_langfuse_analyzer_example.py::test_example_with_langfuse_analyzer -v
else
    echo -e "${YELLOW}Skipping - API keys not available${NC}"
fi
echo

# Test 3: Test the analysis script directly
echo -e "${GREEN}Test 3: Testing analysis script${NC}"
echo "--------------------------------"
python scripts/analyze_langfuse_traces.py --hours 1 | head -20
echo

# Test 4: Show help for analysis script
echo -e "${GREEN}Test 4: Analysis script help${NC}"
echo "-----------------------------"
python scripts/analyze_langfuse_traces.py --help
echo

echo "=============================================="
echo -e "${GREEN}All tests completed successfully!${NC}"
echo "=============================================="
echo
echo "To test with a failing test and see trace analysis:"
echo "1. Edit tests/test_langfuse_analyzer_example.py"
echo "2. Uncomment the failing assertion in test_failing_example_for_demo"
echo "3. Run: ANALYZE_AGENT_BEHAVIOR=true pytest tests/test_langfuse_analyzer_example.py::test_failing_example_for_demo -v"