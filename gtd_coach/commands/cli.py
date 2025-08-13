#!/usr/bin/env python3
"""
Main CLI entry point for GTD Coach
Provides feature flags and configuration for agent-based system
"""

import click
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Import commands
from .daily import daily_capture, resume
from .weekly import weekly_review
from .config import config_group
from .test import test_group


@click.group()
@click.option('--config', type=click.Path(), default=None,
              help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """
    GTD Coach - ADHD-optimized Getting Things Done system
    
    A command-line tool for structured GTD workflows with LangGraph agents.
    
    Features:
      • Daily capture & clarify sessions
      • Weekly reviews with time boxing
      • ADHD pattern detection and interventions
      • Integration with Timing app for focus metrics
      • Graphiti memory for pattern recognition
      • Langfuse observability for performance tracking
    
    Configuration:
      Set GTD_USE_AGENT=true to enable the new LangGraph agent system
      Set GTD_CONFIG=/path/to/config.json for custom configuration
    """
    
    # Load configuration
    ctx.ensure_object(dict)
    
    # Check for config file
    config_path = config or os.getenv('GTD_CONFIG')
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            ctx.obj['config'] = json.load(f)
    else:
        ctx.obj['config'] = _get_default_config()
    
    # Apply environment overrides
    _apply_env_overrides(ctx.obj['config'])


def _get_default_config():
    """Get default configuration"""
    return {
        'agent': {
            'enabled': False,  # Default to legacy for backwards compatibility
            'mode': 'hybrid',
            'llm': {
                'url': 'http://localhost:1234/v1',
                'model': 'meta-llama-3.1-8b-instruct',
                'temperature': 0.7,
                'max_tokens': 500
            }
        },
        'features': {
            'timing_integration': True,
            'graphiti_memory': True,
            'langfuse_tracking': False,
            'adhd_interventions': True
        },
        'behavior': {
            'default_accountability': 'adaptive',
            'session_timeout': 1800,  # 30 minutes
            'auto_save': True
        },
        'paths': {
            'data_dir': str(Path.home() / 'gtd-coach' / 'data'),
            'log_dir': str(Path.home() / 'gtd-coach' / 'logs')
        }
    }


def _apply_env_overrides(config):
    """Apply environment variable overrides to config"""
    
    # Agent settings
    if os.getenv('GTD_USE_AGENT'):
        config['agent']['enabled'] = os.getenv('GTD_USE_AGENT', '').lower() == 'true'
    
    if os.getenv('GTD_AGENT_MODE'):
        config['agent']['mode'] = os.getenv('GTD_AGENT_MODE')
    
    # Feature flags
    if os.getenv('GTD_DISABLE_TIMING'):
        config['features']['timing_integration'] = False
    
    if os.getenv('GTD_DISABLE_GRAPHITI'):
        config['features']['graphiti_memory'] = False
    
    if os.getenv('LANGFUSE_PUBLIC_KEY'):
        config['features']['langfuse_tracking'] = True
    
    # LLM settings
    if os.getenv('LM_STUDIO_URL'):
        config['agent']['llm']['url'] = os.getenv('LM_STUDIO_URL')


# Register commands
cli.add_command(daily_capture, name='daily')
cli.add_command(resume, name='resume')
cli.add_command(weekly_review, name='weekly')
cli.add_command(config_group, name='config')
cli.add_command(test_group, name='test')


@cli.command()
@click.pass_context
def status(ctx):
    """
    Show current configuration and system status
    """
    config = ctx.obj['config']
    
    click.echo("🔍 GTD Coach Status")
    click.echo("=" * 40)
    
    # Agent status
    agent_status = "✅ Enabled" if config['agent']['enabled'] else "⏸️  Disabled (Legacy Mode)"
    click.echo(f"Agent System: {agent_status}")
    if config['agent']['enabled']:
        click.echo(f"  Mode: {config['agent']['mode']}")
    
    # Feature status
    click.echo("\nFeatures:")
    features = config['features']
    
    if features['timing_integration']:
        has_key = bool(os.getenv('TIMING_API_KEY'))
        status = "✅" if has_key else "⚠️  (No API key)"
        click.echo(f"  Timing Integration: {status}")
    else:
        click.echo("  Timing Integration: ⏸️  Disabled")
    
    if features['graphiti_memory']:
        has_neo4j = bool(os.getenv('NEO4J_PASSWORD'))
        status = "✅" if has_neo4j else "⚠️  (Not configured)"
        click.echo(f"  Graphiti Memory: {status}")
    else:
        click.echo("  Graphiti Memory: ⏸️  Disabled")
    
    if features['langfuse_tracking']:
        click.echo("  Langfuse Tracking: ✅")
    else:
        click.echo("  Langfuse Tracking: ⏸️  Disabled")
    
    if features['adhd_interventions']:
        click.echo("  ADHD Interventions: ✅")
    else:
        click.echo("  ADHD Interventions: ⏸️  Disabled")
    
    # LLM status
    click.echo("\nLLM Configuration:")
    click.echo(f"  URL: {config['agent']['llm']['url']}")
    click.echo(f"  Model: {config['agent']['llm']['model']}")
    
    # Data paths
    click.echo("\nData Paths:")
    click.echo(f"  Data: {config['paths']['data_dir']}")
    click.echo(f"  Logs: {config['paths']['log_dir']}")
    
    # Last session info
    session_file = Path.home() / '.gtd-coach' / 'last_session.txt'
    if session_file.exists():
        session_id = session_file.read_text().strip()
        click.echo(f"\nLast Session: {session_id}")


@cli.command()
@click.option('--enable-agent', is_flag=True, help='Enable LangGraph agent')
@click.option('--disable-agent', is_flag=True, help='Use legacy workflow')
@click.option('--mode', type=click.Choice(['workflow', 'agent', 'hybrid']),
              help='Set agent mode')
@click.pass_context
def toggle(ctx, enable_agent, disable_agent, mode):
    """
    Toggle features and save preferences
    """
    
    config_dir = Path.home() / '.gtd-coach'
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / 'config.json'
    
    # Load existing config or use defaults
    if config_file.exists():
        with open(config_file) as f:
            saved_config = json.load(f)
    else:
        saved_config = _get_default_config()
    
    # Apply changes
    changed = False
    
    if enable_agent:
        saved_config['agent']['enabled'] = True
        click.echo("✅ LangGraph agent enabled")
        changed = True
    
    if disable_agent:
        saved_config['agent']['enabled'] = False
        click.echo("⏸️  Switched to legacy workflow")
        changed = True
    
    if mode:
        saved_config['agent']['mode'] = mode
        click.echo(f"🔄 Agent mode set to: {mode}")
        changed = True
    
    # Save if changed
    if changed:
        with open(config_file, 'w') as f:
            json.dump(saved_config, f, indent=2)
        click.echo(f"💾 Configuration saved to {config_file}")
    else:
        click.echo("No changes made")


@cli.command()
def version():
    """Show version information"""
    click.echo("GTD Coach v2.0.0-agent")
    click.echo("LangGraph Agent: Enabled")
    click.echo("Python: " + sys.version.split()[0])


if __name__ == '__main__':
    cli()