#!/usr/bin/env python3
"""
Coverage gap analysis for GTD Coach
Identifies untested code paths and generates targeted test recommendations
"""

import subprocess
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Set
import ast

class CoverageAnalyzer:
    """Analyze test coverage and identify gaps"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.source_dir = self.project_root / "gtd_coach"
        self.test_dir = self.project_root / "tests"
        
    def run_coverage(self) -> Dict:
        """Run coverage and generate reports"""
        print("Running coverage analysis...")
        
        # Run tests with coverage
        cmd = [
            "pytest", 
            str(self.test_dir),
            "--cov=gtd_coach",
            "--cov-report=xml",
            "--cov-report=json",
            "--cov-report=term-missing",
            "-q"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Coverage run completed with exit code: {result.returncode}")
            
            # Parse JSON coverage report
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    return json.load(f)
            else:
                print("Warning: coverage.json not found")
                return {}
        except Exception as e:
            print(f"Error running coverage: {e}")
            return {}
    
    def analyze_uncovered_code(self, coverage_data: Dict) -> Dict[str, List[Tuple[int, str]]]:
        """Identify uncovered code segments"""
        uncovered = {}
        
        if not coverage_data or "files" not in coverage_data:
            return uncovered
        
        for file_path, file_data in coverage_data["files"].items():
            # Skip test files
            if "test_" in file_path or "/tests/" in file_path:
                continue
            
            # Get missing lines
            missing_lines = file_data.get("missing_lines", [])
            if not missing_lines:
                continue
            
            # Read source file
            source_file = Path(file_path)
            if not source_file.exists():
                source_file = self.project_root / file_path
            
            if source_file.exists():
                with open(source_file) as f:
                    lines = f.readlines()
                
                uncovered_segments = []
                for line_num in missing_lines:
                    if 0 < line_num <= len(lines):
                        line_content = lines[line_num - 1].strip()
                        # Filter out trivial lines
                        if line_content and not line_content.startswith("#"):
                            uncovered_segments.append((line_num, line_content))
                
                if uncovered_segments:
                    uncovered[str(file_path)] = uncovered_segments
        
        return uncovered
    
    def identify_critical_gaps(self, uncovered: Dict) -> Dict[str, List]:
        """Identify critical uncovered code paths"""
        critical_patterns = {
            "error_handling": ["except", "raise", "finally"],
            "async_code": ["async ", "await ", "asyncio"],
            "state_management": ["state[", "state.get", "StateValidator"],
            "tool_calls": ["tool.", "invoke(", "Tool("],
            "interrupts": ["interrupt", "NodeInterrupt", "Command"],
            "checkpointing": ["checkpoint", "save", "restore"],
            "adhd_features": ["intervention", "focus", "adhd", "pattern"],
            "timing": ["timing", "Timer", "phase_time"],
        }
        
        critical_gaps = {}
        
        for file_path, segments in uncovered.items():
            file_gaps = []
            
            for line_num, line_content in segments:
                for category, patterns in critical_patterns.items():
                    if any(pattern in line_content.lower() for pattern in patterns):
                        file_gaps.append({
                            "line": line_num,
                            "content": line_content,
                            "category": category,
                            "priority": "HIGH" if category in ["error_handling", "state_management"] else "MEDIUM"
                        })
                        break
            
            if file_gaps:
                critical_gaps[file_path] = file_gaps
        
        return critical_gaps
    
    def analyze_test_distribution(self) -> Dict:
        """Analyze test distribution across modules"""
        test_distribution = {
            "unit": 0,
            "integration": 0,
            "agent": 0,
            "e2e": 0,
            "by_module": {}
        }
        
        # Count tests by category
        for test_file in self.test_dir.rglob("test_*.py"):
            category = test_file.parent.name
            if category in test_distribution:
                # Count test functions
                with open(test_file) as f:
                    content = f.read()
                    test_count = content.count("def test_") + content.count("async def test_")
                    test_distribution[category] += test_count
                    
                    # Track by module
                    module_name = test_file.stem.replace("test_", "")
                    test_distribution["by_module"][module_name] = test_count
        
        return test_distribution
    
    def generate_test_recommendations(self, critical_gaps: Dict) -> List[Dict]:
        """Generate recommendations for new tests"""
        recommendations = []
        
        # Group gaps by category
        gaps_by_category = {}
        for file_path, gaps in critical_gaps.items():
            for gap in gaps:
                category = gap["category"]
                if category not in gaps_by_category:
                    gaps_by_category[category] = []
                gaps_by_category[category].append({
                    "file": file_path,
                    "line": gap["line"],
                    "content": gap["content"]
                })
        
        # Generate recommendations
        test_templates = {
            "error_handling": """
@pytest.mark.asyncio
async def test_{module}_error_handling():
    '''Test error handling in {module}'''
    with pytest.raises(ExpectedError):
        # Test error condition
        pass
""",
            "async_code": """
@pytest.mark.asyncio
async def test_{module}_async_operation():
    '''Test async operations in {module}'''
    result = await async_function()
    assert result is not None
""",
            "state_management": """
def test_{module}_state_validation():
    '''Test state management in {module}'''
    state = StateValidator.ensure_required_fields({})
    # Test state mutations
    assert 'required_field' in state
""",
            "interrupts": """
