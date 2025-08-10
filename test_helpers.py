#!/usr/bin/env python3
"""
Test helpers and mock fixtures for GTD Coach tests.
"""

from unittest.mock import Mock, MagicMock, patch
import datetime
import json


class MockLangfusePrompt:
    """Mock Langfuse prompt object"""
    
    def __init__(self, name="gtd-coach-system", label="firm"):
        self.name = name
        self.label = label
        self.prompt = "You are a GTD coach. Phase: {{phase_name}}, Time remaining: {{time_remaining}}"
        self.messages = [
            {"role": "system", "content": self.prompt}
        ]
        self.config = {
            "model": "meta-llama-3.1-8b-instruct",
            "temperature": 0.7,
            "max_tokens": 500,
            "phase_times": {
                "STARTUP": 2,
                "MIND_SWEEP": 10,
                "PROJECT_REVIEW": 12,
                "PRIORITIZATION": 5,
                "WRAP_UP": 3
            }
        }
    
    def compile(self, **kwargs):
        """Compile prompt with variables"""
        compiled = self.prompt
        for key, value in kwargs.items():
            compiled = compiled.replace(f"{{{{{key}}}}}", str(value))
        return [{"role": "system", "content": compiled}]
    
    def toJSON(self):
        """Convert to JSON for trace linking"""
        return {
            "name": self.name,
            "label": self.label,
            "version": 1,
            "config": self.config
        }


class MockLangfuseClient:
    """Mock Langfuse client"""
    
    def __init__(self, public_key=None, secret_key=None, host=None):
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self._prompts = {
            ("gtd-coach-system", "firm"): MockLangfusePrompt("gtd-coach-system", "firm"),
            ("gtd-coach-system", "gentle"): MockLangfusePrompt("gtd-coach-system", "gentle"),
            ("gtd-coach-fallback", None): MockLangfusePrompt("gtd-coach-fallback", None)
        }
        self._traces = []
        
    def get_prompt(self, name, label=None, cache_ttl_seconds=None):
        """Get a mock prompt"""
        key = (name, label)
        if key in self._prompts:
            return self._prompts[key]
        # Create a default prompt if not found
        return MockLangfusePrompt(name, label)
    
    def get_traces(self, **kwargs):
        """Get mock traces for performance analysis"""
        # Return some mock traces with different variants
        return [
            Mock(
                tags=["variant:firm", "gtd-review"],
                latency=1.2,
                success=True,
                metadata={
                    "phases_completed": ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW", "PRIORITIZATION", "WRAP_UP"],
                    "phase_mind_sweep_items": 8
                },
                scores=[]
            ),
            Mock(
                tags=["variant:gentle", "gtd-review"],
                latency=1.4,
                success=True,
                metadata={
                    "phases_completed": ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW"],
                    "phase_mind_sweep_items": 6
                },
                scores=[]
            ),
            Mock(
                tags=["variant:firm", "gtd-review"],
                latency=1.1,
                success=True,
                metadata={
                    "phases_completed": ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW", "PRIORITIZATION", "WRAP_UP"],
                    "phase_mind_sweep_items": 10
                },
                scores=[]
            )
        ]
    
    def trace(self, **kwargs):
        """Create a mock trace"""
        trace = Mock()
        trace.id = f"trace_{len(self._traces)}"
        trace.span = Mock(return_value=Mock())
        self._traces.append(trace)
        return trace
    
    def create_trace_id(self):
        """Create a mock trace ID"""
        return f"trace_{datetime.datetime.now().timestamp()}"
    
    def flush(self):
        """Mock flush method"""
        pass
    
    def update_current_trace(self, **kwargs):
        """Mock update current trace"""
        pass


class MockOpenAIResponse:
    """Mock OpenAI chat completion response"""
    
    def __init__(self, content="Test response"):
        self.choices = [
            Mock(
                message=Mock(content=content),
                finish_reason="stop"
            )
        ]
        self.usage = Mock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        self.model = "meta-llama-3.1-8b-instruct"
        self.id = "chatcmpl-test123"


class MockLangfuseOpenAI:
    """Mock Langfuse OpenAI wrapper"""
    
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = Mock(return_value=MockOpenAIResponse())
    
    def flushAsync(self):
        """Mock async flush"""
        return Mock()


def mock_gtdcoach_import():
    """Mock the GTDCoach import"""
    mock_coach = Mock()
    mock_coach.GTDCoach = Mock
    mock_coach.GTDCoach.return_value = Mock(
        openai_client=MockLangfuseOpenAI(),
        session_id="test_session",
        user_id="test_user",
        prompt_tone="firm",
        phase_metrics={},
        mindsweep_items=[],
        current_phase="STARTUP",
        system_prompt=MockLangfusePrompt(),
        send_message=Mock(return_value="Test response"),
        complete_phase=Mock(),
        update_phase_metrics=Mock()
    )
    return mock_coach


def create_test_environment():
    """Create a complete test environment with all mocks"""
    import os
    
    # Set test environment variables
    os.environ["LANGFUSE_PUBLIC_KEY"] = "test-public-key"
    os.environ["LANGFUSE_SECRET_KEY"] = "test-secret-key"
    os.environ["LANGFUSE_HOST"] = "http://localhost:3000"
    
    # Create mock patches
    patches = {
        'langfuse.Langfuse': Mock(return_value=MockLangfuseClient()),
        'langfuse.openai.OpenAI': MockLangfuseOpenAI,
        'openai.OpenAI': MockLangfuseOpenAI,
    }
    
    return patches


def cleanup_test_environment():
    """Clean up test environment"""
    import os
    
    # Remove test environment variables
    for key in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        if key in os.environ:
            del os.environ[key]