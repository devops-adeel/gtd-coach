#!/bin/bash

# Run tests in Docker container
echo "🐳 Running GTD Coach tests in Docker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Build the test Docker image
echo -e "${YELLOW}Building test Docker image...${NC}"
docker build -f docker/Dockerfile.test -t gtd-coach-test:latest . || {
    echo -e "${RED}Failed to build Docker image${NC}"
    exit 1
}

# Create test results directory
mkdir -p test-results

# Run tests in Docker container
echo -e "${YELLOW}Running tests...${NC}"
docker run --rm \
    -v "$(pwd)/test-results:/app/test-results" \
    -e TEST_MODE=true \
    -e MOCK_EXTERNAL_APIS=true \
    -e PYTEST_WORKERS=4 \
    gtd-coach-test:latest \
    python -m pytest tests/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit.xml \
        --json-report \
        --json-report-file=/app/test-results/report.json \
        -m "not requires_neo4j and not requires_api_keys" \
        --cov=gtd_coach \
        --cov-report=xml:/app/test-results/coverage.xml \
        --cov-report=term

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    # Display coverage summary if available
    if [ -f test-results/report.json ]; then
        echo -e "${YELLOW}Test Summary:${NC}"
        python3 -c "
import json
with open('test-results/report.json') as f:
    data = json.load(f)
    summary = data.get('summary', {})
    print(f\"  Total: {summary.get('total', 0)}\")
    print(f\"  Passed: {summary.get('passed', 0)}\")
    print(f\"  Failed: {summary.get('failed', 0)}\")
    print(f\"  Skipped: {summary.get('skipped', 0)}\")
" 2>/dev/null || echo "  (Could not parse test results)"
    fi
else
    echo -e "${RED}❌ Tests failed with exit code $EXIT_CODE${NC}"
    
    # Show failed tests if report exists
    if [ -f test-results/report.json ]; then
        echo -e "${RED}Failed tests:${NC}"
        python3 -c "
import json
with open('test-results/report.json') as f:
    data = json.load(f)
    for test in data.get('tests', []):
        if test.get('outcome') == 'failed':
            print(f\"  - {test.get('nodeid', 'Unknown test')}\")
" 2>/dev/null || echo "  (Could not parse failed tests)"
    fi
fi

echo -e "${YELLOW}Test results saved to test-results/${NC}"
exit $EXIT_CODE