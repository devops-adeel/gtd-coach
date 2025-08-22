#!/usr/bin/env python3
"""
Create Grafana dashboard for GTD Coach legacy code migration tracking.
This dashboard visualizes deprecation metrics, migration progress, and quality gates.
"""

import os
import json
import requests
from datetime import datetime

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://grafana.local:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")


def create_migration_dashboard():
    """Create comprehensive migration tracking dashboard"""
    
    dashboard = {
        "dashboard": {
            "uid": "gtd-migration",
            "title": "GTD Coach - Legacy Code Migration Tracker",
            "tags": ["gtd-coach", "migration", "deprecation", "observability"],
            "timezone": "browser",
            "schemaVersion": 30,
            "version": 0,
            "refresh": "10s",
            "time": {
                "from": "now-24h",
                "to": "now"
            },
            "annotations": {
                "list": [
                    {
                        "datasource": "Prometheus",
                        "enable": True,
                        "expr": "gtd_coach_deprecation_warnings_total > 0",
                        "name": "Deprecation Warnings",
                        "iconColor": "yellow",
                        "step": "1m"
                    }
                ]
            },
            "panels": [
                # Row 1: Overview Metrics
                {
                    "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
                    "id": 1,
                    "title": "Overall Migration Progress",
                    "type": "gauge",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": "avg(gtd_coach_migration_readiness)",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 50, "color": "yellow"},
                                    {"value": 80, "color": "green"}
                                ]
                            },
                            "max": 100,
                            "min": 0,
                            "unit": "percent"
                        }
                    },
                    "options": {
                        "showThresholdLabels": True,
                        "showThresholdMarkers": True
                    }
                },
                {
                    "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
                    "id": 2,
                    "title": "Days Until Removal",
                    "type": "stat",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": "min(gtd_coach_deprecation_days_until_removal)",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 30, "color": "orange"},
                                    {"value": 90, "color": "yellow"},
                                    {"value": 180, "color": "green"}
                                ]
                            },
                            "unit": "d",
                            "decimals": 0
                        }
                    },
                    "options": {
                        "graphMode": "area",
                        "colorMode": "value",
                        "justifyMode": "center"
                    }
                },
                {
                    "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
                    "id": 3,
                    "title": "Agent Adoption Rate",
                    "type": "stat",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": '''
                        sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[24h])) /
                        sum(rate(gtd_coach_legacy_usage_total[24h])) * 100
                        ''',
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 25, "color": "orange"},
                                    {"value": 50, "color": "yellow"},
                                    {"value": 75, "color": "light-green"},
                                    {"value": 95, "color": "green"}
                                ]
                            },
                            "unit": "percent",
                            "decimals": 1
                        }
                    },
                    "options": {
                        "graphMode": "area",
                        "colorMode": "value"
                    }
                },
                
                # Row 2: Usage Comparison
                {
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "id": 4,
                    "title": "Legacy vs Agent Usage (24h)",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": "Prometheus",
                            "expr": 'sum(rate(gtd_coach_legacy_usage_total{implementation="legacy"}[5m])) by (command)',
                            "legendFormat": "Legacy - {{command}}",
                            "refId": "A"
                        },
                        {
                            "datasource": "Prometheus",
                            "expr": 'sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[5m])) by (command)',
                            "legendFormat": "Agent - {{command}}",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "palette-classic"
                            },
                            "unit": "ops",
                            "custom": {
                                "axisLabel": "Invocations/sec",
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "gradientMode": "opacity",
                                "spanNulls": True,
                                "showPoints": "never",
                                "stacking": {
                                    "mode": "none"
                                }
                            }
                        }
                    }
                },
                {
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "id": 5,
                    "title": "Deprecation Warnings Shown",
                    "type": "timeseries",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": 'sum(rate(gtd_coach_deprecation_warnings_total[5m])) by (command)',
                        "legendFormat": "{{command}}",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "palette-classic"
                            },
                            "unit": "short",
                            "custom": {
                                "axisLabel": "Warnings/min",
                                "drawStyle": "bars",
                                "lineWidth": 2,
                                "fillOpacity": 50,
                                "gradientMode": "opacity"
                            }
                        }
                    }
                },
                
                # Row 3: Quality Metrics
                {
                    "gridPos": {"h": 8, "w": 8, "x": 0, "y": 16},
                    "id": 6,
                    "title": "Error Rate Comparison",
                    "type": "graph",
                    "targets": [
                        {
                            "datasource": "Prometheus",
                            "expr": '''
                            sum(rate(gtd_coach_migration_errors_total{implementation="legacy"}[5m])) by (command) /
                            sum(rate(gtd_coach_legacy_usage_total{implementation="legacy"}[5m])) by (command)
                            ''',
                            "legendFormat": "Legacy - {{command}}",
                            "refId": "A"
                        },
                        {
                            "datasource": "Prometheus",
                            "expr": '''
                            sum(rate(gtd_coach_migration_errors_total{implementation="agent"}[5m])) by (command) /
                            sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[5m])) by (command)
                            ''',
                            "legendFormat": "Agent - {{command}}",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "custom": {
                                "axisLabel": "Error Rate",
                                "drawStyle": "line",
                                "lineWidth": 2
                            }
                        }
                    },
                    "alert": {
                        "conditions": [{
                            "evaluator": {
                                "params": [0.01],
                                "type": "gt"
                            },
                            "query": {
                                "params": ["A", "5m", "now"]
                            },
                            "reducer": {
                                "params": [],
                                "type": "avg"
                            },
                            "type": "query"
                        }],
                        "alertRuleTags": {},
                        "frequency": "1m",
                        "handler": 1,
                        "name": "High Error Rate",
                        "noDataState": "no_data",
                        "notifications": []
                    }
                },
                {
                    "gridPos": {"h": 8, "w": 8, "x": 8, "y": 16},
                    "id": 7,
                    "title": "P95 Latency Comparison",
                    "type": "graph",
                    "targets": [
                        {
                            "datasource": "Prometheus",
                            "expr": '''
                            histogram_quantile(0.95, 
                                sum(rate(gtd_coach_command_duration_bucket{implementation="legacy"}[5m])) by (command, le)
                            )
                            ''',
                            "legendFormat": "Legacy - {{command}}",
                            "refId": "A"
                        },
                        {
                            "datasource": "Prometheus",
                            "expr": '''
                            histogram_quantile(0.95,
                                sum(rate(gtd_coach_command_duration_bucket{implementation="agent"}[5m])) by (command, le)
                            )
                            ''',
                            "legendFormat": "Agent - {{command}}",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms",
                            "custom": {
                                "axisLabel": "P95 Latency",
                                "drawStyle": "line",
                                "lineWidth": 2
                            }
                        }
                    }
                },
                {
                    "gridPos": {"h": 8, "w": 8, "x": 16, "y": 16},
                    "id": 8,
                    "title": "Quality Score",
                    "type": "heatmap",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": 'gtd_coach_quality_score_bucket',
                        "format": "heatmap",
                        "refId": "A"
                    }],
                    "options": {
                        "calculate": False,
                        "cellGap": 1,
                        "cellRadius": 1,
                        "color": {
                            "scheme": "RdYlGn",
                            "steps": 256,
                            "reverse": False,
                            "min": 0,
                            "max": 100
                        }
                    }
                },
                
                # Row 4: Command Status Table
                {
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 24},
                    "id": 9,
                    "title": "Command Migration Status",
                    "type": "table",
                    "targets": [{
                        "datasource": "Prometheus",
                        "expr": '''
                        sum by (command) (
                            increase(gtd_coach_legacy_usage_total[24h])
                        )
                        ''',
                        "format": "table",
                        "instant": True,
                        "refId": "A"
                    }],
                    "transformations": [
                        {
                            "id": "merge",
                            "options": {}
                        },
                        {
                            "id": "organize",
                            "options": {
                                "excludeByName": {},
                                "indexByName": {},
                                "renameByName": {
                                    "command": "Command",
                                    "Value": "24h Usage"
                                }
                            }
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "align": "auto",
                                "displayMode": "auto"
                            }
                        },
                        "overrides": [
                            {
                                "matcher": {
                                    "id": "byName",
                                    "options": "24h Usage"
                                },
                                "properties": [{
                                    "id": "custom.displayMode",
                                    "value": "color-background"
                                }]
                            }
                        ]
                    }
                },
                
                # Row 5: Traces Integration
                {
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 32},
                    "id": 10,
                    "title": "Recent Migration Traces",
                    "type": "traces",
                    "datasource": "Tempo",
                    "targets": [{
                        "datasource": "Tempo",
                        "query": '{service.name="gtd-coach" && span.kind="server"}',
                        "refId": "A"
                    }]
                }
            ]
        },
        "overwrite": True,
        "message": "Updated GTD Coach migration dashboard"
    }
    
    # Send request to Grafana API
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{GRAFANA_URL}/api/dashboards/db",
        headers=headers,
        json=dashboard
    )
    
    if response.status_code == 200:
        result = response.json()
        dashboard_url = f"{GRAFANA_URL}{result['url']}"
        print(f"✅ Dashboard created successfully!")
        print(f"   View at: {dashboard_url}")
        print(f"   UID: {result['uid']}")
        print(f"   Version: {result['version']}")
        return result
    else:
        print(f"❌ Failed to create dashboard")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def main():
    """Main entry point"""
    print("🚀 Setting up GTD Coach Migration Dashboard in Grafana")
    print(f"   Grafana URL: {GRAFANA_URL}")
    print(f"   API Key: {GRAFANA_API_KEY[:20]}...")
    print()
    
    result = create_migration_dashboard()
    
    if result:
        print("\n📊 Dashboard Features:")
        print("   • Overall migration progress gauge")
        print("   • Days until removal countdown")
        print("   • Agent adoption rate tracking")
        print("   • Legacy vs Agent usage comparison")
        print("   • Error rate and latency metrics")
        print("   • Quality score heatmap")
        print("   • Command migration status table")
        print("   • Integration with Tempo traces")
        print("\n✨ Migration tracking is now live!")
    else:
        print("\n❌ Dashboard creation failed. Please check:")
        print("   1. Grafana is accessible at", GRAFANA_URL)
        print("   2. API key has dashboard creation permissions")
        print("   3. Prometheus and Tempo datasources are configured")


if __name__ == "__main__":
    main()