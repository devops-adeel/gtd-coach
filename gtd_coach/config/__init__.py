"""
GTD Coach configuration module.
"""

from .features import (
    FeatureFlags,
    RolloutManager,
    feature_flags,
    rollout_manager,
    should_use_agent,
    should_run_shadow,
    get_status
)

__all__ = [
    'FeatureFlags',
    'RolloutManager',
    'feature_flags',
    'rollout_manager',
    'should_use_agent',
    'should_run_shadow',
    'get_status'
]