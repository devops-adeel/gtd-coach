#!/usr/bin/env python3
"""
Add Langfuse Integration Knowledge to Graphiti - Simple text version.
This version adds episodes as text to avoid long processing times.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load Graphiti environment variables
load_dotenv('.env.graphiti')

# Import Graphiti
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

async def add_langfuse_knowledge_simple():
    """Add Langfuse knowledge as text episodes for faster processing"""
    
    # Initialize Graphiti client
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_password:
        print("❌ Error: NEO4J_PASSWORD not found in .env.graphiti")
        return 0, 1
    
    print("🔗 Connecting to Graphiti...")
    client = Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
    )
    
    print("✅ Connected to Graphiti")
    
    # Group ID and timestamp
    group_id = "langfuse-integration-knowledge"
    reference_time = datetime.now(timezone.utc)
    
    # Combined episode with all Langfuse knowledge
    langfuse_knowledge = """
# Langfuse Integration Knowledge from GTD Coach

## 1. Trace Management Operations

### Trace Linking Configuration
- Method: Use langfuse_prompt parameter in OpenAI calls
- Implementation: openai_kwargs['langfuse_prompt'] = prompt_object
- Import: from langfuse.openai import OpenAI
- Automatically captures: model parameters, latency, tokens, cost
- Code example: client.chat.completions.create(model='gpt-4', messages=messages, langfuse_prompt=prompt, metadata={'langfuse_session_id': session_id, 'langfuse_user_id': user_id})

### Metadata Enrichment Pattern
- Special fields (langfuse_ prefix automatically recognized):
  - langfuse_session_id: Groups related LLM calls in a session
  - langfuse_user_id: Tracks interactions per user
  - langfuse_tags: ['variant:firm', 'phase:MIND_SWEEP', 'gtd-review', 'week:2025-W32']
- Custom fields:
  - phase_metrics: {items_captured: 10, capture_duration: 5.2}
  - graphiti_batch_id: For linking to memory system
  - timing_session_active: Integration with Timing app
  - adhd_patterns_detected: ['task_switching', 'hyperfocus']

### Session Tracking Best Practices
- Use consistent session_id across multiple LLM calls
- For anonymous users: Use week-based IDs (e.g., '2025-W32')
- For authenticated users: Use consistent user UUID
- Store user_node_uuid in Graphiti for context centering
- Track latency per phase, token usage, completion rates
- Traces are hierarchical: Session > Traces > Spans
- Tag traces with variant for A/B testing

## 2. Implementation Details

### Environment Configuration
Required variables:
- LANGFUSE_HOST: http://langfuse-server.local
- LANGFUSE_PUBLIC_KEY: pk-lf-xxxx
- LANGFUSE_SECRET_KEY: sk-lf-xxxx

Optional variables:
- LANGFUSE_CACHE_TTL_SECONDS: 300 (5 minute cache)
- LANGFUSE_FLUSH_INTERVAL: 1000
- LANGFUSE_ENABLED: true

Setup: from dotenv import load_dotenv; load_dotenv()
Security: Never commit .env file with real credentials
Docker: Pass through env vars in docker-compose.yml

### OpenAI Wrapper Pattern
Import pattern:
- Langfuse wrapper: from langfuse.openai import OpenAI
- Standard OpenAI: from openai import OpenAI
- Langfuse client: from langfuse import Langfuse

Graceful degradation chain:
1. Try Langfuse OpenAI wrapper
2. Fall back to standard OpenAI SDK
3. Fall back to direct HTTP requests

Benefits: System continues working without Langfuse

### Graphiti Memory Integration
- Store trace_id in episode metadata
- Link performance metrics to memory episodes
- Track A/B test results in knowledge graph
- Workflow: LLM call → Extract trace_id → Add to Graphiti → Store metrics

## 3. Troubleshooting Guide

### LM Studio Content Type Error
Error: "Invalid 'content': 'content' objects must have a 'type' field"
Root cause: OpenAI API expects simple string content
Solution: Use {'role': 'user', 'content': 'message'} not {'role': 'user', 'content': [{'text': 'message'}]}
Prevention: Always use simple string content with LM Studio

