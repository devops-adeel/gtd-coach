#!/usr/bin/env python3
"""
Granular feature flags for phase-by-phase migration to LangGraph.
Extends the base FeatureFlags with per-phase control.
"""

import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from gtd_coach.config.features import FeatureFlags


class MigrationPhase(Enum):
    """Phases that can be individually migrated"""
    STARTUP = "startup"
    MIND_SWEEP = "mind_sweep"
    PROJECT_REVIEW = "project_review"
    PRIORITIZATION = "prioritization"
    WRAPUP = "wrapup"
    EXPERIMENTS = "experiments"
    ADAPTIVE = "adaptive"
    COMMANDS = "commands"


class GranularFeatureFlags(FeatureFlags):
    """
    Granular feature flag management for incremental migration.
    Each phase/component can be independently controlled.
    """
    
    # Phase-specific feature flags (environment variables)
    USE_AGENT_STARTUP = os.getenv("USE_AGENT_STARTUP", "false").lower() == "true"
    USE_AGENT_MINDSWEEP = os.getenv("USE_AGENT_MINDSWEEP", "false").lower() == "true"
    USE_AGENT_PROJECT_REVIEW = os.getenv("USE_AGENT_PROJECT_REVIEW", "false").lower() == "true"
    USE_AGENT_PRIORITIZATION = os.getenv("USE_AGENT_PRIORITIZATION", "false").lower() == "true"
    USE_AGENT_WRAPUP = os.getenv("USE_AGENT_WRAPUP", "false").lower() == "true"
    
    # Feature-specific flags
    USE_AGENT_EXPERIMENTS = os.getenv("USE_AGENT_EXPERIMENTS", "false").lower() == "true"
    USE_AGENT_ADAPTIVE = os.getenv("USE_AGENT_ADAPTIVE", "false").lower() == "true"
    USE_AGENT_COMMANDS = os.getenv("USE_AGENT_COMMANDS", "false").lower() == "true"
    
    # Rollout percentages per phase (0-100)
    ROLLOUT_PCT_STARTUP = int(os.getenv("ROLLOUT_PCT_STARTUP", "0"))
    ROLLOUT_PCT_MINDSWEEP = int(os.getenv("ROLLOUT_PCT_MINDSWEEP", "0"))
    ROLLOUT_PCT_PROJECT_REVIEW = int(os.getenv("ROLLOUT_PCT_PROJECT_REVIEW", "0"))
    ROLLOUT_PCT_PRIORITIZATION = int(os.getenv("ROLLOUT_PCT_PRIORITIZATION", "0"))
    ROLLOUT_PCT_WRAPUP = int(os.getenv("ROLLOUT_PCT_WRAPUP", "0"))
    
    # Parallel execution flags (for A/B testing)
    PARALLEL_RUN_STARTUP = os.getenv("PARALLEL_RUN_STARTUP", "false").lower() == "true"
    PARALLEL_RUN_MINDSWEEP = os.getenv("PARALLEL_RUN_MINDSWEEP", "false").lower() == "true"
    PARALLEL_RUN_PROJECT_REVIEW = os.getenv("PARALLEL_RUN_PROJECT_REVIEW", "false").lower() == "true"
    PARALLEL_RUN_PRIORITIZATION = os.getenv("PARALLEL_RUN_PRIORITIZATION", "false").lower() == "true"
    PARALLEL_RUN_WRAPUP = os.getenv("PARALLEL_RUN_WRAPUP", "false").lower() == "true"
    
    @classmethod
    def should_use_agent_for_phase(cls, 
                                   phase: str, 
                                   session_id: str,
                                   force_check: bool = False) -> bool:
        """
        Determine if a specific phase should use the agent.
        
        Args:
            phase: Phase name (startup, mind_sweep, etc.)
            session_id: Unique session identifier
            force_check: Bypass kill switch for testing
            
        Returns:
            True if this phase should use the agent
        """
        # Emergency kill switch (unless forcing)
        if not force_check and cls.KILL_SWITCH:
            return False
        
        # Check phase-specific flags first
        phase_flags = {
            'startup': cls.USE_AGENT_STARTUP,
            'mind_sweep': cls.USE_AGENT_MINDSWEEP,
            'project_review': cls.USE_AGENT_PROJECT_REVIEW,
            'prioritization': cls.USE_AGENT_PRIORITIZATION,
            'wrapup': cls.USE_AGENT_WRAPUP,
            'experiments': cls.USE_AGENT_EXPERIMENTS,
            'adaptive': cls.USE_AGENT_ADAPTIVE,
            'commands': cls.USE_AGENT_COMMANDS
        }
        
        # If phase flag is explicitly set
        if phase_flags.get(phase, False):
            return True
        
        # Check global flag
        if cls.USE_LANGGRAPH_AGENT:
            return True
        
        # Check phase-specific rollout percentage
        rollout_pcts = {
            'startup': cls.ROLLOUT_PCT_STARTUP,
            'mind_sweep': cls.ROLLOUT_PCT_MINDSWEEP,
            'project_review': cls.ROLLOUT_PCT_PROJECT_REVIEW,
            'prioritization': cls.ROLLOUT_PCT_PRIORITIZATION,
            'wrapup': cls.ROLLOUT_PCT_WRAPUP
        }
        
        phase_rollout = rollout_pcts.get(phase, 0)
        
        if phase_rollout == 0:
            return False
        
        if phase_rollout >= 100:
            return True
        
        # Deterministic routing based on session + phase hash
        hash_input = f"{session_id}_{phase}"
        phase_hash = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        return (phase_hash % 100) < phase_rollout
    
    @classmethod
    def should_run_parallel(cls, phase: str) -> bool:
        """
        Determine if both systems should run in parallel for comparison.
        
        Args:
            phase: Phase name
            
        Returns:
            True if parallel execution is enabled for this phase
        """
        parallel_flags = {
            'startup': cls.PARALLEL_RUN_STARTUP,
            'mind_sweep': cls.PARALLEL_RUN_MINDSWEEP,
            'project_review': cls.PARALLEL_RUN_PROJECT_REVIEW,
            'prioritization': cls.PARALLEL_RUN_PRIORITIZATION,
            'wrapup': cls.PARALLEL_RUN_WRAPUP
        }
        
        return parallel_flags.get(phase, False)
    
    @classmethod
    def get_migration_status(cls) -> Dict[str, Any]:
        """Get current migration status for all phases"""
        phases = ['startup', 'mind_sweep', 'project_review', 
                 'prioritization', 'wrapup']
        
        status = {
            'global': {
                'kill_switch': cls.KILL_SWITCH,
                'global_agent': cls.USE_LANGGRAPH_AGENT,
                'global_rollout_pct': cls.AGENT_ROLLOUT_PCT
            },
            'phases': {}
        }
        
        for phase in phases:
            phase_flag = getattr(cls, f"USE_AGENT_{phase.upper()}", False)
            rollout_pct = getattr(cls, f"ROLLOUT_PCT_{phase.upper()}", 0)
            parallel = cls.should_run_parallel(phase)
            
            # Determine effective status
            if cls.KILL_SWITCH:
                effective_status = "disabled (kill switch)"
            elif phase_flag:
                effective_status = "fully migrated"
            elif cls.USE_LANGGRAPH_AGENT:
                effective_status = "fully migrated (global)"
            elif rollout_pct > 0:
                effective_status = f"rolling out ({rollout_pct}%)"
            else:
                effective_status = "legacy"
            
            status['phases'][phase] = {
                'flag': phase_flag,
                'rollout_pct': rollout_pct,
                'parallel_run': parallel,
                'effective_status': effective_status
            }
        
        # Calculate overall migration progress
        migrated_count = sum(
            1 for p in status['phases'].values() 
            if p['effective_status'].startswith('fully')
        )
        status['migration_progress'] = f"{migrated_count}/{len(phases)} phases migrated"
        
        return status
    
    @classmethod
    def set_phase_rollout(cls, phase: str, percentage: int):
        """
        Set rollout percentage for a specific phase.
        
        Args:
            phase: Phase name
            percentage: Rollout percentage (0-100)
        """
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        # Update the class attribute
        attr_name = f"ROLLOUT_PCT_{phase.upper()}"
        if hasattr(cls, attr_name):
            setattr(cls, attr_name, percentage)
            cls.save_config()
            print(f"📊 {phase} rollout set to {percentage}%")
        else:
            raise ValueError(f"Unknown phase: {phase}")
    
    @classmethod
    def enable_phase(cls, phase: str):
        """Fully enable agent for a specific phase"""
        attr_name = f"USE_AGENT_{phase.upper()}"
        if hasattr(cls, attr_name):
            setattr(cls, attr_name, True)
            cls.save_config()
            print(f"✅ Agent enabled for {phase}")
        else:
            raise ValueError(f"Unknown phase: {phase}")
    
    @classmethod
    def disable_phase(cls, phase: str):
        """Disable agent for a specific phase"""
        attr_name = f"USE_AGENT_{phase.upper()}"
        if hasattr(cls, attr_name):
            setattr(cls, attr_name, False)
            # Also reset rollout
            rollout_attr = f"ROLLOUT_PCT_{phase.upper()}"
            if hasattr(cls, rollout_attr):
                setattr(cls, rollout_attr, 0)
            cls.save_config()
            print(f"❌ Agent disabled for {phase}")
        else:
            raise ValueError(f"Unknown phase: {phase}")
    
    @classmethod
    def enable_parallel_run(cls, phase: str):
        """Enable parallel execution for a phase"""
        attr_name = f"PARALLEL_RUN_{phase.upper()}"
        if hasattr(cls, attr_name):
            setattr(cls, attr_name, True)
            cls.save_config()
            print(f"👥 Parallel run enabled for {phase}")
        else:
            raise ValueError(f"Unknown phase: {phase}")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get complete configuration including granular flags"""
        config = super().get_config()
        
        # Add granular phase flags
        config['granular'] = {
            'phases': {
                'startup': {
                    'enabled': cls.USE_AGENT_STARTUP,
                    'rollout_pct': cls.ROLLOUT_PCT_STARTUP,
                    'parallel': cls.PARALLEL_RUN_STARTUP
                },
                'mind_sweep': {
                    'enabled': cls.USE_AGENT_MINDSWEEP,
                    'rollout_pct': cls.ROLLOUT_PCT_MINDSWEEP,
                    'parallel': cls.PARALLEL_RUN_MINDSWEEP
                },
                'project_review': {
                    'enabled': cls.USE_AGENT_PROJECT_REVIEW,
                    'rollout_pct': cls.ROLLOUT_PCT_PROJECT_REVIEW,
                    'parallel': cls.PARALLEL_RUN_PROJECT_REVIEW
                },
                'prioritization': {
                    'enabled': cls.USE_AGENT_PRIORITIZATION,
                    'rollout_pct': cls.ROLLOUT_PCT_PRIORITIZATION,
                    'parallel': cls.PARALLEL_RUN_PRIORITIZATION
                },
                'wrapup': {
                    'enabled': cls.USE_AGENT_WRAPUP,
                    'rollout_pct': cls.ROLLOUT_PCT_WRAPUP,
                    'parallel': cls.PARALLEL_RUN_WRAPUP
                }
            },
            'features': {
                'experiments': cls.USE_AGENT_EXPERIMENTS,
                'adaptive': cls.USE_AGENT_ADAPTIVE,
                'commands': cls.USE_AGENT_COMMANDS
            }
        }
        
        return config
    
    @classmethod
    def get_migration_plan(cls) -> List[Dict[str, Any]]:
        """
        Get recommended migration plan based on current status.
        
        Returns:
            List of recommended next steps
        """
        status = cls.get_migration_status()
        plan = []
        
        # Recommended phase order
        phase_order = ['startup', 'mind_sweep', 'project_review', 
                      'prioritization', 'wrapup']
        
        for phase in phase_order:
            phase_status = status['phases'][phase]
            
            if phase_status['effective_status'] == 'legacy':
                # This is the next phase to migrate
                plan.append({
                    'phase': phase,
                    'action': 'start_rollout',
                    'recommendation': f"Begin {phase} migration with 10% rollout",
                    'command': f"GranularFeatureFlags.set_phase_rollout('{phase}', 10)"
                })
                break  # Only recommend one phase at a time
            
            elif 'rolling out' in phase_status['effective_status']:
                current_pct = phase_status['rollout_pct']
                if current_pct < 50:
                    plan.append({
                        'phase': phase,
                        'action': 'increase_rollout',
                        'recommendation': f"Increase {phase} rollout to {min(current_pct + 20, 50)}%",
                        'command': f"GranularFeatureFlags.set_phase_rollout('{phase}', {min(current_pct + 20, 50)})"
                    })
                else:
                    plan.append({
                        'phase': phase,
                        'action': 'complete_migration',
                        'recommendation': f"Complete {phase} migration (currently at {current_pct}%)",
                        'command': f"GranularFeatureFlags.enable_phase('{phase}')"
                    })
                break
        
        if not plan:
            # All phases migrated
            plan.append({
                'action': 'migration_complete',
                'recommendation': "All phases migrated! Consider removing legacy code.",
                'next_steps': [
                    "Run comprehensive tests",
                    "Monitor metrics for 1 week",
                    "Archive legacy code",
                    "Update documentation"
                ]
            })
        
        return plan


def test_granular_flags():
    """Test granular feature flags"""
    flags = GranularFeatureFlags()
    
    # Test phase-specific routing
    session_id = "test_session_123"
    
    # Test with different phases
    for phase in ['startup', 'mind_sweep', 'project_review']:
        should_use = flags.should_use_agent_for_phase(phase, session_id)
        print(f"{phase}: use_agent={should_use}")
    
    # Get migration status
    status = flags.get_migration_status()
    print(f"\nMigration status: {json.dumps(status, indent=2)}")
    
    # Get migration plan
    plan = flags.get_migration_plan()
    print(f"\nMigration plan: {json.dumps(plan, indent=2)}")
    
    print("✅ Granular feature flags test passed")


if __name__ == "__main__":
    test_granular_flags()