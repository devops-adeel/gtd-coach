"""
Persistence layer for GTD Coach agent system.
Provides checkpointing and state recovery capabilities.
"""

from .checkpointer import (
    CheckpointerManager,
    get_checkpointer_manager,
    get_checkpointer
)

__all__ = [
    'CheckpointerManager',
    'get_checkpointer_manager',
    'get_checkpointer'
]