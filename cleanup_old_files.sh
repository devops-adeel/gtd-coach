#!/bin/bash

# Script to clean up old files after successful reorganization
# Run this after confirming the new structure works

echo "🧹 Cleaning up old files from GTD Coach reorganization..."
echo ""

# Old Python files that were moved to gtd_coach package
OLD_PYTHON_FILES=(
    "gtd-review.py"
    "adhd_patterns.py"
    "pattern_detector.py"
    "memory_enhancer.py"
    "graphiti_integration.py"
    "langfuse_tracker.py"
    "timing_integration.py"
    "timing_comparison.py"
    "generate_summary.py"  # Now in scripts/
)

# Old documentation files that were consolidated
OLD_DOCS=(
    "DOCKER_DEPLOYMENT.md"
    "LANGFUSE_INTEGRATION.md"
    "TIMING_SETUP.md"
    "TIMING_SIMPLE_SETUP.md"
    "USAGE_GUIDE.md"
    "SETUP_COMPLETE.md"
    "QUICK_REFERENCE.md"
    "KNOWN_ISSUES.md"
    "GRAPHITI_INTEGRATION.md"
    "GRAPHITI_IMPROVEMENTS.md"
    "GRAPHITI_OPTIMIZATIONS_SUMMARY.md"
    "README_OLD.md"
)

# Old Docker files
OLD_DOCKER_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-run.sh"
    "start-coach.sh"
)

# Old test files that should be in tests/
OLD_TEST_FILES=(
    "test-coach.py"
    "test-minimal.py"
    "test-simple-prompt.py"
)

# Files to keep (do not delete)
KEEP_FILES=(
    "test_structure.py"  # Useful for verification
    "requirements.txt"   # Essential
    "CLAUDE.md"         # Project instructions
    "CHANGELOG.md"      # Migration guide
    "README.md"         # New navigation hub
)

echo "Files to be removed:"
echo "==================="

echo ""
echo "Old Python files:"
for file in "${OLD_PYTHON_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""
echo "Old documentation:"
for file in "${OLD_DOCS[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""
echo "Old Docker/script files:"
for file in "${OLD_DOCKER_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""
echo "Old test files:"
for file in "${OLD_TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""
echo "==================="
echo ""
read -p "Do you want to remove these files? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing files..."
    
    for file in "${OLD_PYTHON_FILES[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "✓ Removed $file"
        fi
    done
    
    for file in "${OLD_DOCS[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "✓ Removed $file"
        fi
    done
    
    for file in "${OLD_DOCKER_FILES[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "✓ Removed $file"
        fi
    done
    
    for file in "${OLD_TEST_FILES[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "✓ Removed $file"
        fi
    done
    
    echo ""
    echo "✅ Cleanup complete!"
    echo ""
    echo "Files kept for reference:"
    for file in "${KEEP_FILES[@]}"; do
        if [ -f "$file" ]; then
            echo "  - $file"
        fi
    done
else
    echo "Cleanup cancelled."
fi