### Mock Langfuse Client Pattern
For testing without external server:
- Create MockLangfuseClient class
- Methods: get_prompt(), flush(), trace()
- MockLangfusePrompt with compile() and config property
- Usage: with patch('langfuse.Langfuse', MockLangfuseClient)

### Connection Troubleshooting
Authentication failures:
- Verify keys in Langfuse dashboard
- Check .env file is loaded
- Regenerate keys if needed

Network timeouts:
- Verify server is running: curl $LANGFUSE_HOST/health
- Check Docker network configuration
- Use correct protocol (http vs https)

Cache issues:
- Set LANGFUSE_CACHE_TTL_SECONDS=0 for testing
- Default 300 seconds for production

## 4. Testing Patterns

### Integration Test Structure
Test files:
- test_prompt_management.py: 12 tests for prompt operations
- test_e2e_trace_linking.py: 4 tests for trace linking
- test_helpers.py: Mock fixtures and utilities
- analyze_prompt_performance.py: A/B testing analysis

Test categories: Import/Setup, Configuration, Prompt Fetching, Variable Compilation, Trace Linking, Metadata Enrichment, A/B Testing, Graceful Degradation

### Coverage Strategy
- Test with mocks: Langfuse client, LM Studio responses, Prompt objects
- Skip in CI: External service availability tests
- Pass criteria: Setup correctness over runtime availability
- Virtual environment: python3 -m venv test_venv
- Coverage command: pytest --cov=langfuse_integration --cov-report=html

### Hyphenated Filename Import Pattern
Problem: ModuleNotFoundError for gtd-review.py
Solution: Use importlib.util
Code: spec = importlib.util.spec_from_file_location('gtd_review', 'gtd-review.py')

## 5. Operational Procedures

### Prompt Upload to Langfuse
1. Prepare prompt files (firm, gentle, fallback)
2. Use langfuse.create_prompt() with name, content, labels, config
3. Manage variants with labels: ['firm'], ['gentle'], ['production'], ['staging']
4. Version control best practices
5. Test with staging label first
6. Monitor metrics and promote to production
7. Rollback by changing labels

### A/B Testing Analysis Workflow
1. Fetch traces: langfuse.get_traces() with filters
2. Extract metrics: latency, success_rate, completion_rate, items_captured
3. Compare variants: analyze_prompt_performance.py
4. Export results: JSON to analysis/prompt_analysis_YYYYMMDD.json

Decision criteria:
- Latency: Lower is better (< 2s)
- Success rate: Higher is better (> 95%)
- Completion rate: Higher is better (> 80%)
- Productivity: More items captured is better

## Key Takeaways
- Langfuse provides comprehensive LLM observability
- Trace linking enables performance tracking per prompt version
- Metadata enrichment connects traces to business logic
- Graceful degradation ensures system reliability
- A/B testing enables data-driven prompt optimization
- Integration with Graphiti creates memory-aware AI systems
"""
    
    try:
        # Add as a single comprehensive text episode
        await client.add_episode(
            name="Langfuse Integration Complete Guide",
            episode_body=langfuse_knowledge,
            source=EpisodeType.text,
            reference_time=reference_time,
            source_description="Comprehensive Langfuse integration knowledge from GTD Coach production implementation",
            group_id=group_id
        )
        print("✅ Successfully added Langfuse knowledge to Graphiti")
        return 1, 0
    except Exception as e:
        print(f"❌ Failed to add episode: {e}")
        return 0, 1

if __name__ == "__main__":
    success, failed = asyncio.run(add_langfuse_knowledge_simple())
    
    if failed == 0:
        print("\n🎉 Langfuse knowledge successfully added to Graphiti!")
        print("🔍 Search using group_id: 'langfuse-integration-knowledge'")
        sys.exit(0)
    else:
        print(f"\n⚠️ Failed to add knowledge to Graphiti")
        sys.exit(1)