#!/usr/bin/env python3
"""
Add Langfuse Integration Knowledge to Graphiti
This script adds comprehensive documentation about Langfuse integration patterns
from the GTD Coach project to the Graphiti knowledge graph.
"""

import json
import asyncio
from datetime import datetime, timezone
import os
import sys

# Import Graphiti MCP client
# Note: This assumes you have the Graphiti MCP server running
# You may need to adjust the import based on your setup

async def add_langfuse_knowledge():
    """Add all Langfuse integration knowledge to Graphiti"""
    
    # We'll use the MCP tools to add episodes
    # For this example, I'll structure the calls as they would be made
    
    print("Adding Langfuse Integration Knowledge to Graphiti...")
    print("=" * 60)
    
    # Group ID for all Langfuse knowledge
    group_id = "langfuse-integration-knowledge"
    
    # Category 1: Trace Management Operations
    print("\n📊 Adding Trace Management Operations...")
    
    # Episode 1.1: Trace Linking Configuration (JSON)
    episode_1_1 = {
        "name": "Langfuse Trace Linking Configuration",
        "episode_body": json.dumps({
            "trace_linking": {
                "method": "langfuse_prompt_parameter",
                "implementation": "openai_kwargs['langfuse_prompt'] = prompt_object",
                "wrapper": "from langfuse.openai import OpenAI",
                "automatic_capture": ["model_params", "latency", "tokens", "cost"]
            },
            "code_example": """completion = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    langfuse_prompt=prompt,
    metadata={
        "langfuse_session_id": session_id,
        "langfuse_user_id": user_id
    }
)"""
        }),
        "source": "json",
        "source_description": "Langfuse trace linking configuration from GTD Coach",
        "group_id": group_id
    }
    
    # Episode 1.2: Metadata Enrichment Pattern (JSON)
    episode_1_2 = {
        "name": "Langfuse Metadata Enrichment Pattern",
        "episode_body": json.dumps({
            "metadata_structure": {
                "special_fields": {
                    "langfuse_session_id": "Groups related LLM calls in a session",
                    "langfuse_user_id": "Tracks interactions per user",
                    "langfuse_tags": ["variant:firm", "phase:MIND_SWEEP", "gtd-review", "week:2025-W32"]
                },
                "custom_fields": {
                    "phase_metrics": {
                        "items_captured": 10,
                        "capture_duration": 5.2,
                        "phase_name": "MIND_SWEEP"
                    },
                    "graphiti_batch_id": "batch_001",
                    "timing_session_active": True,
                    "adhd_patterns_detected": ["task_switching", "hyperfocus"]
                }
            },
            "implementation_notes": "Special fields with langfuse_ prefix are automatically recognized"
        }),
        "source": "json",
        "source_description": "Langfuse metadata enrichment patterns",
        "group_id": group_id
    }
    
    # Episode 1.3: Session Tracking Guide (Text)
    episode_1_3 = {
        "name": "Langfuse Session Tracking Guide",
        "episode_body": """Langfuse Session Tracking Best Practices for AI Applications:

1. Session Consistency Across Multiple LLM Calls:
   - Use a consistent session_id (e.g., datetime.now().strftime('%Y%m%d_%H%M%S'))
   - Pass session_id in metadata for every LLM call
   - Sessions group related interactions for analysis

2. User Identification Patterns:
   - For anonymous users: Use week-based IDs (e.g., '2025-W32')
   - For authenticated users: Use consistent user UUID
   - Store user_node_uuid in Graphiti for context centering

3. Performance Monitoring:
   - Track latency per phase (startup, mind_sweep, etc.)
   - Monitor token usage and costs
   - Measure completion rates for ADHD coaching sessions

4. Trace Navigation in Langfuse UI:
   - Traces are hierarchical: Session > Traces > Spans
   - Filter by tags to find specific variants or phases
   - Use session view to see full user journey

5. A/B Testing with Traces:
   - Tag traces with variant (variant:firm or variant:gentle)
   - Compare metrics across variants in Langfuse dashboard
   - Export data for statistical analysis""",
        "source": "text",
        "source_description": "Comprehensive guide for Langfuse session tracking",
        "group_id": group_id
    }
    
    # Category 2: Implementation Details
    print("\n⚙️ Adding Implementation Details...")
    
    # Episode 2.1: Environment Configuration (JSON)
    episode_2_1 = {
        "name": "Langfuse Environment Configuration",
        "episode_body": json.dumps({
            "environment_variables": {
                "required": {
                    "LANGFUSE_HOST": "http://langfuse-prod-langfuse-web-1.orb.local",
                    "LANGFUSE_PUBLIC_KEY": "pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed",
                    "LANGFUSE_SECRET_KEY": "sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9"
                },
                "optional": {
                    "LANGFUSE_CACHE_TTL_SECONDS": 300,
                    "LANGFUSE_FLUSH_INTERVAL": 1000,
                    "LANGFUSE_ENABLED": "true"
                }
            },
            "dotenv_setup": {
                "file_location": ".env",
                "load_method": "from dotenv import load_dotenv; load_dotenv()",
                "security_note": "Never commit .env file with real credentials"
            },
            "docker_env": {
                "pass_through": ["LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
                "docker_compose": "environment: - LANGFUSE_HOST=${LANGFUSE_HOST}"
            }
        }),
        "source": "json",
        "source_description": "Langfuse environment configuration patterns",
        "group_id": group_id
    }
    
    # Episode 2.2: OpenAI Wrapper Pattern (JSON)
    episode_2_2 = {
        "name": "Langfuse OpenAI Wrapper Pattern",
        "episode_body": json.dumps({
            "import_pattern": {
                "langfuse_wrapper": "from langfuse.openai import OpenAI",
                "standard_openai": "from openai import OpenAI",
                "langfuse_client": "from langfuse import Langfuse"
            },
            "initialization": {
                "with_langfuse": {
                    "code": "client = OpenAI(base_url='http://localhost:1234/v1', api_key='lm-studio')",
                    "note": "Uses Langfuse wrapper for automatic tracing"
                },
                "fallback_chain": [
                    "Try Langfuse OpenAI wrapper",
                    "Fall back to standard OpenAI SDK",
                    "Fall back to direct HTTP requests"
                ]
            },
            "graceful_degradation": {
                "pattern": """try:
    from langfuse.openai import OpenAI
    client = OpenAI(...)
except ImportError:
    from openai import OpenAI
    client = OpenAI(...)
except:
    # Use requests library
    import requests""",
                "benefits": "Ensures system works without Langfuse"
            }
        }),
        "source": "json",
        "source_description": "Langfuse OpenAI SDK wrapper patterns",
        "group_id": group_id
    }
    
    # Episode 2.3: Graphiti Memory Integration (JSON)
    episode_2_3 = {
        "name": "Graphiti Memory Integration with Langfuse",
        "episode_body": json.dumps({
            "integration_pattern": {
                "store_trace_id": {
                    "location": "episode metadata",
                    "field": "langfuse_trace_id",
                    "usage": "Link Graphiti episodes to Langfuse traces"
                },
                "performance_metrics": {
                    "storage": "episode_body.performance_metrics",
                    "includes": ["latency", "tokens", "cost", "success"]
                },
                "ab_test_results": {
                    "storage": "episode_body.variant_performance",
                    "comparison": "firm vs gentle coaching tone"
                }
            },
            "workflow": {
                "steps": [
                    "Make LLM call with Langfuse tracing",
                    "Extract trace_id from response",
                    "Add episode to Graphiti with trace_id",
                    "Store performance metrics in episode"
                ]
            },
            "benefits": [
                "Connect memory to observability",
                "Track performance over time",
                "Analyze patterns across sessions"
            ]
        }),
        "source": "json",
        "source_description": "Graphiti and Langfuse integration patterns",
        "group_id": group_id
    }
    
    # Category 3: Troubleshooting Guide
    print("\n🔧 Adding Troubleshooting Guide...")
    
    # Episode 3.1: Content Type Error Resolution (JSON)
    episode_3_1 = {
        "name": "LM Studio Content Type Error Resolution",
        "episode_body": json.dumps({
            "error": {
                "message": "Invalid 'content': 'content' objects must have a 'type' field that is either 'text' or 'image_url'",
                "error_code": 400,
                "occurs_with": ["LM Studio", "Local LLMs", "Older OpenAI API versions"]
            },
            "root_cause": "OpenAI API expects simple string content, not complex object arrays",
            "solution": {
                "incorrect_format": {
                    "role": "user",
                    "content": [{"text": "Your message here"}]
                },
                "correct_format": {
                    "role": "user",
                    "content": "Your message here"
                }
            },
            "code_fix": """# Instead of:
messages = [{
    "role": "user",
    "content": [{"text": "Your message"}]  # Causes error
}]

# Use:
messages = [{
    "role": "user",
    "content": "Your message"  # Simple string format
}]""",
            "prevention": "Always use simple string content with LM Studio"
        }),
        "source": "json",
        "source_description": "LM Studio content type error troubleshooting",
        "group_id": group_id
    }
    
    # Episode 3.2: Mock Langfuse Client Pattern (JSON)
    episode_3_2 = {
        "name": "Mock Langfuse Client Pattern",
        "episode_body": json.dumps({
            "mock_pattern": {
                "class_name": "MockLangfuseClient",
                "methods": {
                    "get_prompt": "Returns MockLangfusePrompt object",
                    "flush": "No-op for testing",
                    "trace": "Returns mock trace object"
                },
                "mock_prompt": {
                    "compile": "Returns compiled prompt string",
                    "config": "Returns model configuration dict"
                }
            },
            "usage": {
                "purpose": "Testing without external Langfuse server",
                "implementation": """class MockLangfuseClient:
    def get_prompt(self, name, label=None):
        return MockLangfusePrompt()
    
    def flush(self):
        pass

class MockLangfusePrompt:
    def compile(self, **kwargs):
        return 'Mock compiled prompt'
    
    @property
    def config(self):
        return {'model': 'test-model'}"""
            },
            "test_example": """def test_with_mock():
    with patch('langfuse.Langfuse', MockLangfuseClient):
        # Test code here
        pass"""
        }),
        "source": "json",
        "source_description": "Mock Langfuse client patterns for testing",
        "group_id": group_id
    }
    
    # Episode 3.3: Connection Troubleshooting (Text)
    episode_3_3 = {
        "name": "Langfuse Connection Troubleshooting",
        "episode_body": """Common Langfuse Connection Issues and Solutions:

1. Authentication Failures:
   Problem: 401 Unauthorized errors
   Causes:
   - Incorrect PUBLIC_KEY or SECRET_KEY
   - Keys not loaded from environment
   - Expired or revoked keys
   Solutions:
   - Verify keys in Langfuse dashboard
   - Check .env file is loaded: load_dotenv()
   - Regenerate keys if needed

2. Network Timeouts:
   Problem: Connection timeouts to Langfuse server
   Causes:
   - Server unreachable
   - Firewall blocking connection
   - Incorrect LANGFUSE_HOST URL
   Solutions:
   - Verify server is running: curl $LANGFUSE_HOST/health
   - Check Docker network if using containers
   - Use correct protocol (http vs https)

3. Graceful Degradation Strategy:
   Implementation:
   ```python
   try:
       # Try Langfuse-wrapped client
       from langfuse.openai import OpenAI
       client = OpenAI(...)
   except Exception as e:
       logger.warning(f"Langfuse unavailable: {e}")
       # Fall back to standard OpenAI
       from openai import OpenAI
       client = OpenAI(...)
   ```
   
   Benefits:
   - System continues working without Langfuse
   - No user-facing errors
   - Logs issue for debugging

4. Cache Issues:
   Problem: Stale prompts after updates
   Solution: Clear cache or reduce TTL
   - Set LANGFUSE_CACHE_TTL_SECONDS=0 for testing
   - Default 300 seconds for production""",
        "source": "text",
        "source_description": "Langfuse connection troubleshooting guide",
        "group_id": group_id
    }
    
    # Category 4: Testing Patterns
    print("\n🧪 Adding Testing Patterns...")
    
    # Episode 4.1: Integration Test Structure (JSON)
    episode_4_1 = {
        "name": "Langfuse Integration Test Structure",
        "episode_body": json.dumps({
            "test_organization": {
                "test_files": {
                    "test_prompt_management.py": "12 tests for prompt operations",
                    "test_e2e_trace_linking.py": "4 tests for trace linking",
                    "test_helpers.py": "Mock fixtures and utilities",
                    "analyze_prompt_performance.py": "A/B testing analysis"
                },
                "test_categories": [
                    "Import and Setup",
                    "Configuration",
                    "Prompt Fetching",
                    "Variable Compilation",
                    "Trace Linking",
                    "Metadata Enrichment",
                    "A/B Testing",
                    "Graceful Degradation"
                ],
                "naming_convention": "test_<feature>_<scenario>"
            },
            "test_structure_example": """def test_trace_linking():
    # Arrange
    langfuse = Langfuse()
    prompt = langfuse.get_prompt("system", label="firm")
    
    # Act
    completion = client.chat.completions.create(
        messages=messages,
        langfuse_prompt=prompt
    )
    
    # Assert
    assert completion is not None
    # Verify trace was created in Langfuse"""
        }),
        "source": "json",
        "source_description": "Langfuse integration test structure patterns",
        "group_id": group_id
    }
    
    # Episode 4.2: Coverage Strategy (JSON)
    episode_4_2 = {
        "name": "Coverage Strategy for External Dependencies",
        "episode_body": json.dumps({
            "coverage_approach": {
                "test_with_mocks": {
                    "components": ["Langfuse client", "LM Studio responses", "Prompt objects"],
                    "rationale": "Test logic without external services"
                },
                "skip_in_ci": {
                    "tests": ["External service availability", "Network-dependent operations"],
                    "marker": "@pytest.mark.skipif(not LANGFUSE_AVAILABLE)"
                },
                "pass_criteria": {
                    "philosophy": "Setup correctness over runtime availability",
                    "example": "Test passes if configuration is correct, even if service is down"
                }
            },
            "virtual_environment": {
                "setup": "python3 -m venv test_venv",
                "activate": "source test_venv/bin/activate",
                "install": "pip install -r requirements-test.txt",
                "benefits": "Isolated dependencies, no system conflicts"
            },
            "coverage_command": """pytest \\
    --cov=langfuse_integration \\
    --cov-report=term-missing \\
    --cov-report=html \\
    test_prompt_management.py test_e2e_trace_linking.py"""
        }),
        "source": "json",
        "source_description": "Test coverage strategies for Langfuse integration",
        "group_id": group_id
    }
    
    # Episode 4.3: Import Pattern for Hyphenated Files (JSON)
    episode_4_3 = {
        "name": "Hyphenated Filename Import Pattern",
        "episode_body": json.dumps({
            "problem": {
                "error": "ModuleNotFoundError: No module named 'gtd_review'",
                "cause": "Python cannot import files with hyphens in name",
                "affected_file": "gtd-review.py"
            },
            "solution": {
                "method": "Use importlib.util for dynamic import",
                "code": """import importlib.util
from pathlib import Path

# Load module with hyphenated name
spec = importlib.util.spec_from_file_location(
    "gtd_review",  # Module name (without hyphen)
    str(Path.home() / "gtd-coach" / "gtd-review.py")  # File path
)
gtd_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gtd_review)

# Now use the module
GTDCoach = gtd_review.GTDCoach"""
            },
            "use_cases": [
                "Testing files with hyphens",
                "Dynamic module loading",
                "Working with legacy codebases"
            ]
        }),
        "source": "json",
        "source_description": "Import pattern for files with hyphens",
        "group_id": group_id
    }
    
    # Category 5: Operational Procedures
    print("\n📋 Adding Operational Procedures...")
    
    # Episode 5.1: Prompt Upload Procedure (Text)
    episode_5_1 = {
        "name": "Prompt Upload to Langfuse Procedure",
        "episode_body": """Step-by-Step Guide to Upload Prompts to Langfuse:

1. Prepare Prompt Files:
   - Create system-prompt-firm.txt (direct, time-focused tone)
   - Create system-prompt-gentle.txt (supportive, flexible tone)
   - Create system-prompt-fallback.txt (simplified for timeouts)

2. Create Upload Script (upload_prompts_to_langfuse.py):
   ```python
   from langfuse import Langfuse
   
   langfuse = Langfuse()
   
   # Upload firm variant
   with open('prompts/system-prompt-firm.txt', 'r') as f:
       firm_content = f.read()
   
   langfuse.create_prompt(
       name="gtd-coach-system",
       prompt=firm_content,
       labels=["firm", "production"],
       config={
           "model": "meta-llama-3.1-8b-instruct",
           "temperature": 0.7,
           "max_tokens": 500
       }
   )
   ```

3. Managing Variants:
   - Use labels to distinguish variants: ["firm"], ["gentle"]
   - Use "production" label for active versions
   - Use "staging" label for testing

4. Version Control Best Practices:
   - Keep prompt files in version control
   - Document changes in commit messages
   - Tag releases with prompt versions
   - Use semantic versioning for major changes

5. Testing New Prompts:
   - Upload with "staging" label first
   - Test with subset of users
   - Monitor performance metrics
   - Promote to "production" when validated

6. Rollback Procedure:
   - Keep previous versions in Langfuse
   - Change labels to revert: remove "production" from new, add to old
   - Monitor for improvements""",
        "source": "text",
        "source_description": "Procedure for uploading prompts to Langfuse",
        "group_id": group_id
    }
    
    # Episode 5.2: A/B Testing Analysis Workflow (JSON)
    episode_5_2 = {
        "name": "A/B Testing Analysis Workflow",
        "episode_body": json.dumps({
            "analysis_workflow": {
                "step_1_fetch_traces": {
                    "method": "langfuse.get_traces() or mock data",
                    "filters": "date_range, tags=['gtd-review']",
                    "output": "List of trace objects"
                },
                "step_2_extract_metrics": {
                    "metrics": {
                        "latency": "Response time in seconds",
                        "success_rate": "Percentage of successful completions",
                        "completion_rate": "Phases completed / total phases",
                        "items_captured": "Mind sweep productivity metric"
                    }
                },
                "step_3_compare_variants": {
                    "script": "analyze_prompt_performance.py",
                    "statistics": ["mean", "median", "p95", "success_rate"],
                    "visualization": "Comparison charts"
                },
                "step_4_export_results": {
                    "format": "JSON",
                    "location": "analysis/prompt_analysis_YYYYMMDD.json",
                    "includes": ["statistics", "winners", "raw_metrics"]
                }
            },
            "decision_criteria": {
                "latency": "Lower is better (target < 2s)",
                "success_rate": "Higher is better (target > 95%)",
                "completion_rate": "Higher is better (target > 80%)",
                "productivity": "More items captured is better"
            },
            "sample_output": {
                "winners": {
                    "latency": "firm",
                    "success": "gentle",
                    "completion": "firm",
                    "productivity": "firm"
                },
                "recommendation": "Use firm variant (won 3/4 metrics)"
            }
        }),
        "source": "json",
        "source_description": "A/B testing analysis workflow for prompts",
        "group_id": group_id
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ Successfully prepared 15 Langfuse knowledge episodes")
    print("📚 Categories added:")
    print("   1. Trace Management Operations (3 episodes)")
    print("   2. Implementation Details (3 episodes)")
    print("   3. Troubleshooting Guide (3 episodes)")
    print("   4. Testing Patterns (3 episodes)")
    print("   5. Operational Procedures (2 episodes)")
    print("\n📝 Note: Run this script with Graphiti MCP server active")
    print("   to actually add the episodes to the knowledge graph")
    
    # Return all episodes for processing
    return [
        episode_1_1, episode_1_2, episode_1_3,
        episode_2_1, episode_2_2, episode_2_3,
        episode_3_1, episode_3_2, episode_3_3,
        episode_4_1, episode_4_2, episode_4_3,
        episode_5_1, episode_5_2
    ]

if __name__ == "__main__":
    # Run the async function
    episodes = asyncio.run(add_langfuse_knowledge())
    
    print("\n📤 Episodes ready to be added to Graphiti")
    print("To add them, use the Graphiti MCP tools:")
    print("  - mcp__graphiti-memory__add_episode for each episode")
    print("  - Use the 'group_id' to organize all related knowledge")