"""
GTD Coach LLM-as-a-Judge Evaluation System

Provides non-blocking evaluation of coach interactions for:
- Task extraction accuracy
- Memory relevance
- Coaching quality
"""

from .post_session import PostSessionEvaluator

__all__ = ['PostSessionEvaluator']