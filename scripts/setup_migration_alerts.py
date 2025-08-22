#!/usr/bin/env python3
"""
Setup Grafana alerts for GTD Coach migration tracking.
Simplified for single-user deployment - focused on personal migration progress.
"""

import os
import json
import requests
from datetime import datetime

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://grafana.local:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")


def create_migration_alerts():
    """Create alerts for personal migration tracking"""
    
    # Since you're the only user, these alerts focus on your migration progress
    alerts = [
        {
            "uid": "still-using-legacy",
            "title": "Still Using Legacy Commands",
            "folderUID": "gtd-coach",
            "interval": "5m",
            "rules": [{
                "uid": "legacy-usage-alert",
                "title": "Legacy Command Used Today",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 86400,  # 24 hours
                        "to": 0
                    },
                    "datasourceUid": "prometheus",
                    "model": {
                        "expr": '''sum(increase(gtd_coach_legacy_usage_total{implementation="legacy"}[24h])) > 0''',
                        "interval": "5m",
                        "refId": "A"
                    }
                }],
                "noDataState": "OK",
                "execErrState": "Alerting",
                "for": "5m",
                "annotations": {
                    "summary": "You're still using legacy commands. Time to switch to agent workflows!",
                    "description": '''
                    Legacy usage detected in the last 24 hours.
                    Consider switching to agent implementations:
                    - unset USE_LEGACY_DAILY_CLARIFY
                    - unset USE_LEGACY_DAILY_CAPTURE
                    - unset USE_LEGACY_DAILY_ALIGNMENT
                    ''',
                    "runbook_url": "http://grafana.local:3000/d/gtd-migration"
                },
                "labels": {
                    "severity": "info",
                    "component": "migration"
                }
            }]
        },
        {
            "uid": "high-error-rate",
            "title": "Quality Gate - Error Rate",
            "folderUID": "gtd-coach",
            "interval": "1m",
            "rules": [{
                "uid": "error-rate-alert",
                "title": "Agent Implementation Error Rate High",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 600,  # 10 minutes
                        "to": 0
                    },
                    "datasourceUid": "prometheus",
                    "model": {
                        "expr": '''
                        (sum(rate(gtd_coach_migration_errors_total{implementation="agent"}[5m])) /
                         sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[5m]))) > 0.01
                        ''',
                        "interval": "1m",
                        "refId": "A"
                    }
                }],
                "noDataState": "OK",
                "execErrState": "Alerting",
                "for": "3m",
                "annotations": {
                    "summary": "Agent error rate > 1% - Check implementation",
                    "description": "The agent implementation is experiencing higher error rates. Consider reverting to legacy temporarily.",
                    "runbook_url": "http://grafana.local:3000/d/gtd-migration"
                },
                "labels": {
                    "severity": "warning",
                    "component": "quality"
                }
            }]
        },
        {
            "uid": "ready-for-deletion",
            "title": "Ready for Deletion",
            "folderUID": "gtd-coach",
            "interval": "1h",
            "rules": [{
                "uid": "zero-usage-30d",
                "title": "Legacy Code Ready for Deletion",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 2592000,  # 30 days
                        "to": 0
                    },
                    "datasourceUid": "prometheus",
                    "model": {
                        "expr": '''sum(increase(gtd_coach_legacy_usage_total{implementation="legacy"}[30d])) == 0''',
                        "interval": "1h",
                        "refId": "A"
                    }
                }],
                "noDataState": "OK",
                "execErrState": "OK",
                "for": "24h",
                "annotations": {
                    "summary": "🎉 Legacy code unused for 30 days - Safe to delete!",
                    "description": '''
                    No legacy usage detected in 30 days. You can now safely:
                    1. Run: python scripts/safe_delete_legacy.py
                    2. Remove legacy command files
                    3. Clean up migration adapters
                    ''',
                    "runbook_url": "http://grafana.local:3000/d/gtd-migration"
                },
                "labels": {
                    "severity": "info",
                    "component": "deletion"
                }
            }]
        },
        {
            "uid": "migration-milestone",
            "title": "Migration Milestones",
            "folderUID": "gtd-coach",
            "interval": "1h",
            "rules": [
                {
                    "uid": "50-percent-migrated",
                    "title": "50% Migrated to Agent",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "datasourceUid": "prometheus",
                        "model": {
                            "expr": '''
                            (sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[24h])) /
                             sum(rate(gtd_coach_legacy_usage_total[24h]))) >= 0.5
                            ''',
                            "interval": "1h",
                            "refId": "A"
                        }
                    }],
                    "for": "1h",
                    "annotations": {
                        "summary": "🎯 Milestone: 50% of usage is now on agent implementation!",
                        "description": "You're halfway through the migration. Keep going!"
                    },
                    "labels": {
                        "severity": "info",
                        "milestone": "50%"
                    }
                },
                {
                    "uid": "95-percent-migrated",
                    "title": "95% Migrated to Agent",
                    "condition": "A",
                    "data": [{
                        "refId": "A",
                        "datasourceUid": "prometheus",
                        "model": {
                            "expr": '''
                            (sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[24h])) /
                             sum(rate(gtd_coach_legacy_usage_total[24h]))) >= 0.95
                            ''',
                            "interval": "1h",
                            "refId": "A"
                        }
                    }],
                    "for": "1h",
                    "annotations": {
                        "summary": "🚀 Milestone: 95% migrated! Almost done!",
                        "description": "Only 5% of usage remains on legacy. Consider full switch."
                    },
                    "labels": {
                        "severity": "info",
                        "milestone": "95%"
                    }
                }
            ]
        },
        {
            "uid": "performance-regression",
            "title": "Performance Regression",
            "folderUID": "gtd-coach",
            "interval": "5m",
            "rules": [{
                "uid": "latency-regression",
                "title": "Agent Slower Than Legacy",
                "condition": "A",
                "data": [{
                    "refId": "A",
                    "datasourceUid": "prometheus",
                    "model": {
                        "expr": '''
                        (histogram_quantile(0.95, sum(rate(gtd_coach_command_duration_bucket{implementation="agent"}[5m])) by (le)) /
                         histogram_quantile(0.95, sum(rate(gtd_coach_command_duration_bucket{implementation="legacy"}[5m])) by (le))) > 1.5
                        ''',
                        "interval": "5m",
                        "refId": "A"
                    }
                }],
                "for": "10m",
                "annotations": {
                    "summary": "⚠️ Agent implementation 50% slower than legacy",
                    "description": "Performance regression detected. Check agent workflow efficiency."
                },
                "labels": {
                    "severity": "warning",
                    "component": "performance"
                }
            }]
        }
    ]
    
    # Create alert folder first
    folder_response = requests.post(
        f"{GRAFANA_URL}/api/folders",
        headers={
            "Authorization": f"Bearer {GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "uid": "gtd-coach",
            "title": "GTD Coach"
        }
    )
    
    if folder_response.status_code not in [200, 409]:  # 409 = already exists
        print(f"⚠️ Could not create folder: {folder_response.text}")
    
    # Create each alert rule group
    created_alerts = []
    failed_alerts = []
    
    for alert_group in alerts:
        response = requests.post(
            f"{GRAFANA_URL}/api/v1/provisioning/alert-rules",
            headers={
                "Authorization": f"Bearer {GRAFANA_API_KEY}",
                "Content-Type": "application/json"
            },
            json=alert_group
        )
        
        if response.status_code in [201, 202]:
            created_alerts.append(alert_group["title"])
            print(f"✅ Created alert: {alert_group['title']}")
        else:
            failed_alerts.append(alert_group["title"])
            print(f"❌ Failed to create alert: {alert_group['title']}")
            print(f"   Error: {response.text}")
    
    return created_alerts, failed_alerts


