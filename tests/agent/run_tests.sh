#!/bin/bash

# GTD Agent Test Runner
# Run various test configurations easily

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
PARALLEL=false

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-n)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            echo "GTD Agent Test Runner"
            echo ""
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit          Run unit tests only"
            echo "  --integration   Run integration tests only"
            echo "  --coverage      Generate coverage report"
            echo "  --verbose, -v   Verbose output"
            echo "  --parallel, -n  Run tests in parallel"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                    # Run all tests"
            echo "  ./run_tests.sh --unit --coverage  # Run unit tests with coverage"
            echo "  ./run_tests.sh --parallel -v      # Run all tests in parallel with verbose output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add test type filter
if [ "$TEST_TYPE" = "unit" ]; then
    PYTEST_CMD="$PYTEST_CMD -m unit"
    print_color "$YELLOW" "Running unit tests only..."
elif [ "$TEST_TYPE" = "integration" ]; then
    PYTEST_CMD="$PYTEST_CMD -m integration"
    print_color "$YELLOW" "Running integration tests only..."
else
    print_color "$YELLOW" "Running all tests..."
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=gtd_coach.agent --cov-report=term-missing --cov-report=html"
    print_color "$YELLOW" "Coverage reporting enabled..."
fi

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
    print_color "$YELLOW" "Parallel execution enabled..."
fi

# Add color output
PYTEST_CMD="$PYTEST_CMD --color=yes"

# Change to test directory
cd "$(dirname "$0")"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_color "$RED" "Error: pytest is not installed"
    echo "Please install test dependencies: pip install -r requirements-test.txt"
    exit 1
fi

# Run the tests
print_color "$GREEN" "Executing: $PYTEST_CMD"
echo ""

if $PYTEST_CMD; then
    echo ""
    print_color "$GREEN" "✅ All tests passed!"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        print_color "$YELLOW" "Coverage report generated in htmlcov/index.html"
        echo "Open with: open htmlcov/index.html"
    fi
else
    echo ""
    print_color "$RED" "❌ Some tests failed"
    exit 1
fi