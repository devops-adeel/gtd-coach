#!/usr/bin/env python3
"""
Test commands for validating system components
"""

import click
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.group()
def test_group():
    """Test GTD Coach components"""
    pass


@test_group.command()
def llm():
    """Test LM Studio connection"""
    click.echo("🧪 Testing LM Studio connection...")
    
    try:
        import aiohttp
        
        async def test_connection():
            url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')
            
            async with aiohttp.ClientSession() as session:
                # Test models endpoint
                try:
                    async with session.get(f"{url}/models") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            click.echo(f"✅ Connected to LM Studio at {url}")
                            
                            if 'data' in data and data['data']:
                                click.echo("   Available models:")
                                for model in data['data']:
                                    click.echo(f"     • {model.get('id', 'unknown')}")
                            return True
                        else:
                            click.echo(f"❌ LM Studio returned status {resp.status}", err=True)
                            return False
                except aiohttp.ClientError as e:
                    click.echo(f"❌ Cannot connect to LM Studio: {e}", err=True)
                    click.echo(f"   Make sure LM Studio is running at {url}", err=True)
                    return False
        
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
        
    except ImportError:
        click.echo("❌ aiohttp not installed", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@test_group.command()
def timing():
    """Test Timing app API connection"""
    click.echo("🧪 Testing Timing API connection...")
    
    api_key = os.getenv('TIMING_API_KEY')
    if not api_key:
        click.echo("❌ TIMING_API_KEY not set", err=True)
        click.echo("   Get your API key from https://web.timingapp.com", err=True)
        sys.exit(1)
    
    try:
        from gtd_coach.integrations.timing import TimingAPI
        
        def test_api():
            timing = TimingAPI(api_key)
            
            # Test with a simple request
            try:
                projects = timing.fetch_projects_last_week()
                click.echo(f"✅ Connected to Timing API")
                click.echo(f"   Found {len(projects)} projects")
                
                # Show sample projects
                if projects:
                    click.echo("   Sample projects:")
                    for project in projects[:5]:
                        click.echo(f"     • {project.get('name', 'Unnamed')}")
                
                return True
            except Exception as e:
                click.echo(f"❌ API call failed: {e}", err=True)
                return False
        
        success = test_api()
        sys.exit(0 if success else 1)
        
    except ImportError as e:
        click.echo(f"❌ Import error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@test_group.command()
def graphiti():
    """Test Graphiti memory connection"""
    click.echo("🧪 Testing Graphiti connection...")
    
    # Check for Neo4j configuration
    if not os.getenv('NEO4J_PASSWORD'):
        click.echo("⚠️  NEO4J_PASSWORD not set", err=True)
        click.echo("   Graphiti memory will use JSON fallback", err=True)
        
        # Test JSON fallback
        data_dir = Path.home() / 'gtd-coach' / 'data' / 'memory_fallback'
        data_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = data_dir / 'test_connection.json'
        test_data = {
            'test': True,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            click.echo("✅ JSON fallback working")
            click.echo(f"   Data directory: {data_dir}")
            
            # Clean up
            test_file.unlink()
            
        except Exception as e:
            click.echo(f"❌ JSON fallback failed: {e}", err=True)
            sys.exit(1)
    else:
        try:
            from gtd_coach.integrations.graphiti import GraphitiMemory
            
            async def test_connection():
                memory = GraphitiMemory()
                
                if memory.is_configured():
                    try:
                        # Try a simple operation
                        result = await memory.search_nodes("test", max_nodes=1)
                        click.echo("✅ Connected to Graphiti/Neo4j")
                        return True
                    except Exception as e:
                        click.echo(f"❌ Graphiti query failed: {e}", err=True)
                        return False
                else:
                    click.echo("❌ Graphiti not properly configured", err=True)
                    return False
            
            success = asyncio.run(test_connection())
            sys.exit(0 if success else 1)
            
        except ImportError as e:
            click.echo(f"❌ Import error: {e}", err=True)
            sys.exit(1)


@test_group.command()
def langfuse():
    """Test Langfuse connection"""
    click.echo("🧪 Testing Langfuse connection...")
    
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    
    if not public_key or not secret_key:
        click.echo("⚠️  Langfuse keys not configured", err=True)
        click.echo("   Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY", err=True)
        click.echo("   Langfuse tracking is disabled", err=True)
        sys.exit(0)  # Not a failure, just disabled
    
    try:
        from langfuse import Langfuse
        
        # Initialize client
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        )
        
        # Test connection with a simple trace
        trace = langfuse.trace(
            name="test_connection",
            metadata={"test": True}
        )
        
        trace.update(output="Connection test successful")
        
        # Flush to ensure it's sent
        langfuse.flush()
        
        click.echo("✅ Connected to Langfuse")
        click.echo(f"   Host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
        
    except Exception as e:
        click.echo(f"❌ Langfuse connection failed: {e}", err=True)
        sys.exit(1)


@test_group.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def agent(verbose):
    """Test agent initialization and basic execution"""
    click.echo("🧪 Testing GTD Agent...")
    
    try:
        from gtd_coach.agent import GTDAgent
        
        # Test initialization
        click.echo("  Testing agent initialization...")
        agent = GTDAgent(test_mode=True)
        
        click.echo(f"  ✅ Agent initialized in {agent.mode} mode")
        
        # Check tools
        tools = agent.get_available_tools()
        click.echo(f"  ✅ {len(tools)} tools loaded")
        
        if verbose:
            click.echo("     Available tools:")
            for tool in tools[:10]:  # Show first 10
                click.echo(f"       • {tool}")
        
        # Get mode info
        info = agent.get_mode_info()
        click.echo(f"  ✅ Mode info retrieved")
        
        if verbose:
            click.echo(f"     Mode: {info['mode']}")
            click.echo(f"     Workflow: {info['workflow_type']}")
            click.echo(f"     Tools: {info['tools_available']}")
        
        # Test a minimal run
        click.echo("  Testing minimal execution...")
        
        async def test_run():
            # Create a very simple state that will complete quickly
            result = await agent.run(
                initial_state={'test_mode': True},
                session_config={'skip_timing': True}
            )
            return result
        
        result = asyncio.run(test_run())
        
        if result['success']:
            click.echo("  ✅ Agent execution successful")
            if verbose:
                click.echo(f"     Session ID: {result['session_id']}")
                click.echo(f"     Duration: {result.get('duration', 'N/A')} seconds")
        else:
            click.echo(f"  ❌ Agent execution failed: {result.get('error')}", err=True)
            sys.exit(1)
        
        click.echo("\n✅ All agent tests passed!")
        
    except ImportError as e:
        click.echo(f"❌ Import error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@test_group.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def all(verbose):
    """Run all component tests"""
    click.echo("🧪 Running all tests...\n")
    
    tests = ['llm', 'timing', 'graphiti', 'langfuse', 'agent']
    results = {}
    
    for test_name in tests:
        click.echo(f"Testing {test_name}...")
        
        # Get the command
        cmd = test_group.commands[test_name]
        
        # Create a context and invoke
        ctx = click.Context(cmd)
        if test_name == 'agent' and verbose:
            ctx.params = {'verbose': True}
        
        try:
            cmd.invoke(ctx)
            results[test_name] = "✅ Passed"
        except SystemExit as e:
            if e.code == 0:
                results[test_name] = "✅ Passed"
            else:
                results[test_name] = "❌ Failed"
        except Exception as e:
            results[test_name] = f"❌ Error: {e}"
        
        click.echo()  # Add spacing
    
    # Summary
    click.echo("=" * 40)
    click.echo("Test Summary:")
    for test_name, result in results.items():
        click.echo(f"  {test_name}: {result}")
    
    # Overall result
    if all("✅" in r for r in results.values()):
        click.echo("\n✅ All tests passed!")
        sys.exit(0)
    else:
        click.echo("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == '__main__':
    test_group()