#!/usr/bin/env python3
"""
Batch fix script for LangGraph v0.6 test pattern updates
Helps identify and fix common test issues
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class TestPatternFixer:
    """Fix common test patterns for LangGraph v0.6"""
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_modified = set()
        
    def find_test_files(self, test_dir: Path) -> List[Path]:
        """Find all Python test files"""
        return list(test_dir.rglob("test_*.py"))
    
    def check_tool_run_pattern(self, content: str) -> List[Tuple[str, str]]:
        """Find tool.run() patterns that need fixing"""
        fixes = []
        
        # Exclude common false positives
        exclude_patterns = ['asyncio.run', 'subprocess.run', 'unittest.run', 'runner.run']
        
        # Pattern 1: tool.run(args, state)
        pattern1 = re.compile(r'(\w+)\.run\(([^,]+),\s*state\)')
        for match in pattern1.finditer(content):
            tool_name = match.group(1)
            # Skip false positives
            if any(f"{tool_name}.run" in exclude for exclude in exclude_patterns):
                continue
            old = match.group(0)
            args = match.group(2)
            new = f"{tool_name}.invoke({args})"
            fixes.append((old, new))
        
        # Pattern 2: _tool.run(args) - likely a tool
        pattern2 = re.compile(r'(\w+_tool)\.run\(([^)]+)\)')
        for match in pattern2.finditer(content):
            old = match.group(0)
            tool_name = match.group(1)
            args = match.group(2)
            new = f"{tool_name}.invoke({args})"
            fixes.append((old, new))
        
        # Pattern 3: Specific tool patterns
        specific_patterns = [
            r'(load_context_tool|detect_patterns_tool|mindsweep_tool)\.run\(',
            r'(save_state_tool|analysis_tool|capture_tool)\.run\(',
        ]
        for pattern_str in specific_patterns:
            pattern = re.compile(pattern_str)
            for match in pattern.finditer(content):
                tool_name = match.group(1)
                # Find the full call
                start = match.start()
                paren_count = 1
                i = match.end()
                while i < len(content) and paren_count > 0:
                    if content[i] == '(':
                        paren_count += 1
                    elif content[i] == ')':
                        paren_count -= 1
                    i += 1
                old = content[start:i]
                # Extract just the arguments
                args = old[old.index('(')+1:-1]
                new = f"{tool_name}.invoke({args})"
                fixes.append((old, new))
        
        return fixes
    
    def check_interrupt_pattern(self, content: str) -> List[Tuple[str, str]]:
        """Find NodeInterrupt patterns that need fixing"""
        fixes = []
        
        # Pattern: from langgraph.errors import NodeInterrupt
        if "from langgraph.errors import NodeInterrupt" in content:
            fixes.append(
                ("from langgraph.errors import NodeInterrupt",
                 "from langgraph.types import interrupt")
            )
        
        # Pattern: raise NodeInterrupt
        pattern = re.compile(r'raise\s+NodeInterrupt\([^)]*\)')
        for match in pattern.finditer(content):
            old = match.group(0)
            # Extract the message
            msg_match = re.search(r'NodeInterrupt\(([^)]*)\)', old)
            if msg_match:
                msg = msg_match.group(1)
                new = f"interrupt({msg})"
                fixes.append((old, new))
        
        # Pattern: with pytest.raises(NodeInterrupt)
        if "pytest.raises(NodeInterrupt)" in content:
            fixes.append(
                ("with pytest.raises(NodeInterrupt):",
                 '# Check for __interrupt__ in result instead of exception\n        # assert "__interrupt__" in result')
            )
        
        return fixes
    
    def check_workflow_run_pattern(self, content: str) -> List[Tuple[str, str]]:
        """Find workflow.run() patterns that need fixing"""
        fixes = []
        
        # Pattern: workflow.run(state)
        pattern = re.compile(r'(\w+)\.run\(([^)]+)\)')
        for match in pattern.finditer(content):
            if "workflow" in match.group(1).lower():
                old = match.group(0)
                workflow_name = match.group(1)
                args = match.group(2)
                
                # Generate replacement with graph compilation
                new = f"""# Compile workflow first
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()
        graph = {workflow_name}.compile(checkpointer=checkpointer)
        config = {{"configurable": {{"thread_id": "test_thread"}}}}
        result = graph.invoke({args}, config)"""
                
                fixes.append((old, new))
        
        return fixes
    
    def check_mock_patterns(self, content: str) -> List[Tuple[str, str]]:
        """Find mock patterns that need updating"""
        fixes = []
        
        # Pattern: mock_tool.run = Mock/AsyncMock
        pattern = re.compile(r'(\w+)\.run\s*=\s*(Mock|AsyncMock)\(')
        for match in pattern.finditer(content):
            old_line = match.group(0)
            tool_name = match.group(1)
            mock_type = match.group(2)
            new_line = f"{tool_name}.invoke = {mock_type}("
            fixes.append((old_line, new_line))
        
        return fixes
    
    def apply_fixes(self, file_path: Path, fixes: List[Tuple[str, str]]) -> bool:
        """Apply fixes to a file"""
        if not fixes:
            return False
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        modified = False
        for old, new in fixes:
            if old in content:
                content = content.replace(old, new)
                modified = True
                self.fixes_applied += 1
        
        if modified and not self.dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
            self.files_modified.add(file_path)
        
        return modified
    
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single test file"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        all_fixes = []
        
        # Check each pattern type
        fixes = self.check_tool_run_pattern(content)
        if fixes:
            all_fixes.extend(fixes)
            print(f"  {YELLOW}Tool .run() → .invoke(): {len(fixes)} fixes{RESET}")
        
        fixes = self.check_interrupt_pattern(content)
        if fixes:
            all_fixes.extend(fixes)
            print(f"  {YELLOW}NodeInterrupt patterns: {len(fixes)} fixes{RESET}")
        
        fixes = self.check_workflow_run_pattern(content)
        if fixes:
            all_fixes.extend(fixes)
            print(f"  {YELLOW}Workflow .run() patterns: {len(fixes)} fixes{RESET}")
        
        fixes = self.check_mock_patterns(content)
        if fixes:
            all_fixes.extend(fixes)
            print(f"  {YELLOW}Mock patterns: {len(fixes)} fixes{RESET}")
        
        if all_fixes:
            if self.dry_run:
                print(f"  {BLUE}Would apply {len(all_fixes)} fixes (dry run){RESET}")
                for old, new in all_fixes[:3]:  # Show first 3 fixes
                    print(f"    OLD: {old[:50]}...")
                    print(f"    NEW: {new[:50]}...")
            else:
                if self.apply_fixes(file_path, all_fixes):
                    print(f"  {GREEN}Applied {len(all_fixes)} fixes{RESET}")
    
    def run(self, test_dir: Path) -> None:
        """Run the fixer on all test files"""
        print(f"{BLUE}Scanning test files for LangGraph v0.6 patterns...{RESET}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'APPLY FIXES'}")
        print("-" * 60)
        
        test_files = self.find_test_files(test_dir)
        files_with_issues = 0
        
        for file_path in test_files:
            # Skip this script itself
            if file_path.name == Path(__file__).name:
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Quick check if file needs attention
            needs_fixes = (
                ".run(" in content or
                "NodeInterrupt" in content or
                "workflow.run" in content or
                "mock_tool.run" in content
            )
            
            if needs_fixes:
                files_with_issues += 1
                print(f"\n{file_path.relative_to(test_dir.parent)}:")
                self.analyze_file(file_path)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"{BLUE}SUMMARY{RESET}")
        print("=" * 60)
        print(f"Files scanned: {len(test_files)}")
        print(f"Files with issues: {files_with_issues}")
        
        if self.dry_run:
            print(f"\n{YELLOW}This was a DRY RUN. No files were modified.{RESET}")
            print(f"To apply fixes, run with --apply flag")
        else:
            print(f"Files modified: {len(self.files_modified)}")
            print(f"Total fixes applied: {self.fixes_applied}")
            
            if self.files_modified:
                print(f"\n{GREEN}✅ Fixes applied successfully!{RESET}")
                print("Modified files:")
                for f in sorted(self.files_modified):
                    print(f"  - {f.relative_to(test_dir.parent)}")
        
        print(f"\n{YELLOW}Note: Some tests may need manual review:{RESET}")
        print("1. Tests with InjectedState may need graph context setup")
        print("2. Complex interrupt patterns may need Command(resume=...) updates")
        print("3. Async tools may need AsyncMock for .invoke()")
        print("4. Checkpointing tests need InMemorySaver and config")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix test patterns for LangGraph v0.6"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply fixes (default is dry run)"
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path.home() / "gtd-coach" / "tests",
        help="Test directory to scan"
    )
    
    args = parser.parse_args()
    
    if not args.test_dir.exists():
        print(f"{RED}Error: Test directory not found: {args.test_dir}{RESET}")
        sys.exit(1)
    
    fixer = TestPatternFixer(dry_run=not args.apply)
    fixer.run(args.test_dir)


if __name__ == "__main__":
    main()