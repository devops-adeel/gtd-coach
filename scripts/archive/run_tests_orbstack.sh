#!/bin/bash
# Comprehensive test runner for OrbStack/Docker with all dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_TYPE="${1:-all}"
REBUILD="${2:-false}"

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}GTD Coach Test Suite - OrbStack/Docker${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_orbstack() {
    if ! docker version > /dev/null 2>&1; then
        echo -e "${RED}❌ OrbStack/Docker is not running${NC}"
        echo "Please start OrbStack and try again"
        exit 1
    fi
    echo -e "${GREEN}✓ OrbStack/Docker is running${NC}"
}

build_images() {
    echo -e "${YELLOW}🔨 Building Docker images with all dependencies...${NC}"
    
    # Build all targets
    docker compose build --no-cache
    
    # Also build test-specific image
    docker compose --profile test build
    
    echo -e "${GREEN}✓ Images built successfully${NC}"
}

start_services() {
    echo -e "${YELLOW}🚀 Starting required services...${NC}"
    
    # Start Neo4j first and wait for it to be healthy
    docker compose up -d neo4j
    
    echo -n "Waiting for Neo4j to be ready..."
    for i in {1..30}; do
        if docker compose exec neo4j cypher-shell -u neo4j -p gtd-password "RETURN 1" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Check if Neo4j is actually ready
    if ! docker compose exec neo4j cypher-shell -u neo4j -p gtd-password "RETURN 1" > /dev/null 2>&1; then
        echo -e " ${RED}✗${NC}"
        echo -e "${RED}Neo4j failed to start properly${NC}"
        docker compose logs neo4j
        exit 1
    fi
}

run_unit_tests() {
    echo -e "${YELLOW}🧪 Running unit tests...${NC}"
    
    docker compose run --rm test-runner python -m pytest \
        tests/unit/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit-unit.xml \
        --json-report \
        --json-report-file=/app/test-results/report-unit.json \
        --cov=gtd_coach \
        --cov-report=xml:/app/test-results/coverage-unit.xml \
        --cov-report=term \
        -m "not integration and not requires_neo4j and not requires_api_keys" \
        || true
}

run_integration_tests() {
    echo -e "${YELLOW}🔗 Running integration tests...${NC}"
    
    docker compose run --rm test-runner python -m pytest \
        tests/integration/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit-integration.xml \
        --json-report \
        --json-report-file=/app/test-results/report-integration.json \
        --cov=gtd_coach \
        --cov-report=xml:/app/test-results/coverage-integration.xml \
        --cov-report=term \
        -m "integration or requires_neo4j" \
        || true
}

run_agent_tests() {
    echo -e "${YELLOW}🤖 Running agent tests (LangGraph)...${NC}"
    
    docker compose run --rm test-runner python -m pytest \
        tests/agent/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit-agent.xml \
        --json-report \
        --json-report-file=/app/test-results/report-agent.json \
        --cov=gtd_coach/agent \
        --cov-report=xml:/app/test-results/coverage-agent.xml \
        --cov-report=term \
        || true
}

run_all_tests() {
    echo -e "${YELLOW}🎯 Running all tests...${NC}"
    
    docker compose run --rm test-runner python -m pytest \
        tests/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-results/junit-all.xml \
        --json-report \
        --json-report-file=/app/test-results/report-all.json \
        --cov=gtd_coach \
        --cov-report=xml:/app/test-results/coverage-all.xml \
        --cov-report=html:/app/test-results/htmlcov \
        --cov-report=term \
        || true
}

run_specific_test() {
    local test_path=$1
    echo -e "${YELLOW}🎯 Running specific test: ${test_path}${NC}"
    
    docker compose run --rm test-runner python -m pytest \
        "${test_path}" \
        -vvs \
        --tb=short \
        --capture=no \
        || true
}

parse_results() {
    if [ -f test-results/report-all.json ]; then
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Test Results Summary:${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
        
        python3 -c "
import json
import sys

try:
    with open('test-results/report-all.json') as f:
        data = json.load(f)
        summary = data.get('summary', {})
        
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        skipped = summary.get('skipped', 0)
        errors = summary.get('error', 0)
        
        print(f'  Total:   {total}')
        print(f'  ✅ Passed:  {passed}')
        print(f'  ❌ Failed:  {failed}')
        print(f'  ⏭️  Skipped: {skipped}')
        if errors > 0:
            print(f'  🔥 Errors:  {errors}')
        
        if failed > 0:
            print('\nFailed tests:')
            for test in data.get('tests', []):
                if test.get('outcome') == 'failed':
                    print(f\"  • {test.get('nodeid', 'Unknown test')}\")
                    if 'call' in test and 'longrepr' in test['call']:
                        print(f\"    {test['call']['longrepr'][:200]}...\")
        
        # Calculate pass rate
        if total > 0:
            pass_rate = (passed / total) * 100
            print(f'\n📊 Pass Rate: {pass_rate:.1f}%')
            
            if pass_rate == 100:
                print('🎉 All tests passed!')
                sys.exit(0)
            elif pass_rate >= 80:
                print('👍 Good coverage, but some tests need attention')
                sys.exit(1)
            else:
                print('⚠️  Significant test failures detected')
                sys.exit(1)
except Exception as e:
    print(f'Could not parse test results: {e}')
    sys.exit(1)
" || EXIT_CODE=$?
    else
        echo -e "${YELLOW}No test results found${NC}"
        EXIT_CODE=1
    fi
}

cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker compose --profile test down
}

# Main execution
print_header

# Parse command line arguments
case "$TEST_TYPE" in
    unit)
        RUNNER=run_unit_tests
        ;;
    integration)
        RUNNER=run_integration_tests
        ;;
    agent)
        RUNNER=run_agent_tests
        ;;
    all)
        RUNNER=run_all_tests
        ;;
    specific)
        if [ -z "$3" ]; then
            echo -e "${RED}Please specify a test path${NC}"
            echo "Usage: $0 specific <rebuild> <test_path>"
            exit 1
        fi
        RUNNER="run_specific_test $3"
        ;;
    *)
        echo "Usage: $0 [unit|integration|agent|all|specific] [rebuild] [test_path]"
        echo ""
        echo "Examples:"
        echo "  $0 all              # Run all tests"
        echo "  $0 unit             # Run only unit tests"
        echo "  $0 agent rebuild    # Rebuild and run agent tests"
        echo "  $0 specific false tests/agent/test_tools.py::TestAdaptiveTools"
        exit 1
        ;;
esac

# Check OrbStack/Docker
check_orbstack

# Build images if requested or if they don't exist
if [ "$REBUILD" = "true" ] || ! docker images | grep -q "gtd-coach.*test"; then
    build_images
fi

# Create test results directory
mkdir -p test-results

# Start services
start_services

# Run tests
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Running Test Suite: ${TEST_TYPE}${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

$RUNNER

# Parse and display results
parse_results

# Cleanup
cleanup

echo ""
echo -e "${GREEN}✅ Test execution complete!${NC}"
echo -e "${YELLOW}📁 Results saved to: test-results/${NC}"

# Generate HTML coverage report URL if running locally
if [ -d test-results/htmlcov ]; then
    echo -e "${BLUE}📊 Coverage report: file://$(pwd)/test-results/htmlcov/index.html${NC}"
fi

exit ${EXIT_CODE:-0}