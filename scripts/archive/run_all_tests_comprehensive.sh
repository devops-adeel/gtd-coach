#!/bin/bash

# Comprehensive Test Runner for GTD Coach
# Runs ALL tests with real APIs and proper reporting

echo "================================================"
echo "🚀 COMPREHENSIVE GTD COACH TEST SUITE"
echo "================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Activate virtual environment if it exists
if [ -d "test_venv" ]; then
    echo -e "${YELLOW}Using virtual environment...${NC}"
    source test_venv/bin/activate
else
    echo -e "${YELLOW}No virtual environment found, using system Python${NC}"
fi

# Set environment for real API testing
export USE_REAL_APIS=true
export MOCK_EXTERNAL_APIS=false
export TEST_MODE=false

# Track totals
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_ERRORS=0

# Function to run tests
run_test_category() {
    local name=$1
    local path=$2
    
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}Testing: $name${NC}"
    echo -e "${BLUE}============================================${NC}"
    
    if [ ! -e "$path" ]; then
        echo -e "${YELLOW}Path $path not found, skipping${NC}"
        return
    fi
    
    # Run pytest with JSON report
    python -m pytest "$path" \
        -v \
        --tb=short \
        --json-report \
        --json-report-file=test_report_temp.json \
        2>&1 | tee test_output_temp.log
    
    # Parse results
    if [ -f "test_report_temp.json" ]; then
        passed=$(python -c "import json; data=json.load(open('test_report_temp.json')); print(data.get('summary', {}).get('passed', 0))")
        failed=$(python -c "import json; data=json.load(open('test_report_temp.json')); print(data.get('summary', {}).get('failed', 0))")
        errors=$(python -c "import json; data=json.load(open('test_report_temp.json')); print(data.get('summary', {}).get('error', 0))")
        
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_ERRORS=$((TOTAL_ERRORS + errors))
        
        echo ""
        echo -e "${GREEN}Passed: $passed${NC}"
        if [ "$failed" -gt 0 ]; then
            echo -e "${RED}Failed: $failed${NC}"
        fi
        if [ "$errors" -gt 0 ]; then
            echo -e "${RED}Errors: $errors${NC}"
        fi
        
        # Show failed tests
        if [ "$failed" -gt 0 ]; then
            echo -e "${RED}Failed tests:${NC}"
            python -c "
import json
data = json.load(open('test_report_temp.json'))
for test in data.get('tests', []):
    if test.get('outcome') == 'failed':
        print(f\"  - {test.get('nodeid', 'Unknown')}\")"
        fi
        
        rm -f test_report_temp.json
    else
        # Fallback parsing from output
        passed=$(grep -c "PASSED" test_output_temp.log 2>/dev/null || echo 0)
        failed=$(grep -c "FAILED" test_output_temp.log 2>/dev/null || echo 0)
        errors=$(grep -c "ERROR" test_output_temp.log 2>/dev/null || echo 0)
        
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_ERRORS=$((TOTAL_ERRORS + errors))
        
        echo -e "${GREEN}Passed: $passed${NC}"
        echo -e "${RED}Failed: $failed${NC}"
        echo -e "${RED}Errors: $errors${NC}"
    fi
    
    rm -f test_output_temp.log
}

# Test all categories
echo -e "${YELLOW}Starting comprehensive test suite...${NC}"

# Unit tests
run_test_category "Unit Tests" "tests/unit"

# Integration tests
run_test_category "Integration Tests" "tests/integration"

# Agent tests
run_test_category "Agent Tests" "tests/agent"

# E2E tests
run_test_category "E2E Tests" "tests/e2e"

# Root level test files
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Testing: Root Level Tests${NC}"
echo -e "${BLUE}============================================${NC}"

for test_file in test_*.py; do
    if [ -f "$test_file" ] && [ "$test_file" != "test_mocks.py" ]; then
        echo -e "${YELLOW}Running $test_file...${NC}"
        python -m pytest "$test_file" -v --tb=short
    fi
done

# Test with real LM Studio if available
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Testing: LM Studio Integration${NC}"
echo -e "${BLUE}============================================${NC}"

if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}LM Studio is running, testing real LLM calls...${NC}"
    
    # Create a simple LLM test
    cat > test_llm_real.py << 'EOF'
import requests
import json

def test_lm_studio():
    """Test real LM Studio API"""
    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "meta-llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "Say 'test passed' in 3 words"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'choices' in data
    print(f"LLM Response: {data['choices'][0]['message']['content']}")
    return True

if __name__ == "__main__":
    try:
        if test_lm_studio():
            print("✅ LM Studio test passed")
    except Exception as e:
        print(f"❌ LM Studio test failed: {e}")
EOF
    
    python test_llm_real.py
    rm -f test_llm_real.py
else
    echo -e "${YELLOW}LM Studio not running, skipping LLM tests${NC}"
fi

# Summary
echo ""
echo "================================================"
echo -e "${BLUE}📊 COMPREHENSIVE TEST SUMMARY${NC}"
echo "================================================"
echo -e "${GREEN}Total Passed: $TOTAL_PASSED${NC}"
echo -e "${RED}Total Failed: $TOTAL_FAILED${NC}"
echo -e "${RED}Total Errors: $TOTAL_ERRORS${NC}"

# Calculate success rate
if [ $((TOTAL_PASSED + TOTAL_FAILED)) -gt 0 ]; then
    SUCCESS_RATE=$((TOTAL_PASSED * 100 / (TOTAL_PASSED + TOTAL_FAILED)))
    echo -e "Success Rate: ${SUCCESS_RATE}%"
fi

# Final result
echo ""
if [ $TOTAL_FAILED -eq 0 ] && [ $TOTAL_ERRORS -eq 0 ] && [ $TOTAL_PASSED -gt 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
    exit 0
else
    echo -e "${RED}⚠️ Some tests failed or had errors${NC}"
    exit 1
fi