#!/bin/bash

# Quick activation script for GTD Coach development

echo "🚀 Activating GTD Coach development environment..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating it now..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import langfuse" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

echo ""
echo "✅ Environment ready!"
echo ""
echo "You can now run:"
echo "  python -m gtd_coach          # Run the coach"
echo "  python test_structure.py     # Test the structure"
echo "  ./scripts/docker-run.sh      # Run in Docker"
echo ""
echo "To deactivate the environment, run: deactivate"