def test_{module}_interrupt_handling():
    '''Test interrupt handling in {module}'''
    with pytest.raises(NodeInterrupt):
        # Test interrupt scenario
        pass
"""
        }
        
        for category, gaps in gaps_by_category.items():
            if category in test_templates:
                module = Path(gaps[0]["file"]).stem
                recommendations.append({
                    "category": category,
                    "priority": "HIGH" if category in ["error_handling", "state_management"] else "MEDIUM",
                    "test_count": len(gaps),
                    "template": test_templates[category].format(module=module),
                    "locations": gaps[:3]  # Show first 3 examples
                })
        
        return recommendations
    
    def calculate_metrics(self, coverage_data: Dict) -> Dict:
        """Calculate coverage metrics"""
        if not coverage_data:
            return {}
        
        totals = coverage_data.get("totals", {})
        files = coverage_data.get("files", {})
        
        # Calculate critical path coverage
        critical_paths = [
            "workflows/weekly_review.py",
            "workflows/daily_capture.py",
            "tools/",
            "state.py"
        ]
        
        critical_covered = 0
        critical_total = 0
        
        for file_path, file_data in files.items():
            if any(path in file_path for path in critical_paths):
                summary = file_data.get("summary", {})
                critical_covered += summary.get("covered_lines", 0)
                critical_total += summary.get("num_statements", 0)
        
        critical_coverage = (critical_covered / critical_total * 100) if critical_total > 0 else 0
        
        return {
            "overall_coverage": totals.get("percent_covered", 0),
            "critical_path_coverage": round(critical_coverage, 2),
            "total_lines": totals.get("num_statements", 0),
            "covered_lines": totals.get("covered_lines", 0),
            "missing_lines": totals.get("missing_lines", 0),
            "total_files": len(files),
            "fully_covered_files": sum(1 for f in files.values() if f.get("summary", {}).get("percent_covered", 0) == 100)
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive coverage report"""
        # Run coverage
        coverage_data = self.run_coverage()
        
        # Analyze gaps
        uncovered = self.analyze_uncovered_code(coverage_data)
        critical_gaps = self.identify_critical_gaps(uncovered)
        
        # Get test distribution
        test_distribution = self.analyze_test_distribution()
        
        # Generate recommendations
        recommendations = self.generate_test_recommendations(critical_gaps)
        
        # Calculate metrics
        metrics = self.calculate_metrics(coverage_data)
        
        # Generate report
        report = []
        report.append("# Coverage Gap Analysis Report\n")
        report.append(f"## Overall Metrics\n")
        
        if metrics:
            report.append(f"- **Overall Coverage**: {metrics['overall_coverage']:.2f}%")
            report.append(f"- **Critical Path Coverage**: {metrics['critical_path_coverage']:.2f}%")
            report.append(f"- **Lines Covered**: {metrics['covered_lines']}/{metrics['total_lines']}")
            report.append(f"- **Files Analyzed**: {metrics['total_files']}")
            report.append(f"- **Fully Covered Files**: {metrics['fully_covered_files']}")
        
        report.append(f"\n## Test Distribution\n")
        report.append(f"- **Unit Tests**: {test_distribution['unit']}")
        report.append(f"- **Integration Tests**: {test_distribution['integration']}")
        report.append(f"- **Agent Tests**: {test_distribution['agent']}")
        report.append(f"- **E2E Tests**: {test_distribution['e2e']}")
        
        report.append(f"\n## Critical Coverage Gaps\n")
        
        for file_path, gaps in list(critical_gaps.items())[:10]:  # Top 10 files
            report.append(f"\n### {Path(file_path).name}")
            report.append(f"**Uncovered Critical Lines**: {len(gaps)}\n")
            
            # Group by category
            by_category = {}
            for gap in gaps:
                cat = gap["category"]
                if cat not in by_category:
                    by_category[cat] = 0
                by_category[cat] += 1
            
            for cat, count in by_category.items():
                report.append(f"- {cat}: {count} lines")
        
        report.append(f"\n## Test Recommendations\n")
        
        for rec in recommendations:
            report.append(f"\n### {rec['category'].replace('_', ' ').title()}")
            report.append(f"**Priority**: {rec['priority']}")
            report.append(f"**Required Tests**: {rec['test_count']}")
            report.append(f"\n```python{rec['template']}```")
        
        report.append(f"\n## Action Items\n")
        
        # Determine action items based on metrics
        if metrics.get("overall_coverage", 0) < 85:
            report.append(f"1. ⚠️ Overall coverage ({metrics['overall_coverage']:.2f}%) is below target (85%)")
        
        if metrics.get("critical_path_coverage", 0) < 95:
            report.append(f"2. ⚠️ Critical path coverage ({metrics['critical_path_coverage']:.2f}%) is below target (95%)")
        
        if len(critical_gaps) > 0:
            report.append(f"3. Add tests for {len(critical_gaps)} files with critical gaps")
        
        if test_distribution["e2e"] < 50:
            report.append(f"4. Consider adding more E2E tests (current: {test_distribution['e2e']})")
        
        return "\n".join(report)


def main():
    """Main entry point"""
    analyzer = CoverageAnalyzer()
    report = analyzer.generate_report()
    
    # Save report
    report_path = Path("coverage_gap_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\nCoverage gap analysis complete!")
    print(f"Report saved to: {report_path}")
    print("\n" + "="*50)
    print(report)


if __name__ == "__main__":
    main()