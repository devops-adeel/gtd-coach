#!/bin/bash
# Convenience script to run GTD Coach in Docker/OrbStack
# This avoids Python "externally managed environment" issues

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service=$1
    local port=$2
    local name=$3
    
    if curl -s --connect-timeout 2 "http://localhost:$port" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is running on port $port${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $name not detected on port $port${NC}"
        return 1
    fi
}

# Function to show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  review       Run the GTD weekly review (default)"
    echo "  test         Test Langfuse integration"
    echo "  test-trace-linking  Test prompt-to-trace linking (E2E)"
    echo "  timing       Test Timing app integration"
    echo "  analyze-timing Analyze your Timing data for GTD alignment"
    echo "  summary      Generate weekly summary"
    echo "  build        Build the Docker image"
    echo "  shell        Open a shell in the container"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Run the review"
    echo "  $0 test         # Test Langfuse"
    echo "  $0 summary      # Generate summary"
}

# Default command
COMMAND="${1:-review}"

# Handle commands
case "$COMMAND" in
    help|--help|-h)
        usage
        exit 0
        ;;
    
    build)
        echo "🔨 Building GTD Coach Docker image..."
        docker compose build
        echo -e "${GREEN}✓ Build complete${NC}"
        exit 0
        ;;
esac

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if Docker/OrbStack is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker/OrbStack is not running${NC}"
    echo "Please start OrbStack first"
    exit 1
fi

# Check services
check_service "1234" "1234" "LM Studio"
LM_STUDIO_OK=$?

check_service "3000" "3000" "Langfuse"
LANGFUSE_OK=$?

if [ $LM_STUDIO_OK -ne 0 ]; then
    echo -e "${RED}❌ LM Studio is required for GTD Coach${NC}"
    echo "Please start LM Studio server and load the model"
    exit 1
fi

if [ $LANGFUSE_OK -ne 0 ]; then
    echo -e "${YELLOW}Note: Langfuse is not running - performance tracking will be disabled${NC}"
fi

# Build image if it doesn't exist
if ! docker images | grep -q "gtd-coach"; then
    echo "🔨 First time setup - building Docker image..."
    docker compose build
fi

# Run the appropriate command
case "$COMMAND" in
    review)
        echo -e "\n${GREEN}🚀 Starting GTD Weekly Review in Docker${NC}"
        echo "================================================"
        echo ""
        docker compose run --rm gtd-coach
        ;;
    
    test)
        echo -e "\n${GREEN}🧪 Testing Langfuse Integration${NC}"
        echo "================================"
        echo ""
        docker compose run --rm test-langfuse
        ;;
    
    summary)
        echo -e "\n${GREEN}📊 Generating Weekly Summary${NC}"
        echo "============================"
        echo ""
        docker compose run --rm generate-summary
        ;;
    
    timing)
        echo -e "\n${GREEN}⏱️ Testing Timing App Integration${NC}"
        echo "================================="
        echo ""
        docker compose run --rm gtd-coach python3 test_timing_integration.py
        ;;
    
    test-trace-linking)
        echo -e "\n${GREEN}🔗 Testing Prompt-to-Trace Linking (E2E)${NC}"
        echo "======================================="
        echo ""
        docker compose run --rm gtd-coach python3 test_e2e_trace_linking.py
        ;;
    
    analyze-timing)
        echo -e "\n${GREEN}📊 Analyzing Timing Data for GTD Alignment${NC}"
        echo "=========================================="
        echo ""
        docker compose run --rm gtd-coach python3 analyze_timing.py
        ;;
    
    shell)
        echo -e "\n${GREEN}🐚 Opening shell in GTD Coach container${NC}"
        echo "======================================="
        echo ""
        docker compose run --rm gtd-coach /bin/bash
        ;;
    
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac