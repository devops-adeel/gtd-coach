#!/bin/bash
# Simple test runner that uses existing services

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${GREEN}GTD Coach Test Runner (Simple)${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}"

# Check if Docker is running
if ! docker version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker/OrbStack is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Build test image if needed
if ! docker images | grep -q "gtd-coach.*test"; then
    echo -e "${YELLOW}Building test image...${NC}"
    docker build -f Dockerfile -t gtd-coach:test --target testing .
fi

# Create results directory
mkdir -p test-results

# Run tests in container with existing Neo4j
echo -e "${YELLOW}Running tests...${NC}"

docker run --rm \
    --network host \
    -v "$(pwd)/tests:/app/tests:ro" \
    -v "$(pwd)/gtd_coach:/app/gtd_coach:ro" \
    -v "$(pwd)/test-results:/app/test-results" \
    -e TEST_MODE=true \
    -e MOCK_EXTERNAL_APIS=true \
    -e NEO4J_URI=bolt://localhost:7687 \
    -e NEO4J_USERNAME=neo4j \
    -e NEO4J_PASSWORD='!uK-TkCGWdrFfbZUw*j6' \
    -e PYTHONPATH=/app \
    gtd-coach:test \
    python -m pytest tests/agent/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit.xml \
        -x \
        --no-header \
        2>&1 | tee test-results/output.log

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${BLUE}════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Tests passed!${NC}"
else
    echo -e "${RED}❌ Tests failed (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}Check test-results/output.log for details${NC}"
fi

exit $EXIT_CODE