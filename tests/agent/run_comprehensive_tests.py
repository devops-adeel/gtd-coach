#!/usr/bin/env python3
"""
Comprehensive test runner for Phase 4 test suite
Runs all test categories with coverage reporting
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import pytest
import coverage


class TestRunner:
    """Comprehensive test runner with coverage analysis"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.test_dir = self.root_dir / "tests"
        self.agent_test_dir = self.test_dir / "agent"
        self.coverage_dir = self.root_dir / "htmlcov"
        self.results = {}
        
    def run_test_category(self, category: str, test_files: List[str], markers: str = None) -> Tuple[bool, Dict]:
        """Run a specific category of tests"""
        print(f"\n{'='*60}")
        print(f"Running {category} Tests")
        print(f"{'='*60}")
        
        cmd = ["pytest", "-v", "--tb=short"]
        
        # Add markers if specified
        if markers:
            cmd.extend(["-m", markers])
        
        # Add specific test files
        for test_file in test_files:
            test_path = self.agent_test_dir / test_file
            if test_path.exists():
                cmd.append(str(test_path))
        
        # Add coverage options
        cmd.extend([
            f"--cov={self.root_dir}/gtd_coach/agent",
            "--cov-report=term-missing",
            "--cov-report=html",
            f"--cov-report=json:{self.root_dir}/coverage_{category}.json"
        ])
        
        # Run tests
        start_time = datetime.now()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Parse results
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        # Extract test counts
        test_counts = self._parse_test_output(output)
        
        # Load coverage data
        coverage_file = self.root_dir / f"coverage_{category}.json"
        coverage_data = {}
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_json = json.load(f)
                coverage_data = {
                    "percent_covered": coverage_json.get("totals", {}).get("percent_covered", 0),
                    "num_statements": coverage_json.get("totals", {}).get("num_statements", 0),
                    "missing_lines": coverage_json.get("totals", {}).get("missing_lines", 0)
                }
        
        return success, {
            "category": category,
            "success": success,
            "duration": duration,
            "test_counts": test_counts,
            "coverage": coverage_data,
            "output": output if not success else ""
        }
    
    def _parse_test_output(self, output: str) -> Dict:
        """Parse pytest output for test counts"""
        counts = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for line in output.split('\n'):
            if 'passed' in line and 'failed' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'passed' in part and i > 0:
                        counts['passed'] = int(parts[i-1])
                    elif 'failed' in part and i > 0:
                        counts['failed'] = int(parts[i-1])
                    elif 'skipped' in part and i > 0:
                        counts['skipped'] = int(parts[i-1])
                    elif 'error' in part and i > 0:
                        counts['errors'] = int(parts[i-1])
        
        return counts
    
    def run_all_tests(self):
        """Run all test categories"""
        print("\n" + "="*60)
        print("GTD Coach Agent - Comprehensive Test Suite")
        print("Phase 4 Implementation")
        print("="*60)
        
        test_categories = [
            {
                "name": "Unit Tests - State & Validation",
                "files": ["test_state.py", "test_tools.py"],
                "markers": "unit"
            },
            {
                "name": "Checkpointing Tests",
                "files": ["test_checkpointing.py"],
                "markers": None
            },
            {
                "name": "Interrupt/Resume Tests",
                "files": ["test_interrupt_resume.py"],
                "markers": None
            },
            {
                "name": "Workflow Tests",
                "files": ["test_workflow.py"],
                "markers": None
            },
            {
                "name": "Integration Tests",
                "files": ["test_integration.py"],
                "markers": "integration"
            },
            {
                "name": "Shadow Mode Tests",
                "files": ["../integration/test_workflow_with_interrupts.py"],
                "markers": None
            }
        ]
        
        all_success = True
        
        for category in test_categories:
            success, result = self.run_test_category(
                category["name"],
                category["files"],
                category.get("markers")
            )
            
            self.results[category["name"]] = result
            all_success = all_success and success
            
            # Print summary for this category
            self._print_category_summary(result)
        
        # Generate final report
        self._generate_final_report(all_success)
        
        return all_success
    
    def _print_category_summary(self, result: Dict):
        """Print summary for a test category"""
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"\n{result['category']}: {status}")
        
        counts = result["test_counts"]
        print(f"  Tests: {counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped")
        
        if result["coverage"]:
            cov = result["coverage"]
            print(f"  Coverage: {cov['percent_covered']:.1f}% ({cov['num_statements']} statements)")
        
        print(f"  Duration: {result['duration']:.2f}s")
    
    def _generate_final_report(self, all_success: bool):
        """Generate final test report"""
        print("\n" + "="*60)
        print("FINAL TEST REPORT")
        print("="*60)
        
        total_passed = sum(r["test_counts"]["passed"] for r in self.results.values())
        total_failed = sum(r["test_counts"]["failed"] for r in self.results.values())
        total_skipped = sum(r["test_counts"]["skipped"] for r in self.results.values())
        total_duration = sum(r["duration"] for r in self.results.values())
        
        # Calculate overall coverage
        coverage_percentages = [r["coverage"].get("percent_covered", 0) 
                               for r in self.results.values() 
                               if r["coverage"]]
        avg_coverage = sum(coverage_percentages) / len(coverage_percentages) if coverage_percentages else 0
        
        print(f"\nTotal Tests Run: {total_passed + total_failed}")
        print(f"  ✅ Passed: {total_passed}")
        print(f"  ❌ Failed: {total_failed}")
        print(f"  ⏭️ Skipped: {total_skipped}")
        print(f"\nOverall Coverage: {avg_coverage:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Critical path coverage check
        critical_paths = ["Checkpointing Tests", "Interrupt/Resume Tests", "Workflow Tests"]
        critical_coverage = []
        
        for path in critical_paths:
            if path in self.results and self.results[path]["coverage"]:
                critical_coverage.append(self.results[path]["coverage"]["percent_covered"])
        
        if critical_coverage:
            critical_avg = sum(critical_coverage) / len(critical_coverage)
            print(f"\nCritical Path Coverage: {critical_avg:.1f}%")
            
            if critical_avg >= 95:
                print("  ✅ Meets 95% critical path target")
            else:
                print(f"  ⚠️ Below 95% target (current: {critical_avg:.1f}%)")
        
        # Overall status
        print("\n" + "="*60)
        if all_success and avg_coverage >= 85:
            print("✅ ALL TESTS PASSED - Coverage target met!")
        elif all_success:
            print(f"⚠️ Tests passed but coverage below 85% target ({avg_coverage:.1f}%)")
        else:
            print("❌ TEST FAILURES DETECTED - Please review")
        print("="*60)
        
        # Save detailed report
        self._save_detailed_report()
    
    def _save_detailed_report(self):
        """Save detailed test report to file"""
        report_file = self.root_dir / "test_report_phase4.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total_passed": sum(r["test_counts"]["passed"] for r in self.results.values()),
                "total_failed": sum(r["test_counts"]["failed"] for r in self.results.values()),
                "total_skipped": sum(r["test_counts"]["skipped"] for r in self.results.values()),
                "total_duration": sum(r["duration"] for r in self.results.values()),
                "categories_run": len(self.results)
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
    
    def run_coverage_analysis(self):
        """Run detailed coverage analysis"""
        print("\n" + "="*60)
        print("Running Coverage Analysis")
        print("="*60)
        
        cov = coverage.Coverage(source=[str(self.root_dir / "gtd_coach/agent")])
        cov.start()
        
        # Run all tests with coverage
        pytest.main([
            str(self.agent_test_dir),
            "-v",
            "--tb=short",
            f"--cov={self.root_dir}/gtd_coach/agent",
            "--cov-report=html",
            "--cov-report=term-missing:skip-covered",
            "--cov-branch"
        ])
        
        cov.stop()
        cov.save()
        
        # Generate reports
        print("\nGenerating coverage reports...")
        cov.html_report(directory=str(self.coverage_dir))
        
        print(f"\nHTML coverage report: {self.coverage_dir}/index.html")
        
        # Analyze uncovered code
        self._analyze_coverage_gaps(cov)
    
    def _analyze_coverage_gaps(self, cov):
        """Analyze and report coverage gaps"""
        print("\n" + "="*60)
        print("Coverage Gap Analysis")
        print("="*60)
        
        analysis = cov.analysis2(str(self.root_dir / "gtd_coach/agent/__init__.py"))
        missing_lines = analysis[3]
        
        if missing_lines:
            print(f"\nUncovered lines in agent/__init__.py: {missing_lines}")
        
        # Check specific critical files
        critical_files = [
            "gtd_coach/agent/state.py",
            "gtd_coach/agent/tools.py",
            "gtd_coach/agent/workflows/weekly_review.py",
            "gtd_coach/agent/workflows/daily_capture.py"
        ]
        
        for file_path in critical_files:
            full_path = self.root_dir / file_path
            if full_path.exists():
                analysis = cov.analysis2(str(full_path))
                if analysis[3]:  # Missing lines
                    print(f"\nUncovered in {file_path}: lines {analysis[3][:10]}...")


def main():
    """Main entry point"""
    runner = TestRunner()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--coverage":
            runner.run_coverage_analysis()
        elif sys.argv[1] == "--quick":
            # Run only unit tests for quick feedback
            success, result = runner.run_test_category(
                "Quick Unit Tests",
                ["test_state.py", "test_tools.py"],
                "unit"
            )
            runner._print_category_summary(result)
            sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()