"""
Feature flag management for GTD Coach migration to LangGraph.
Enables gradual rollout and emergency rollback capabilities.
"""

import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class FeatureFlags:
    """
    Centralized feature flag management with percentage-based rollout.
    
    Environment variables:
    - USE_LANGGRAPH: "true" to enable agent globally
    - AGENT_ROLLOUT_PCT: 0-100 percentage of users to get agent
    - AGENT_KILL_SWITCH: "true" to disable agent immediately
    - AGENT_SHADOW_MODE: "true" to run agent in shadow mode
    """
    
    # Feature flag environment variables
    USE_LANGGRAPH_AGENT = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
    AGENT_ROLLOUT_PCT = int(os.getenv("AGENT_ROLLOUT_PCT", "0"))
    KILL_SWITCH = os.getenv("AGENT_KILL_SWITCH", "false").lower() == "true"
    SHADOW_MODE = os.getenv("AGENT_SHADOW_MODE", "true").lower() == "true"
    
    # Performance monitoring flags
    LOG_PERFORMANCE = os.getenv("LOG_AGENT_PERFORMANCE", "true").lower() == "true"
    COMPARE_OUTPUTS = os.getenv("COMPARE_AGENT_OUTPUTS", "true").lower() == "true"
    
    # Rollback thresholds
    ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "0.1"))  # 10%
    LATENCY_THRESHOLD_MS = int(os.getenv("LATENCY_THRESHOLD_MS", "5000"))  # 5 seconds
    
    @classmethod
    def should_use_agent(cls, session_id: str) -> bool:
        """
        Determine if a session should use the LangGraph agent.
        Uses deterministic hashing for consistent routing per session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if this session should use the agent
        """
        # Emergency kill switch takes priority
        if cls.KILL_SWITCH:
            return False
        
        # Global flag override
        if cls.USE_LANGGRAPH_AGENT:
            return True
        
        # Percentage-based rollout
        if cls.AGENT_ROLLOUT_PCT == 0:
            return False
        
        if cls.AGENT_ROLLOUT_PCT >= 100:
            return True
        
        # Deterministic routing based on session hash
        session_hash = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        return (session_hash % 100) < cls.AGENT_ROLLOUT_PCT
    
    @classmethod
    def should_run_shadow(cls, session_id: str) -> bool:
        """
        Determine if shadow mode should run for comparison.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if shadow mode should run
        """
        # Only run shadow if not using agent directly
        if cls.should_use_agent(session_id):
            return False
        
        return cls.SHADOW_MODE and not cls.KILL_SWITCH
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get current feature flag configuration"""
        return {
            "use_langgraph": cls.USE_LANGGRAPH_AGENT,
            "rollout_percentage": cls.AGENT_ROLLOUT_PCT,
            "kill_switch": cls.KILL_SWITCH,
            "shadow_mode": cls.SHADOW_MODE,
            "log_performance": cls.LOG_PERFORMANCE,
            "compare_outputs": cls.COMPARE_OUTPUTS,
            "error_threshold": cls.ERROR_RATE_THRESHOLD,
            "latency_threshold_ms": cls.LATENCY_THRESHOLD_MS,
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    def save_config(cls, config_dir: Optional[Path] = None):
        """Save current configuration to file for persistence"""
        if config_dir is None:
            config_dir = Path(__file__).parent
        
        config_file = config_dir / "feature_flags.json"
        
        with open(config_file, 'w') as f:
            json.dump(cls.get_config(), f, indent=2)
        
        return config_file
    
    @classmethod
    def load_config(cls, config_dir: Optional[Path] = None):
        """Load configuration from file (for override)"""
        if config_dir is None:
            config_dir = Path(__file__).parent
        
        config_file = config_dir / "feature_flags.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                
                # Override environment variables with saved config
                if "rollout_percentage" in config:
                    cls.AGENT_ROLLOUT_PCT = config["rollout_percentage"]
                if "kill_switch" in config:
                    cls.KILL_SWITCH = config["kill_switch"]
                if "shadow_mode" in config:
                    cls.SHADOW_MODE = config["shadow_mode"]
                
                return config
        
        return None
    
    @classmethod
    def activate_kill_switch(cls):
        """Emergency disable of agent system"""
        cls.KILL_SWITCH = True
        cls.save_config()
        print("⚠️ KILL SWITCH ACTIVATED - Agent system disabled")
    
    @classmethod
    def deactivate_kill_switch(cls):
        """Re-enable agent system after kill switch"""
        cls.KILL_SWITCH = False
        cls.save_config()
        print("✅ Kill switch deactivated - Agent system re-enabled")
    
    @classmethod
    def set_rollout_percentage(cls, percentage: int):
        """Update rollout percentage"""
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        cls.AGENT_ROLLOUT_PCT = percentage
        cls.save_config()
        print(f"📊 Rollout percentage set to {percentage}%")
    
    @classmethod
    def get_status(cls) -> str:
        """Get human-readable status of feature flags"""
        lines = [
            "Feature Flag Status",
            "=" * 40
        ]
        
        if cls.KILL_SWITCH:
            lines.append("⚠️ KILL SWITCH ACTIVE - Agent disabled")
        elif cls.USE_LANGGRAPH_AGENT:
            lines.append("✅ Agent GLOBALLY ENABLED")
        elif cls.AGENT_ROLLOUT_PCT > 0:
            lines.append(f"📊 Rollout: {cls.AGENT_ROLLOUT_PCT}% of sessions")
            if cls.SHADOW_MODE:
                lines.append("👻 Shadow mode: ENABLED")
        else:
            lines.append("🔄 Using legacy system")
        
        if cls.LOG_PERFORMANCE:
            lines.append("📈 Performance logging: ON")
        
        return "\n".join(lines)


class RolloutManager:
    """Manages gradual rollout with monitoring and automatic rollback"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".gtd-coach" / "rollout"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.data_dir / "rollout_metrics.json"
        self.load_metrics()
    
    def load_metrics(self):
        """Load rollout metrics from file"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {
                "sessions_total": 0,
                "sessions_agent": 0,
                "sessions_legacy": 0,
                "errors_agent": 0,
                "errors_legacy": 0,
                "avg_latency_agent_ms": 0,
                "avg_latency_legacy_ms": 0,
                "rollout_history": []
            }
    
    def save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def record_session(self, used_agent: bool, success: bool, latency_ms: float):
        """Record metrics for a session"""
        self.metrics["sessions_total"] += 1
        
        if used_agent:
            self.metrics["sessions_agent"] += 1
            if not success:
                self.metrics["errors_agent"] += 1
            
            # Update average latency
            prev_avg = self.metrics["avg_latency_agent_ms"]
            count = self.metrics["sessions_agent"]
            self.metrics["avg_latency_agent_ms"] = (
                (prev_avg * (count - 1) + latency_ms) / count
            )
        else:
            self.metrics["sessions_legacy"] += 1
            if not success:
                self.metrics["errors_legacy"] += 1
            
            # Update average latency
            prev_avg = self.metrics["avg_latency_legacy_ms"]
            count = self.metrics["sessions_legacy"]
            self.metrics["avg_latency_legacy_ms"] = (
                (prev_avg * (count - 1) + latency_ms) / count
            )
        
        self.save_metrics()
        self.check_rollback_conditions()
    
    def check_rollback_conditions(self):
        """Check if automatic rollback should be triggered"""
        if self.metrics["sessions_agent"] < 10:
            # Not enough data yet
            return
        
        # Calculate error rates
        agent_error_rate = (
            self.metrics["errors_agent"] / self.metrics["sessions_agent"]
            if self.metrics["sessions_agent"] > 0 else 0
        )
        
        # Check error rate threshold
        if agent_error_rate > FeatureFlags.ERROR_RATE_THRESHOLD:
            print(f"⚠️ High error rate detected: {agent_error_rate:.1%}")
            print("🔄 Triggering automatic rollback")
            FeatureFlags.activate_kill_switch()
            self.record_rollback("high_error_rate", agent_error_rate)
        
        # Check latency threshold
        if self.metrics["avg_latency_agent_ms"] > FeatureFlags.LATENCY_THRESHOLD_MS:
            print(f"⚠️ High latency detected: {self.metrics['avg_latency_agent_ms']:.0f}ms")
            print("🔄 Triggering automatic rollback")
            FeatureFlags.activate_kill_switch()
            self.record_rollback("high_latency", self.metrics["avg_latency_agent_ms"])
    
    def record_rollback(self, reason: str, value: float):
        """Record a rollback event"""
        self.metrics["rollout_history"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "rollback",
            "reason": reason,
            "value": value,
            "rollout_pct": FeatureFlags.AGENT_ROLLOUT_PCT
        })
        self.save_metrics()
    
    def get_comparison_report(self) -> str:
        """Generate comparison report between agent and legacy"""
        if self.metrics["sessions_agent"] == 0:
            return "No agent sessions recorded yet"
        
        if self.metrics["sessions_legacy"] == 0:
            return "No legacy sessions for comparison"
        
        agent_error_rate = (
            self.metrics["errors_agent"] / self.metrics["sessions_agent"]
        )
        legacy_error_rate = (
            self.metrics["errors_legacy"] / self.metrics["sessions_legacy"]
        )
        
        lines = [
            "Agent vs Legacy Comparison",
            "=" * 40,
            f"Sessions: {self.metrics['sessions_agent']} agent, {self.metrics['sessions_legacy']} legacy",
            f"Error rate: {agent_error_rate:.1%} vs {legacy_error_rate:.1%}",
            f"Avg latency: {self.metrics['avg_latency_agent_ms']:.0f}ms vs {self.metrics['avg_latency_legacy_ms']:.0f}ms"
        ]
        
        # Performance comparison
        if self.metrics["avg_latency_agent_ms"] < self.metrics["avg_latency_legacy_ms"]:
            improvement = (
                (self.metrics["avg_latency_legacy_ms"] - self.metrics["avg_latency_agent_ms"])
                / self.metrics["avg_latency_legacy_ms"] * 100
            )
            lines.append(f"✅ Agent is {improvement:.1f}% faster")
        else:
            degradation = (
                (self.metrics["avg_latency_agent_ms"] - self.metrics["avg_latency_legacy_ms"])
                / self.metrics["avg_latency_legacy_ms"] * 100
            )
            lines.append(f"⚠️ Agent is {degradation:.1f}% slower")
        
        return "\n".join(lines)


# Create singleton instances
feature_flags = FeatureFlags()
rollout_manager = RolloutManager()

# Export for convenience
should_use_agent = feature_flags.should_use_agent
should_run_shadow = feature_flags.should_run_shadow
get_status = feature_flags.get_status