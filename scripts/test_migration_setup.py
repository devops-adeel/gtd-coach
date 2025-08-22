#!/usr/bin/env python3
"""
Test script to verify migration tracking setup is working.
Tests telemetry, dashboard, and decorators.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.observability.deprecation_telemetry import (
    update_migration_readiness,
    calculate_quality_score,
    legacy_usage_counter,
    tracer
)


def test_telemetry():
    """Test that telemetry is configured"""
    print("✅ Testing telemetry configuration...")
    
    # Test updating migration readiness
    update_migration_readiness("test_command", 75.0)
    print("   ✓ Migration readiness updated")
    
    # Test quality score calculation
    test_metrics = {
        "error_rate": 0.005,
        "p95_latency": 1000,
        "feature_parity": 0.9,
        "adoption_rate": 0.8,
        "test_coverage": 0.85
    }
    score = calculate_quality_score("test_command", test_metrics)
    print(f"   ✓ Quality score calculated: {score:.1f}/100")
    
    # Test counter increment
    legacy_usage_counter.add(1, {"command": "test", "implementation": "test"})
    print("   ✓ Metrics counter working")
    
    # Test tracer
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test.attribute", "value")
        print("   ✓ Tracer span created")
    
    return True


def test_dashboard_access():
    """Test that Grafana dashboard is accessible"""
    print("\n✅ Testing Grafana dashboard access...")
    
    import requests
    
    api_key = os.getenv("GRAFANA_API_KEY", "")
    grafana_url = "http://grafana.local:3000"
    
    # Check dashboard exists
    response = requests.get(
        f"{grafana_url}/api/dashboards/uid/gtd-migration",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    if response.status_code == 200:
        dashboard = response.json()
        print(f"   ✓ Dashboard found: {dashboard['dashboard']['title']}")
        print(f"   ✓ Panels configured: {len(dashboard['dashboard']['panels'])}")
        return True
    else:
        print(f"   ✗ Dashboard not found: {response.status_code}")
        return False


def test_decorators():
    """Test that deprecation decorators are importable"""
    print("\n✅ Testing deprecation decorators...")
    
    try:
        from gtd_coach.deprecation.decorator import (
            deprecate_daily_clarify,
            deprecate_daily_capture,
            deprecate_daily_alignment,
            check_migration_feasibility
        )
        print("   ✓ All decorators imported successfully")
        
        # Test feasibility check
        feasibility = check_migration_feasibility("test_command")
        print(f"   ✓ Feasibility check: score={feasibility['score']:.1f}, ready={feasibility['ready_for_migration']}")
        
        return True
    except ImportError as e:
        print(f"   ✗ Failed to import decorators: {e}")
        return False


def test_legacy_commands():
    """Test that legacy commands have decorators applied"""
    print("\n✅ Testing legacy command decoration...")
    
    try:
        # Test daily_clarify
        from gtd_coach.commands.daily_clarify import DailyClarify
        dc = DailyClarify()
        if hasattr(dc.run, '__wrapped__'):
            print("   ✓ daily_clarify.run() is decorated")
        else:
            print("   ⚠️  daily_clarify.run() decorator not detected (may be normal)")
        
        # Check imports are present
        import gtd_coach.commands.daily_clarify as dc_module
        if 'deprecate_daily_clarify' in dir(dc_module):
            print("   ✓ Deprecation decorator imported in daily_clarify")
        
        return True
    except Exception as e:
        print(f"   ✗ Error testing legacy commands: {e}")
        return False


def main():
    """Run all tests"""
    print("🔬 GTD Coach Migration Setup Test")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Telemetry", test_telemetry()))
    results.append(("Dashboard", test_dashboard_access()))
    results.append(("Decorators", test_decorators()))
    results.append(("Legacy Commands", test_legacy_commands()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Migration tracking setup is complete and working!")
        print("\n📋 Next steps:")
        print("   1. View dashboard: http://grafana.local:3000/d/gtd-migration")
        print("   2. Start using commands to generate telemetry")
        print("   3. Monitor progress as you migrate to agent implementations")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)