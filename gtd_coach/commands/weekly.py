#!/usr/bin/env python3
"""
Weekly review command with agent support
"""

import asyncio
import click
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.command()
@click.option('--use-agent', is_flag=True, default=False,
              help='Use new LangGraph agent (when implemented)')
@click.option('--skip-timing', is_flag=True, default=False,
              help='Skip Timing app review')
def weekly_review(use_agent, skip_timing):
    """
    Run GTD weekly review session
    
    A structured 30-minute review of your GTD system with:
      • Mind sweep capture
      • Project review
      • Priority setting
      • Weekly insights
    
    Note: Agent-based weekly review is not yet implemented.
    """
    
    # Check if agent mode is requested
    if use_agent or os.getenv('GTD_USE_AGENT', '').lower() == 'true':
        click.echo("⚠️  Agent-based weekly review not yet implemented")
        click.echo("   Falling back to legacy weekly review...")
        use_agent = False
    
    # Import legacy weekly review
    try:
        from gtd_coach.gtd_review import GTDCoach
        
        click.echo("🗓️  Starting Weekly Review")
        click.echo("=" * 40)
        
        coach = GTDCoach()
        coach.run_review()
        
    except ImportError:
        click.echo("❌ Legacy weekly review not found", err=True)
        click.echo("   Please check your installation", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n🛑 Review interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ Error during review: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    weekly_review()