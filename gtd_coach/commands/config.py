#!/usr/bin/env python3
"""
Configuration management commands
"""

import click
import os
import json
from pathlib import Path


@click.group()
def config_group():
    """Manage GTD Coach configuration"""
    pass


@config_group.command()
def show():
    """Show current configuration"""
    config_file = Path.home() / '.gtd-coach' / 'config.json'
    
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        
        click.echo("📋 Current Configuration:")
        click.echo(json.dumps(config, indent=2))
    else:
        click.echo("No custom configuration found. Using defaults.")
        click.echo("Run 'gtd config init' to create a configuration file.")


@config_group.command()
def init():
    """Initialize configuration file with defaults"""
    config_dir = Path.home() / '.gtd-coach'
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / 'config.json'
    
    if config_file.exists():
        if not click.confirm("Configuration file exists. Overwrite?"):
            return
    
    default_config = {
        'agent': {
            'enabled': False,
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
            'session_timeout': 1800,
            'auto_save': True
        },
        'paths': {
            'data_dir': str(Path.home() / 'gtd-coach' / 'data'),
            'log_dir': str(Path.home() / 'gtd-coach' / 'logs')
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    click.echo(f"✅ Configuration initialized at {config_file}")
    click.echo("   Edit this file to customize your settings.")


@config_group.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """
    Set a configuration value
    
    Examples:
        gtd config set agent.enabled true
        gtd config set agent.mode hybrid
        gtd config set features.timing_integration false
    """
    config_file = Path.home() / '.gtd-coach' / 'config.json'
    
    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {}
    
    # Parse the key path
    keys = key.split('.')
    current = config
    
    # Navigate to the nested key
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    # Set the value (with type conversion)
    final_key = keys[-1]
    if value.lower() in ['true', 'false']:
        current[final_key] = value.lower() == 'true'
    elif value.isdigit():
        current[final_key] = int(value)
    else:
        try:
            current[final_key] = float(value)
        except ValueError:
            current[final_key] = value
    
    # Save config
    config_file.parent.mkdir(exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"✅ Set {key} = {value}")


@config_group.command()
@click.argument('key')
def get(key):
    """
    Get a configuration value
    
    Examples:
        gtd config get agent.enabled
        gtd config get features.timing_integration
    """
    config_file = Path.home() / '.gtd-coach' / 'config.json'
    
    if not config_file.exists():
        click.echo("No configuration file found.", err=True)
        return
    
    with open(config_file) as f:
        config = json.load(f)
    
    # Parse the key path
    keys = key.split('.')
    current = config
    
    try:
        for k in keys:
            current = current[k]
        click.echo(f"{key} = {current}")
    except KeyError:
        click.echo(f"Key '{key}' not found", err=True)


@config_group.command()
def reset():
    """Reset configuration to defaults"""
    if click.confirm("This will reset all configuration. Continue?"):
        config_file = Path.home() / '.gtd-coach' / 'config.json'
        if config_file.exists():
            config_file.unlink()
            click.echo("✅ Configuration reset to defaults")
        else:
            click.echo("No configuration file to reset")


@config_group.command()
def env():
    """Show environment variables"""
    click.echo("🔧 Environment Variables:")
    
    env_vars = [
        ('GTD_USE_AGENT', 'Enable LangGraph agent'),
        ('GTD_AGENT_MODE', 'Agent mode (workflow/agent/hybrid)'),
        ('GTD_CONFIG', 'Path to config file'),
        ('GTD_DISABLE_TIMING', 'Disable Timing integration'),
        ('GTD_DISABLE_GRAPHITI', 'Disable Graphiti memory'),
        ('LM_STUDIO_URL', 'LM Studio API URL'),
        ('TIMING_API_KEY', 'Timing app API key'),
        ('NEO4J_PASSWORD', 'Neo4j password for Graphiti'),
        ('LANGFUSE_PUBLIC_KEY', 'Langfuse public key'),
        ('LANGFUSE_SECRET_KEY', 'Langfuse secret key'),
        ('LANGFUSE_HOST', 'Langfuse host URL')
    ]
    
    for var, description in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'PASSWORD' in var:
                display_value = value[:4] + '...' if len(value) > 4 else '***'
            else:
                display_value = value
            click.echo(f"  {var}={display_value}")
            click.echo(f"    {description}")
        else:
            click.echo(f"  {var}=<not set>")
            click.echo(f"    {description}")


if __name__ == '__main__':
    config_group()