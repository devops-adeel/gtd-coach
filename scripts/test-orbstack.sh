#!/bin/bash
# Test runner optimized for OrbStack networking
# Ensures all services are accessible before running tests

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${GREEN}GTD Coach Test Runner - OrbStack Edition${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}"

# Function to check service connectivity
check_service() {
    local name=$1
    local url=$2
    local check_cmd=$3
    
    echo -n "Checking $name... "
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check if Docker is running
if ! docker version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker/OrbStack is not running${NC}"
    exit 1
fi

# Check critical services
echo -e "\n${YELLOW}Verifying service connectivity...${NC}"

# Check FalkorDB
check_service "FalkorDB (host)" \
    "localhost:6380" \
    "nc -zv localhost 6380"

# Check Langfuse
check_service "Langfuse" \
    "http://langfuse-web.langfuse-prod.orb.local" \
    "curl -s http://langfuse-web.langfuse-prod.orb.local/api/public/health | grep -q OK"

# Check LM Studio
check_service "LM Studio" \
    "http://localhost:1234" \
    "curl -s http://localhost:1234/v1/models | grep -q data"

# Build test image if needed
if [ "$1" == "--build" ] || ! docker images | grep -q "gtd-coach.*test"; then
    echo -e "\n${YELLOW}Building test image...${NC}"
    docker compose build test-runner
fi

# Create results directory
mkdir -p test-results

# Determine test scope
TEST_SCOPE="${1:-all}"
if [ "$TEST_SCOPE" == "--build" ]; then
    TEST_SCOPE="${2:-all}"
fi

# Set test path based on scope
case "$TEST_SCOPE" in
    unit)
        TEST_PATH="tests/unit/"
        echo -e "\n${YELLOW}Running unit tests only...${NC}"
        ;;
    integration)
        TEST_PATH="tests/integration/"
        echo -e "\n${YELLOW}Running integration tests only...${NC}"
        ;;
    memory)
        TEST_PATH="tests/unit/test_memory_persistence.py"
        echo -e "\n${YELLOW}Running memory persistence tests...${NC}"
        ;;
    agent)
        TEST_PATH="tests/agent/"
        echo -e "\n${YELLOW}Running agent tests...${NC}"
        ;;
    *)
        TEST_PATH="tests/"
        echo -e "\n${YELLOW}Running all tests...${NC}"
        ;;
esac

# Run tests with OrbStack networking configuration
echo -e "\n${BLUE}Starting test execution...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker run --rm \
    --network gtd-coach_gtd-network \
    -v "$(pwd)/tests:/app/tests:ro" \
    -v "$(pwd)/gtd_coach:/app/gtd_coach:ro" \
    -v "$(pwd)/test-results:/app/test-results" \
    -v "$(pwd)/.env.orbstack:/app/.env.orbstack:ro" \
    -e TEST_MODE=true \
    -e MOCK_EXTERNAL_APIS=${MOCK_EXTERNAL_APIS:-true} \
    -e FALKORDB_HOST=falkordb.local \
    -e FALKORDB_PORT=6379 \
    -e FALKORDB_DATABASE=shared_gtd_knowledge_test \
    -e LM_STUDIO_URL=http://host.orb.internal:1234 \
    -e LANGFUSE_HOST=http://langfuse-web.langfuse-prod.orb.local \
    -e GRAPHITI_GROUP_ID=test_group \
    -e PYTHONPATH=/app \
    -e PYTEST_WORKERS=${PYTEST_WORKERS:-auto} \
    gtd-coach:test \
    python -m pytest $TEST_PATH \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit.xml \
        --no-header \
        2>&1 | tee test-results/output.log

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${BLUE}════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    # Show summary if available
    if [ -f test-results/junit.xml ]; then
        TOTAL=$(grep -o 'tests="[0-9]*"' test-results/junit.xml | head -1 | grep -o '[0-9]*')
        FAILURES=$(grep -o 'failures="[0-9]*"' test-results/junit.xml | head -1 | grep -o '[0-9]*')
        ERRORS=$(grep -o 'errors="[0-9]*"' test-results/junit.xml | head -1 | grep -o '[0-9]*')
        
        echo -e "${GREEN}Total: $TOTAL tests${NC}"
        if [ "$FAILURES" != "0" ] || [ "$ERRORS" != "0" ]; then
            echo -e "${YELLOW}Failures: $FAILURES, Errors: $ERRORS${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Tests failed (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}Check test-results/output.log for details${NC}"
    
    # Show last few lines of failures
    echo -e "\n${YELLOW}Recent failures:${NC}"
    grep -A 5 "FAILED\|ERROR" test-results/output.log | tail -20 || true
fi

exit $EXIT_CODE