def create_notification_policy():
    """Create notification policy for personal alerts"""
    
    # For single user, simple notification to default contact point
    policy = {
        "receiver": "default",
        "group_by": ["alertname", "severity"],
        "group_interval": "5m",
        "group_wait": "10s",
        "repeat_interval": "4h",
        "routes": [
            {
                "receiver": "migration-notifications",
                "matchers": [
                    "component=migration"
                ],
                "group_interval": "1h",
                "repeat_interval": "24h"
            },
            {
                "receiver": "quality-notifications", 
                "matchers": [
                    "severity=warning"
                ],
                "group_interval": "5m",
                "repeat_interval": "1h"
            }
        ]
    }
    
    response = requests.put(
        f"{GRAFANA_URL}/api/v1/provisioning/policies",
        headers={
            "Authorization": f"Bearer {GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        },
        json=policy
    )
    
    if response.status_code in [202, 204]:
        print("✅ Notification policy configured")
        return True
    else:
        print(f"❌ Failed to configure notification policy: {response.text}")
        return False


def main():
    """Main entry point"""
    print("🚨 Setting up GTD Coach Migration Alerts")
    print(f"   Grafana URL: {GRAFANA_URL}")
    print(f"   For user: adeel (single-user mode)")
    print()
    
    # Create alerts
    created, failed = create_migration_alerts()
    
    print(f"\n📊 Alert Summary:")
    print(f"   ✅ Created: {len(created)} alerts")
    if created:
        for alert in created:
            print(f"      • {alert}")
    
    if failed:
        print(f"   ❌ Failed: {len(failed)} alerts")
        for alert in failed:
            print(f"      • {alert}")
    
    # Configure notifications
    print("\n📬 Configuring notifications...")
    create_notification_policy()
    
    print("\n✨ Alert Configuration Complete!")
    print("\n📋 Alerts will track:")
    print("   • Daily legacy usage (reminder to switch)")
    print("   • Error rate increases (quality gate)")
    print("   • 30-day zero usage (safe to delete)")
    print("   • Migration milestones (50%, 95%)")
    print("   • Performance regressions")
    print("\n💡 Since you're the only user:")
    print("   • No multi-user tracking needed")
    print("   • Alerts focus on your personal migration progress")
    print("   • Simplified thresholds for single-user patterns")


if __name__ == "__main__":
    main()