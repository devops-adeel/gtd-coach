#!/usr/bin/env python3
"""Verify that all dependencies are at the correct versions."""

import sys
import importlib.metadata

def verify_dependencies():
    """Check that all required packages are installed at correct versions."""
    
    print('🔍 Final Verification of Updated Dependencies')
    print('=' * 50)
    
    requirements = {
        'requests': '2.32.4',
        'python-dotenv': '1.1.1',
        'neo4j': '5.28.2',
        'graphiti-core': '0.18.5',
        'langfuse': '3.2.3'
    }
    
    all_correct = True
    
    for package, expected_version in requirements.items():
        try:
            installed_version = importlib.metadata.version(package)
            status = '✅' if installed_version == expected_version else '❌'
            
            if installed_version != expected_version:
                all_correct = False
                
            print(f'{status} {package}: {installed_version} (expected: {expected_version})')
            
        except importlib.metadata.PackageNotFoundError:
            print(f'❌ {package}: Not installed')
            all_correct = False
        except Exception as e:
            print(f'❌ {package}: Error checking - {e}')
            all_correct = False
    
    print('=' * 50)
    
    if all_correct:
        print('✅ All packages at correct versions!')
        return 0
    else:
        print('❌ Some packages need attention')
        return 1

if __name__ == '__main__':
    sys.exit(verify_dependencies())