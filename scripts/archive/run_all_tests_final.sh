#!/bin/bash

# Final test runner script for GTD Coach
# Runs all available tests with proper error handling

echo "============================================================"
echo "🚀 RUNNING ALL GTD COACH TESTS"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track totals
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# Function to run tests for a category
run_test_category() {
    local category=$1
    local path=$2
    local markers=$3
    
    echo -e "\n${YELLOW}### $category ###${NC}"
    
    if [ ! -d "$path" ]; then
        echo "  ⚠️ Path $path not found, skipping"
        return
    fi
    
    # Run tests and capture output
    output=$(python3 -m pytest "$path" \
        -v \
        --tb=short \
        --no-header \
        -q \
        -m "$markers" \
        2>&1)
    
    # Extract statistics from output
    if echo "$output" | grep -q "passed"; then
        passed=$(echo "$output" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1)
        failed=$(echo "$output" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" | head -1)
        skipped=$(echo "$output" | grep -oE "[0-9]+ skipped" | grep -oE "[0-9]+" | head -1)
        warnings=$(echo "$output" | grep -oE "[0-9]+ warning" | grep -oE "[0-9]+" | head -1)
        
        # Default to 0 if not found
        passed=${passed:-0}
        failed=${failed:-0}
        skipped=${skipped:-0}
        warnings=${warnings:-0}
        
        # Update totals
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
        
        # Display results
        echo -e "  ${GREEN}Passed:${NC} $passed"
        if [ "$failed" -gt 0 ]; then
            echo -e "  ${RED}Failed:${NC} $failed"
        else
            echo -e "  Failed: $failed"
        fi
        echo -e "  Skipped: $skipped"
        
        # Show failed test names if any
        if [ "$failed" -gt 0 ]; then
            echo -e "  ${RED}Failed tests:${NC}"
            echo "$output" | grep "FAILED" | head -5 | while read line; do
                echo "    - $line"
            done
        fi
    else
        echo "  ❌ No tests found or error occurred"
        echo "$output" | head -5
    fi
}

# Install minimal test dependencies if needed
echo -e "${YELLOW}Checking test dependencies...${NC}"
python3 -c "import pytest" 2>/dev/null || {
    echo "Installing pytest..."
    python3 -m pip install --break-system-packages --quiet pytest pytest-asyncio pytest-mock
}

# Set environment variables
export TEST_MODE=true
export MOCK_EXTERNAL_APIS=true
export PYTHONDONTWRITEBYTECODE=1

# Run each test category
run_test_category "Unit Tests" "tests/unit" "not requires_neo4j and not requires_api_keys"
run_test_category "Integration Tests" "tests/integration" "not slow and not requires_neo4j and not requires_api_keys"
run_test_category "Agent Tests (Fast)" "tests/agent" "not slow and not requires_neo4j and not requires_api_keys"

# Additional test files in root tests directory
if [ -f "tests/test_structure.py" ]; then
    run_test_category "Structure Tests" "tests/test_structure.py" ""
fi

if [ -f "tests/test_integrations.py" ]; then
    run_test_category "Integration Suite" "tests/test_integrations.py" ""
fi

# Summary
echo ""
echo "============================================================"
echo -e "${YELLOW}📊 TEST EXECUTION SUMMARY${NC}"
echo "============================================================"
echo -e "${GREEN}Passed:${NC} $TOTAL_PASSED"
echo -e "${RED}Failed:${NC} $TOTAL_FAILED"
echo -e "Skipped: $TOTAL_SKIPPED"

if [ $TOTAL_FAILED -eq 0 ] && [ $TOTAL_PASSED -gt 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
    exit 0
else
    if [ $TOTAL_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}❌ $TOTAL_FAILED tests failed${NC}"
        exit 1
    else
        echo ""
        echo -e "${YELLOW}⚠️ No tests were executed${NC}"
        exit 2
    fi
fi