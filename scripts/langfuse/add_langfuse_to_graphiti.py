#!/usr/bin/env python3
"""
Add Langfuse Integration Knowledge to Graphiti using Python client.
This script connects directly to Graphiti and adds comprehensive documentation
about Langfuse integration patterns from the GTD Coach project.
"""

import json
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load Graphiti environment variables
load_dotenv('.env.graphiti')

# Import Graphiti
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

async def add_langfuse_knowledge_to_graphiti():
    """Add all Langfuse integration knowledge to Graphiti using Python client"""
    
    # Initialize Graphiti client
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_password:
        print("❌ Error: NEO4J_PASSWORD not found in .env.graphiti")
        return
    
    print("🔗 Connecting to Graphiti...")
    client = Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
    )
    
    print("✅ Connected to Graphiti")
    print("=" * 60)
    
    # Group ID for all Langfuse knowledge
    group_id = "langfuse-integration-knowledge"
    reference_time = datetime.now(timezone.utc)
    
    # Track success/failure
    episodes_added = []
    episodes_failed = []
    
    # Category 1: Trace Management Operations
    print("\n📊 Adding Trace Management Operations...")
    
    # Episode 1.1: Trace Linking Configuration (JSON)
    try:
        episode_1_1_data = {
            "trace_linking": {
                "method": "langfuse_prompt_parameter",
                "implementation": "openai_kwargs['langfuse_prompt'] = prompt_object",
                "wrapper": "from langfuse.openai import OpenAI",
                "automatic_capture": ["model_params", "latency", "tokens", "cost"]
            },
            "code_example": "completion = client.chat.completions.create(model='gpt-4', messages=messages, langfuse_prompt=prompt, metadata={'langfuse_session_id': session_id, 'langfuse_user_id': user_id})"
        }
        
        await client.add_episode(
            name="Langfuse Trace Linking Configuration",
            episode_body=json.dumps(episode_1_1_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Langfuse trace linking configuration from GTD Coach",
            group_id=group_id
        )
        episodes_added.append("1.1 Trace Linking Configuration")
        print("  ✅ Added Episode 1.1: Trace Linking Configuration")
    except Exception as e:
        episodes_failed.append(f"1.1: {str(e)}")
        print(f"  ❌ Failed Episode 1.1: {e}")
    
    # Episode 1.2: Metadata Enrichment Pattern (JSON)
    try:
        episode_1_2_data = {
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
        }
        
        await client.add_episode(
            name="Langfuse Metadata Enrichment Pattern",
            episode_body=json.dumps(episode_1_2_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Langfuse metadata enrichment patterns",
            group_id=group_id
        )
        episodes_added.append("1.2 Metadata Enrichment Pattern")
        print("  ✅ Added Episode 1.2: Metadata Enrichment Pattern")
    except Exception as e:
        episodes_failed.append(f"1.2: {str(e)}")
        print(f"  ❌ Failed Episode 1.2: {e}")
    
    # Episode 1.3: Session Tracking Guide (Text)
    try:
        episode_1_3_text = """Langfuse Session Tracking Best Practices for AI Applications:

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
   - Export data for statistical analysis"""
        
        await client.add_episode(
            name="Langfuse Session Tracking Guide",
            episode_body=episode_1_3_text,
            source=EpisodeType.text,
            reference_time=reference_time,
            source_description="Comprehensive guide for Langfuse session tracking",
            group_id=group_id
        )
        episodes_added.append("1.3 Session Tracking Guide")
        print("  ✅ Added Episode 1.3: Session Tracking Guide")
    except Exception as e:
        episodes_failed.append(f"1.3: {str(e)}")
        print(f"  ❌ Failed Episode 1.3: {e}")
    
    # Category 2: Implementation Details
    print("\n⚙️ Adding Implementation Details...")
    
    # Episode 2.1: Environment Configuration (JSON)
    try:
        episode_2_1_data = {
            "environment_variables": {
                "required": {
                    "LANGFUSE_HOST": "http://langfuse-prod-langfuse-web-1.orb.local",
                    "LANGFUSE_PUBLIC_KEY": "pk-lf-xxxx",
                    "LANGFUSE_SECRET_KEY": "sk-lf-xxxx"
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
        }
        
        await client.add_episode(
            name="Langfuse Environment Configuration",
            episode_body=json.dumps(episode_2_1_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Langfuse environment configuration patterns",
            group_id=group_id
        )
        episodes_added.append("2.1 Environment Configuration")
        print("  ✅ Added Episode 2.1: Environment Configuration")
    except Exception as e:
        episodes_failed.append(f"2.1: {str(e)}")
        print(f"  ❌ Failed Episode 2.1: {e}")
    
    # Episode 2.2: OpenAI Wrapper Pattern (JSON)
    try:
        episode_2_2_data = {
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
                "pattern": "try langfuse.openai import, except use standard openai, except use requests",
                "benefits": "Ensures system works without Langfuse"
            }
        }
        
        await client.add_episode(
            name="Langfuse OpenAI Wrapper Pattern",
            episode_body=json.dumps(episode_2_2_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Langfuse OpenAI SDK wrapper patterns",
            group_id=group_id
        )
        episodes_added.append("2.2 OpenAI Wrapper Pattern")
        print("  ✅ Added Episode 2.2: OpenAI Wrapper Pattern")
    except Exception as e:
        episodes_failed.append(f"2.2: {str(e)}")
        print(f"  ❌ Failed Episode 2.2: {e}")
    
    # Episode 2.3: Graphiti Memory Integration (JSON)
    try:
        episode_2_3_data = {
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
            "workflow": [
                "Make LLM call with Langfuse tracing",
                "Extract trace_id from response",
                "Add episode to Graphiti with trace_id",
                "Store performance metrics in episode"
            ],
            "benefits": [
                "Connect memory to observability",
                "Track performance over time",
                "Analyze patterns across sessions"
            ]
        }
        
        await client.add_episode(
            name="Graphiti Memory Integration with Langfuse",
            episode_body=json.dumps(episode_2_3_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Graphiti and Langfuse integration patterns",
            group_id=group_id
        )
        episodes_added.append("2.3 Graphiti Memory Integration")
        print("  ✅ Added Episode 2.3: Graphiti Memory Integration")
    except Exception as e:
        episodes_failed.append(f"2.3: {str(e)}")
        print(f"  ❌ Failed Episode 2.3: {e}")
    
    # Category 3: Troubleshooting Guide
    print("\n🔧 Adding Troubleshooting Guide...")
    
    # Episode 3.1: Content Type Error Resolution (JSON)
    try:
        episode_3_1_data = {
            "error": {
                "message": "Invalid 'content': 'content' objects must have a 'type' field",
                "error_code": 400,
                "occurs_with": ["LM Studio", "Local LLMs", "Older OpenAI API versions"]
            },
            "root_cause": "OpenAI API expects simple string content, not complex object arrays",
            "solution": {
                "incorrect_format": {"role": "user", "content": [{"text": "message"}]},
                "correct_format": {"role": "user", "content": "message"}
            },
            "code_fix": "Use simple string content: messages = [{'role': 'user', 'content': 'message'}]",
            "prevention": "Always use simple string content with LM Studio"
        }
        
        await client.add_episode(
            name="LM Studio Content Type Error Resolution",
            episode_body=json.dumps(episode_3_1_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="LM Studio content type error troubleshooting",
            group_id=group_id
        )
        episodes_added.append("3.1 Content Type Error Resolution")
        print("  ✅ Added Episode 3.1: Content Type Error Resolution")
    except Exception as e:
        episodes_failed.append(f"3.1: {str(e)}")
        print(f"  ❌ Failed Episode 3.1: {e}")
    
    # Episode 3.2: Mock Langfuse Client Pattern (JSON)
    try:
        episode_3_2_data = {
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
                "implementation": "Create MockLangfuseClient and MockLangfusePrompt classes"
            },
            "test_example": "with patch('langfuse.Langfuse', MockLangfuseClient): test_code_here()"
        }
        
        await client.add_episode(
            name="Mock Langfuse Client Pattern",
            episode_body=json.dumps(episode_3_2_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Mock Langfuse client patterns for testing",
            group_id=group_id
        )
        episodes_added.append("3.2 Mock Langfuse Client Pattern")
        print("  ✅ Added Episode 3.2: Mock Langfuse Client Pattern")
    except Exception as e:
        episodes_failed.append(f"3.2: {str(e)}")
        print(f"  ❌ Failed Episode 3.2: {e}")
    
    # Episode 3.3: Connection Troubleshooting (Text)
    try:
        episode_3_3_text = """Common Langfuse Connection Issues and Solutions:

1. Authentication Failures:
   Problem: 401 Unauthorized errors
   Solutions:
   - Verify keys in Langfuse dashboard
   - Check .env file is loaded: load_dotenv()
   - Regenerate keys if needed

2. Network Timeouts:
   Problem: Connection timeouts to Langfuse server
   Solutions:
   - Verify server is running: curl $LANGFUSE_HOST/health
   - Check Docker network if using containers
   - Use correct protocol (http vs https)

3. Graceful Degradation Strategy:
   Try Langfuse-wrapped client first, fall back to standard OpenAI, then HTTP requests
   Benefits: System continues working, no user-facing errors, logs issues

4. Cache Issues:
   Problem: Stale prompts after updates
   Solution: Clear cache or reduce TTL (LANGFUSE_CACHE_TTL_SECONDS=0 for testing)"""
        
        await client.add_episode(
            name="Langfuse Connection Troubleshooting",
            episode_body=episode_3_3_text,
            source=EpisodeType.text,
            reference_time=reference_time,
            source_description="Langfuse connection troubleshooting guide",
            group_id=group_id
        )
        episodes_added.append("3.3 Connection Troubleshooting")
        print("  ✅ Added Episode 3.3: Connection Troubleshooting")
    except Exception as e:
        episodes_failed.append(f"3.3: {str(e)}")
        print(f"  ❌ Failed Episode 3.3: {e}")
    
    # Category 4: Testing Patterns
    print("\n🧪 Adding Testing Patterns...")
    
    # Episode 4.1: Integration Test Structure (JSON)
    try:
        episode_4_1_data = {
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
            }
        }
        
        await client.add_episode(
            name="Langfuse Integration Test Structure",
            episode_body=json.dumps(episode_4_1_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Langfuse integration test structure patterns",
            group_id=group_id
        )
        episodes_added.append("4.1 Integration Test Structure")
        print("  ✅ Added Episode 4.1: Integration Test Structure")
    except Exception as e:
        episodes_failed.append(f"4.1: {str(e)}")
        print(f"  ❌ Failed Episode 4.1: {e}")
    
    # Episode 4.2: Coverage Strategy (JSON)
    try:
        episode_4_2_data = {
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
            }
        }
        
        await client.add_episode(
            name="Coverage Strategy for External Dependencies",
            episode_body=json.dumps(episode_4_2_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Test coverage strategies for Langfuse integration",
            group_id=group_id
        )
        episodes_added.append("4.2 Coverage Strategy")
        print("  ✅ Added Episode 4.2: Coverage Strategy")
    except Exception as e:
        episodes_failed.append(f"4.2: {str(e)}")
        print(f"  ❌ Failed Episode 4.2: {e}")
    
    # Episode 4.3: Import Pattern for Hyphenated Files (JSON)
    try:
        episode_4_3_data = {
            "problem": {
                "error": "ModuleNotFoundError: No module named 'gtd_review'",
                "cause": "Python cannot import files with hyphens in name",
                "affected_file": "gtd-review.py"
            },
            "solution": {
                "method": "Use importlib.util for dynamic import",
                "code": "spec = importlib.util.spec_from_file_location('gtd_review', 'gtd-review.py')"
            },
            "use_cases": [
                "Testing files with hyphens",
                "Dynamic module loading",
                "Working with legacy codebases"
            ]
        }
        
        await client.add_episode(
            name="Hyphenated Filename Import Pattern",
            episode_body=json.dumps(episode_4_3_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="Import pattern for files with hyphens",
            group_id=group_id
        )
        episodes_added.append("4.3 Hyphenated Filename Import")
        print("  ✅ Added Episode 4.3: Hyphenated Filename Import")
    except Exception as e:
        episodes_failed.append(f"4.3: {str(e)}")
        print(f"  ❌ Failed Episode 4.3: {e}")
    
    # Category 5: Operational Procedures
    print("\n📋 Adding Operational Procedures...")
    
    # Episode 5.1: Prompt Upload Procedure (Text)
    try:
        episode_5_1_text = """Step-by-Step Guide to Upload Prompts to Langfuse:

1. Prepare Prompt Files:
   - Create system-prompt-firm.txt (direct, time-focused tone)
   - Create system-prompt-gentle.txt (supportive, flexible tone)
   - Create system-prompt-fallback.txt (simplified for timeouts)

2. Create Upload Script:
   Use langfuse.create_prompt() with name, prompt content, labels, and config

3. Managing Variants:
   - Use labels to distinguish variants: ["firm"], ["gentle"]
   - Use "production" label for active versions
   - Use "staging" label for testing

4. Version Control Best Practices:
   - Keep prompt files in version control
   - Document changes in commit messages
   - Use semantic versioning for major changes

5. Testing New Prompts:
   - Upload with "staging" label first
   - Test with subset of users
   - Monitor performance metrics
   - Promote to "production" when validated

6. Rollback Procedure:
   - Keep previous versions in Langfuse
   - Change labels to revert
   - Monitor for improvements"""
        
        await client.add_episode(
            name="Prompt Upload to Langfuse Procedure",
            episode_body=episode_5_1_text,
            source=EpisodeType.text,
            reference_time=reference_time,
            source_description="Procedure for uploading prompts to Langfuse",
            group_id=group_id
        )
        episodes_added.append("5.1 Prompt Upload Procedure")
        print("  ✅ Added Episode 5.1: Prompt Upload Procedure")
    except Exception as e:
        episodes_failed.append(f"5.1: {str(e)}")
        print(f"  ❌ Failed Episode 5.1: {e}")
    
    # Episode 5.2: A/B Testing Analysis Workflow (JSON)
    try:
        episode_5_2_data = {
            "analysis_workflow": {
                "step_1_fetch_traces": {
                    "method": "langfuse.get_traces() or mock data",
                    "filters": "date_range, tags=['gtd-review']",
                    "output": "List of trace objects"
                },
                "step_2_extract_metrics": {
                    "latency": "Response time in seconds",
                    "success_rate": "Percentage of successful completions",
                    "completion_rate": "Phases completed / total phases",
                    "items_captured": "Mind sweep productivity metric"
                },
                "step_3_compare_variants": {
                    "script": "analyze_prompt_performance.py",
                    "statistics": ["mean", "median", "p95", "success_rate"]
                },
                "step_4_export_results": {
                    "format": "JSON",
                    "location": "analysis/prompt_analysis_YYYYMMDD.json"
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
        }
        
        await client.add_episode(
            name="A/B Testing Analysis Workflow",
            episode_body=json.dumps(episode_5_2_data),
            source=EpisodeType.json,
            reference_time=reference_time,
            source_description="A/B testing analysis workflow for prompts",
            group_id=group_id
        )
        episodes_added.append("5.2 A/B Testing Analysis Workflow")
        print("  ✅ Added Episode 5.2: A/B Testing Analysis Workflow")
    except Exception as e:
        episodes_failed.append(f"5.2: {str(e)}")
        print(f"  ❌ Failed Episode 5.2: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"✅ Successfully added: {len(episodes_added)} episodes")
    if episodes_added:
        for episode in episodes_added:
            print(f"   • {episode}")
    
    if episodes_failed:
        print(f"\n❌ Failed to add: {len(episodes_failed)} episodes")
        for failure in episodes_failed:
            print(f"   • {failure}")
    
    print("\n📚 Knowledge Categories Added:")
    print("   1. Trace Management Operations")
    print("   2. Implementation Details")
    print("   3. Troubleshooting Guide")
    print("   4. Testing Patterns")
    print("   5. Operational Procedures")
    
    print(f"\n🔍 Group ID: {group_id}")
    print("   Use this to search for all Langfuse-related knowledge")
    
    return len(episodes_added), len(episodes_failed)

if __name__ == "__main__":
    # Run the async function
    success, failed = asyncio.run(add_langfuse_knowledge_to_graphiti())
    
    if failed == 0:
        print("\n🎉 All episodes successfully added to Graphiti!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failed} episodes failed to add. Check errors above.")
        sys.exit(1)