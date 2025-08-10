#!/usr/bin/env python3
"""Test script to verify the new structure works correctly."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all imports work with the new structure."""
    print("Testing new structure imports...")
    
    try:
        # Test main coach import
        from gtd_coach.coach import GTDCoach
        print("✓ GTDCoach import successful")
        
        # Test pattern imports
        from gtd_coach.patterns.adhd_metrics import ADHDPatternDetector
        print("✓ ADHDPatternDetector import successful")
        
        from gtd_coach.patterns.detector import PatternDetector
        print("✓ PatternDetector import successful")
        
        # Test integration imports
        from gtd_coach.integrations.graphiti import GraphitiMemory
        print("✓ GraphitiMemory import successful")
        
        from gtd_coach.integrations.timing import TimingAPI
        print("✓ TimingAPI import successful")
        
        from gtd_coach.integrations.langfuse import get_langfuse_client
        print("✓ Langfuse import successful")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        if "langfuse" in str(e).lower():
            print("\n📦 To fix this, activate the virtual environment and install dependencies:")
            print("  source venv/bin/activate")
            print("  pip install -r requirements.txt")
        return False

def test_file_structure():
    """Verify the file structure is correct."""
    print("\nVerifying file structure...")
    
    expected_paths = [
        "gtd_coach/__init__.py",
        "gtd_coach/__main__.py",
        "gtd_coach/coach.py",
        "gtd_coach/patterns/__init__.py",
        "gtd_coach/patterns/adhd_metrics.py",
        "gtd_coach/patterns/detector.py",
        "gtd_coach/integrations/__init__.py",
        "gtd_coach/integrations/graphiti.py",
        "gtd_coach/integrations/timing.py",
        "gtd_coach/integrations/langfuse.py",
        "docs/USER_GUIDE.md",
        "docs/DEVELOPER.md",
        "docs/CONFIGURATION.md",
        "config/.env.example",
        "config/docker/Dockerfile",
        "config/docker/docker-compose.yml",
        "scripts/start-coach.sh",
        "scripts/docker-run.sh",
    ]
    
    all_exist = True
    for path in expected_paths:
        # Use parent.parent since test_structure.py is now in tests/
        full_path = Path(__file__).parent.parent / path
        if full_path.exists():
            print(f"✓ {path}")
        else:
            print(f"✗ {path} - NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ All expected files exist!")
    else:
        print("\n⚠️ Some files are missing")
    
    return all_exist

def main():
    """Run all tests."""
    print("=" * 50)
    print("GTD Coach Structure Verification")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test file structure
    structure_ok = test_file_structure()
    
    # Summary
    print("\n" + "=" * 50)
    if imports_ok and structure_ok:
        print("✅ VERIFICATION SUCCESSFUL - New structure is working!")
        sys.exit(0)
    else:
        print("❌ VERIFICATION FAILED - Check errors above")
        sys.exit(1)

if __name__ == "__main__":
    main()