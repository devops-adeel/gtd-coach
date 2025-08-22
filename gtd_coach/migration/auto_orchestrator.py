#!/usr/bin/env python3
"""
Automated Migration Orchestrator for GTD Coach.
Simplified for single-user deployment - manages personal migration from legacy to agent.
"""

import os
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://grafana.local:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus.local:9090")


class SingleUserMigrationOrchestrator:
    """
    Orchestrates the migration from legacy to agent implementations.
    Optimized for single-user (adeel) deployment.
    """
    
    def __init__(self):
        self.grafana_api_key = GRAFANA_API_KEY
        self.grafana_url = GRAFANA_URL
        self.prometheus_url = PROMETHEUS_URL
        
        # Commands to migrate
        self.commands = [
            "daily_clarify",
            "daily_capture",
            "daily_alignment"
        ]
        
        # File mappings for deletion
        self.legacy_files = {
            "daily_clarify": [
                "gtd_coach/commands/daily_clarify.py"
            ],
            "daily_capture": [
                "gtd_coach/commands/daily_capture_legacy.py"
            ],
            "daily_alignment": [
                "gtd_coach/commands/daily_alignment.py"
            ],
            "parallel_runner": [
                "gtd_coach/bridge/parallel_runner.py"
            ]
        }
        
        # Archive directory
        self.archive_dir = Path.home() / ".gtd_coach" / "legacy_archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    async def check_current_status(self) -> Dict:
        """Check current migration status for all commands"""
        
        status = {}
        for command in self.commands:
            metrics = await self.get_command_metrics(command)
            status[command] = {
                "legacy_usage_24h": metrics.get("legacy_usage_24h", 0),
                "agent_usage_24h": metrics.get("agent_usage_24h", 0),
                "last_legacy_use": metrics.get("last_legacy_use"),
                "adoption_rate": metrics.get("adoption_rate", 0),
                "ready_for_deletion": metrics.get("legacy_usage_30d", 0) == 0,
                "quality_score": await self.calculate_quality_score(command)
            }
        
        return status
    
    async def get_command_metrics(self, command: str) -> Dict:
        """Query Prometheus for command-specific metrics"""
        
        queries = {
            "legacy_usage_24h": f'''
                sum(increase(gtd_coach_legacy_usage_total{{
                    command="{command}",
                    implementation="legacy"
                }}[24h]))
            ''',
            "agent_usage_24h": f'''
                sum(increase(gtd_coach_legacy_usage_total{{
                    command="{command}",
                    implementation="agent"
                }}[24h]))
            ''',
            "legacy_usage_30d": f'''
                sum(increase(gtd_coach_legacy_usage_total{{
                    command="{command}",
                    implementation="legacy"
                }}[30d]))
            ''',
            "adoption_rate": f'''
                sum(rate(gtd_coach_legacy_usage_total{{
                    command="{command}",
                    implementation="agent"
                }}[7d])) /
                sum(rate(gtd_coach_legacy_usage_total{{
                    command="{command}"
                }}[7d]))
            ''',
            "error_rate": f'''
                sum(rate(gtd_coach_migration_errors_total{{
                    command="{command}"
                }}[24h])) /
                sum(rate(gtd_coach_legacy_usage_total{{
                    command="{command}"
                }}[24h]))
            ''',
            "p95_latency": f'''
                histogram_quantile(0.95,
                    sum(rate(gtd_coach_command_duration_bucket{{
                        command="{command}"
                    }}[5m])) by (le)
                )
            '''
        }
        
        results = {}
        for metric_name, query in queries.items():
            try:
                value = await self._query_prometheus(query)
                results[metric_name] = float(value) if value else 0
            except Exception as e:
                logger.warning(f"Failed to query {metric_name}: {e}")
                results[metric_name] = 0
        
        return results
    
    async def _query_prometheus(self, query: str) -> Optional[float]:
        """Execute Prometheus query via HTTP API"""
        
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["data"]["result"]:
                    return float(data["data"]["result"][0]["value"][1])
            return None
            
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return None
    
    async def calculate_quality_score(self, command: str) -> float:
        """Calculate quality score for migration readiness"""
        
        metrics = await self.get_command_metrics(command)
        
        # Single user = simpler scoring
        score = 100.0
        
        # Deduct for errors
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 0.01:  # >1% errors
            score -= 30
        elif error_rate > 0.005:  # >0.5% errors
            score -= 15
        
        # Deduct for slow performance
        latency = metrics.get("p95_latency", 0)
        if latency > 2000:  # >2s
            score -= 20
        elif latency > 1000:  # >1s
            score -= 10
        
        # Boost for adoption
        adoption = metrics.get("adoption_rate", 0)
        score += adoption * 20  # Up to +20 for 100% adoption
        
        return max(0, min(100, score))
    
    async def suggest_next_action(self) -> str:
        """Suggest the next migration action based on current status"""
        
        status = await self.check_current_status()
        
        suggestions = []
        
        for command, metrics in status.items():
            if metrics["ready_for_deletion"]:
                suggestions.append(f"✅ {command}: Ready to delete (no usage in 30 days)")
                
            elif metrics["adoption_rate"] >= 0.95:
                suggestions.append(f"🎯 {command}: 95% migrated - consider forcing agent-only")
                
            elif metrics["adoption_rate"] >= 0.5:
                suggestions.append(f"📈 {command}: {metrics['adoption_rate']*100:.0f}% migrated - keep using agent")
                
            elif metrics["legacy_usage_24h"] > 0:
                suggestions.append(f"⚠️ {command}: Still using legacy - switch to agent")
                
            else:
                suggestions.append(f"💤 {command}: No recent usage")
        
        return "\n".join(suggestions)
    
    async def archive_legacy_code(self, command: str) -> bool:
        """Archive legacy code before deletion"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_subdir = self.archive_dir / f"{command}_{timestamp}"
        archive_subdir.mkdir(parents=True, exist_ok=True)
        
        files = self.legacy_files.get(command, [])
        archived = []
        
        for file_path in files:
            source = Path(file_path)
            if source.exists():
                dest = archive_subdir / source.name
                shutil.copy2(source, dest)
                archived.append(str(dest))
                logger.info(f"Archived {source} to {dest}")
        
        # Create manifest
        manifest = {
            "command": command,
            "archived_at": datetime.now().isoformat(),
            "files": archived,
            "reason": "Zero usage for 30+ days"
        }
        
        manifest_file = archive_subdir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Created archive manifest: {manifest_file}")
        return len(archived) > 0
    
    async def delete_legacy_command(self, command: str, force: bool = False) -> bool:
        """Delete legacy command files after safety checks"""
        
        # Safety checks
        if not force:
            metrics = await self.get_command_metrics(command)
            
            if metrics["legacy_usage_30d"] > 0:
                logger.error(f"Cannot delete {command}: Still has usage in last 30 days")
                return False
            
            if metrics["adoption_rate"] < 0.95:
                logger.warning(f"Warning: {command} adoption only {metrics['adoption_rate']*100:.0f}%")
                response = input("Continue with deletion? (y/n): ")
                if response.lower() != 'y':
                    return False
        
        # Archive first
        if not await self.archive_legacy_code(command):
            logger.error(f"Failed to archive {command}")
            return False
        
        # Delete files
        files = self.legacy_files.get(command, [])
        deleted = []
        
        for file_path in files:
            source = Path(file_path)
            if source.exists():
                source.unlink()
                deleted.append(file_path)
                logger.info(f"Deleted {file_path}")
        
        # Update migration adapters to remove legacy option
        await self.update_migration_adapter(command, remove_legacy=True)
        
        # Log to Grafana annotation
        await self.add_grafana_annotation(
            f"Deleted legacy {command}",
            f"Removed {len(deleted)} files after 30 days of zero usage"
        )
        
        return len(deleted) > 0
    
    async def update_migration_adapter(self, command: str, remove_legacy: bool = False):
        """Update migration adapter to reflect deletion"""
        
        adapter_file = Path(f"gtd_coach/migration/{command}_adapter.py")
        
        if adapter_file.exists():
            # For single user, just update to always use agent
            content = adapter_file.read_text()
            
            if remove_legacy:
                # Replace logic to always return agent implementation
                new_content = content.replace(
                    'use_legacy = os.getenv("USE_LEGACY_',
                    'use_legacy = False  # Legacy removed - '
                )
                adapter_file.write_text(new_content)
                logger.info(f"Updated {adapter_file} to disable legacy")
    
    async def add_grafana_annotation(self, title: str, text: str):
        """Add annotation to Grafana dashboard"""
        
        annotation = {
            "dashboardUID": "gtd-migration",
            "time": int(datetime.now().timestamp() * 1000),
            "tags": ["migration", "automated"],
            "text": text,
            "title": title
        }
        
        response = requests.post(
            f"{self.grafana_url}/api/annotations",
            headers={
                "Authorization": f"Bearer {self.grafana_api_key}",
                "Content-Type": "application/json"
            },
            json=annotation
        )
        
        if response.status_code == 200:
            logger.info(f"Added Grafana annotation: {title}")
        else:
            logger.warning(f"Failed to add annotation: {response.text}")
    
    async def run_migration_check(self) -> Dict:
        """Run a complete migration check and return recommendations"""
        
        print("\n🔍 GTD Coach Migration Status Check")
        print("=" * 50)
        
        status = await self.check_current_status()
        
        # Summary statistics
        total_legacy = sum(s["legacy_usage_24h"] for s in status.values())
        total_agent = sum(s["agent_usage_24h"] for s in status.values())
        overall_adoption = total_agent / (total_legacy + total_agent) if (total_legacy + total_agent) > 0 else 0
        
        print(f"\n📊 Overall Statistics (24h):")
        print(f"   Legacy invocations: {total_legacy:.0f}")
        print(f"   Agent invocations: {total_agent:.0f}")
        print(f"   Adoption rate: {overall_adoption*100:.1f}%")
        
        # Command-specific status
        print(f"\n📋 Command Status:")
        for command, metrics in status.items():
            status_emoji = "✅" if metrics["ready_for_deletion"] else "🔄" if metrics["adoption_rate"] > 0.5 else "⚠️"
            print(f"\n   {status_emoji} {command}:")
            print(f"      Legacy (24h): {metrics['legacy_usage_24h']:.0f}")
            print(f"      Agent (24h): {metrics['agent_usage_24h']:.0f}")
            print(f"      Adoption: {metrics['adoption_rate']*100:.1f}%")
            print(f"      Quality: {metrics['quality_score']:.0f}/100")
            print(f"      Ready to delete: {'Yes' if metrics['ready_for_deletion'] else 'No'}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        suggestions = await self.suggest_next_action()
        print(suggestions)
        
        # Next milestone
        if overall_adoption < 0.5:
            print(f"\n🎯 Next milestone: Reach 50% adoption (currently {overall_adoption*100:.1f}%)")
        elif overall_adoption < 0.95:
            print(f"\n🎯 Next milestone: Reach 95% adoption (currently {overall_adoption*100:.1f}%)")
        else:
            print(f"\n🎉 Ready for complete migration! Consider deleting legacy code.")
        
        return status


async def main():
    """Main entry point for testing"""
    orchestrator = SingleUserMigrationOrchestrator()
    
    # Run migration check
    await orchestrator.run_migration_check()
    
    # Check for commands ready to delete
    status = await orchestrator.check_current_status()
    deletable = [cmd for cmd, metrics in status.items() if metrics["ready_for_deletion"]]
    
    if deletable:
        print(f"\n🗑️ Commands ready for deletion: {', '.join(deletable)}")
        response = input("Delete legacy code for these commands? (y/n): ")
        
        if response.lower() == 'y':
            for command in deletable:
                success = await orchestrator.delete_legacy_command(command)
                if success:
                    print(f"✅ Deleted legacy code for {command}")
                else:
                    print(f"❌ Failed to delete {command}")


if __name__ == "__main__":
    asyncio.run(main())