#!/usr/bin/env python3
"""
Migration Adapter for Daily Clarify Command
Provides gradual transition from legacy to agent-based implementation
"""

import os
import sys
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ClarifyMigrationAdapter:
    """
    Bridge between legacy daily_clarify.py and new agent workflow.
    Allows gradual migration with feature flags and telemetry.
    """
    
    # Deprecation date - 2 weeks from now
    DEPRECATION_DATE = datetime(2025, 2, 15)
    
    def __init__(self):
        """Initialize adapter with both implementations"""
        self.legacy = None  # Lazy load
        self.agent = None   # Lazy load
        
        # Track usage for telemetry
        self.usage_file = Path.home() / ".gtd_coach" / "migration_metrics.json"
        self.usage_file.parent.mkdir(exist_ok=True)
    
    def _load_legacy(self):
        """Lazy load legacy implementation"""
        if self.legacy is None:
            try:
                from gtd_coach.commands.daily_clarify import DailyClarify
                self.legacy = DailyClarify()
            except ImportError as e:
                logger.error(f"Failed to import legacy clarify: {e}")
                raise RuntimeError(
                    "Legacy clarify implementation not available. "
                    "Use agent implementation instead."
                )
        return self.legacy
    
    def _load_agent(self):
        """Lazy load agent implementation"""
        if self.agent is None:
            from gtd_coach.agent.workflows.daily_clarify import DailyClarifyWorkflow
            self.agent = DailyClarifyWorkflow()
        return self.agent
    
    def _log_usage(self, implementation: str):
        """Log usage metrics for migration tracking"""
        try:
            import json
            
            # Load existing metrics
            if self.usage_file.exists():
                with open(self.usage_file, 'r') as f:
                    metrics = json.load(f)
            else:
                metrics = {"legacy": [], "agent": []}
            
            # Add current usage
            metrics[implementation].append({
                "timestamp": datetime.now().isoformat(),
                "user": os.getenv("USER", "unknown")
            })
            
            # Keep only last 100 entries per implementation
            metrics[implementation] = metrics[implementation][-100:]
            
            # Save metrics
            with open(self.usage_file, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Failed to log usage metrics: {e}")
    
    def _show_deprecation_warning(self):
        """Show deprecation warning for legacy usage"""
        days_until = (self.DEPRECATION_DATE - datetime.now()).days
        
        warning_msg = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️  DEPRECATION WARNING                    ║
╠══════════════════════════════════════════════════════════════╣
║ The legacy clarify command is deprecated and will be         ║
║ removed on {self.DEPRECATION_DATE.strftime('%Y-%m-%d')}.                                   ║
║                                                              ║
║ Days remaining: {days_until:2d}                                        ║
║                                                              ║
║ To use the new agent-based implementation:                  ║
║   unset USE_LEGACY_CLARIFY                                  ║
║                                                              ║
║ To suppress this warning (not recommended):                 ║
║   export SUPPRESS_DEPRECATION_WARNING=true                  ║
╚══════════════════════════════════════════════════════════════╝
"""
        
        if not os.getenv("SUPPRESS_DEPRECATION_WARNING"):
            print(warning_msg)
            
        # Also use Python warnings
        warnings.warn(
            f"Legacy clarify command deprecated. Will be removed on {self.DEPRECATION_DATE}. "
            f"Migrate to agent-based implementation.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _show_migration_benefits(self):
        """Show benefits of migrating to agent workflow"""
        print("""
✨ New Agent-Based Clarify Benefits:
  • Better interrupt handling (no state pollution)
  • Automatic checkpointing (resume after interruption)
  • Integration with agent memory system
  • Improved error recovery
  • Consistent with other GTD workflows
  
Try it now: gtd-coach clarify (without USE_LEGACY_CLARIFY)
""")
    
    def run(self, use_legacy: Optional[bool] = None, show_comparison: bool = False):
        """
        Run clarify workflow with appropriate implementation.
        
        Args:
            use_legacy: Force legacy implementation (overrides env var)
            show_comparison: Run both and show comparison (for testing)
        
        Returns:
            Metrics dictionary from the chosen implementation
        """
        # Determine which implementation to use
        if use_legacy is None:
            use_legacy = os.getenv("USE_LEGACY_CLARIFY", "false").lower() == "true"
        
        # Check if past deprecation date
        if datetime.now() > self.DEPRECATION_DATE and use_legacy:
            print("\n❌ Legacy clarify has been removed. Using agent implementation.\n")
            use_legacy = False
        
        # Show comparison mode (for testing/evaluation)
        if show_comparison:
            return self._run_comparison()
        
        # Run appropriate implementation
        if use_legacy:
            logger.info("Running legacy clarify implementation")
            self._show_deprecation_warning()
            self._log_usage("legacy")
            
            # Run legacy
            legacy_impl = self._load_legacy()
            legacy_impl.run()
            
            # Show migration benefits
            self._show_migration_benefits()
            
            return legacy_impl.metrics
            
        else:
            logger.info("Running agent-based clarify implementation")
            self._log_usage("agent")
            
            # Run agent workflow
            agent_impl = self._load_agent()
            result = agent_impl.run()
            
            # Extract metrics from agent state
            return {
                "inbox_count": len(result.get("inbox_tasks", [])),
                "processed": result.get("processed_count", 0),
                "deleted": result.get("deleted_count", 0),
                "deep_work": result.get("deep_work_count", 0),
                "quick_tasks": result.get("quick_task_count", 0)
            }
    
    def _run_comparison(self) -> Dict:
        """
        Run both implementations and show comparison.
        Useful for testing and validation during migration.
        """
        print("\n🔬 COMPARISON MODE - Running both implementations\n")
        print("=" * 60)
        
        # Run legacy
        print("\n1️⃣  LEGACY IMPLEMENTATION")
        print("-" * 30)
        legacy_impl = self._load_legacy()
        legacy_impl.run()
        legacy_metrics = legacy_impl.metrics
        
        print("\n" + "=" * 60)
        
        # Run agent
        print("\n2️⃣  AGENT IMPLEMENTATION")
        print("-" * 30)
        agent_impl = self._load_agent()
        agent_result = agent_impl.run()
        
        agent_metrics = {
            "inbox_count": len(agent_result.get("inbox_tasks", [])),
            "processed": agent_result.get("processed_count", 0),
            "deleted": agent_result.get("deleted_count", 0),
            "deep_work": agent_result.get("deep_work_count", 0),
            "quick_tasks": agent_result.get("quick_task_count", 0)
        }
        
        # Show comparison
        print("\n" + "=" * 60)
        print("📊 COMPARISON RESULTS")
        print("=" * 60)
        
        print(f"\n{'Metric':<20} {'Legacy':>10} {'Agent':>10} {'Match':>10}")
        print("-" * 50)
        
        for key in legacy_metrics:
            if key in agent_metrics:
                legacy_val = legacy_metrics[key]
                agent_val = agent_metrics[key]
                match = "✅" if legacy_val == agent_val else "❌"
                print(f"{key:<20} {legacy_val:>10} {agent_val:>10} {match:>10}")
        
        print("\n" + "=" * 60)
        
        return agent_metrics
    
    def get_migration_status(self) -> Dict:
        """
        Get current migration status and usage metrics.
        
        Returns:
            Dictionary with migration status information
        """
        try:
            import json
            
            # Load usage metrics
            if self.usage_file.exists():
                with open(self.usage_file, 'r') as f:
                    metrics = json.load(f)
            else:
                metrics = {"legacy": [], "agent": []}
            
            # Calculate usage in last 7 days
            week_ago = datetime.now() - timedelta(days=7)
            
            legacy_recent = sum(
                1 for entry in metrics.get("legacy", [])
                if datetime.fromisoformat(entry["timestamp"]) > week_ago
            )
            
            agent_recent = sum(
                1 for entry in metrics.get("agent", [])
                if datetime.fromisoformat(entry["timestamp"]) > week_ago
            )
            
            days_until_deprecation = (self.DEPRECATION_DATE - datetime.now()).days
            
            return {
                "deprecation_date": self.DEPRECATION_DATE.isoformat(),
                "days_until_deprecation": max(0, days_until_deprecation),
                "legacy_usage_last_week": legacy_recent,
                "agent_usage_last_week": agent_recent,
                "migration_progress": (agent_recent / max(1, legacy_recent + agent_recent)) * 100
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                "error": str(e),
                "deprecation_date": self.DEPRECATION_DATE.isoformat()
            }


def main():
    """Standalone entry point for testing adapter"""
    import argparse
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(description="Clarify Migration Adapter")
    parser.add_argument("--legacy", action="store_true", 
                       help="Force use of legacy implementation")
    parser.add_argument("--compare", action="store_true",
                       help="Run both implementations and compare")
    parser.add_argument("--status", action="store_true",
                       help="Show migration status")
    args = parser.parse_args()
    
    load_dotenv()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    adapter = ClarifyMigrationAdapter()
    
    if args.status:
        status = adapter.get_migration_status()
        print("\n📊 Migration Status")
        print("=" * 40)
        for key, value in status.items():
            print(f"{key}: {value}")
    else:
        adapter.run(use_legacy=args.legacy, show_comparison=args.compare)


if __name__ == "__main__":
    main()