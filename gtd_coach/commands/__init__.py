#!/usr/bin/env python3
"""
GTD Coach Commands Module

Provides CLI commands with feature flag support for transitioning
from legacy workflow to LangGraph agent-based system.
"""

from .cli import cli
from .daily import daily_capture, resume
from .weekly import weekly_review
from .config import config_group
from .test import test_group

__all__ = [
    'cli',
    'daily_capture',
    'resume',
    'weekly_review',
    'config_group',
    'test_group'
]

# Version info
__version__ = '2.0.0-agent'