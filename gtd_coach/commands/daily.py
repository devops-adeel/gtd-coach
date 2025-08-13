#!/usr/bin/env python3
"""
Daily capture command with LangGraph agent support
Provides feature flags for transitioning from legacy to agent-based system
"""

import asyncio
import click
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.agent import create_daily_capture_agent
from gtd_coach.commands.daily_capture_legacy import DailyCaptureReview  # Legacy implementation

logger = logging.getLogger(__name__)


@click.command()
@click.option('--use-agent', is_flag=True, default=False,
              help='Use new LangGraph agent instead of legacy workflow')
@click.option('--agent-mode', type=click.Choice(['workflow', 'agent', 'hybrid']), 
              default='hybrid',
              help='Agent mode: workflow (structured), agent (flexible), or hybrid')
@click.option('--skip-timing', is_flag=True, default=False,
              help='Skip Timing app review')
@click.option('--accountability', type=click.Choice(['gentle', 'firm', 'adaptive']),
              default='adaptive',
              help='Coaching accountability style')
@click.option('--test-mode', is_flag=True, default=False,
              help='Run in test mode with mocked APIs')
@click.option('--resume', type=str, default=None,
              help='Resume a previous session by ID')
@click.option('--user-id', type=str, default=None,
              help='User identifier for personalization')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Verbose output')
def daily_capture(use_agent, agent_mode, skip_timing, accountability, 
                 test_mode, resume, user_id, verbose):
    """
    Run daily capture & clarify session
    
    This command helps you capture everything on your mind and clarify it
    into actionable items using GTD methodology.
    
    Examples:
        # Run with legacy workflow (current default)
        gtd daily
        
        # Run with new LangGraph agent
        gtd daily --use-agent
        
        # Run agent in pure workflow mode (no AI decisions)
        gtd daily --use-agent --agent-mode workflow
        
        # Run with firm accountability
        gtd daily --use-agent --accountability firm
        
        # Resume an interrupted session
        gtd daily --use-agent --resume session_20250101_100000
    """
    
    # Setup logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Feature flag check from environment
    if not use_agent:
        use_agent = os.getenv('GTD_USE_AGENT', 'false').lower() == 'true'
    
    if use_agent:
        click.echo("🚀 Starting Daily Capture with LangGraph Agent")
        click.echo(f"   Mode: {agent_mode}")
        click.echo(f"   Accountability: {accountability}")
        
        # Run the agent-based version
        asyncio.run(_run_agent_capture(
            agent_mode=agent_mode,
            skip_timing=skip_timing,
            accountability=accountability,
            test_mode=test_mode,
            resume_session=resume,
            user_id=user_id
        ))
    else:
        click.echo("📝 Starting Daily Capture (Legacy Mode)")
        
        # Run the legacy version
        try:
            review = DailyCaptureReview()
            asyncio.run(review.run())
        except KeyboardInterrupt:
            click.echo("\n\n🛑 Session interrupted by user")
            sys.exit(0)
        except Exception as e:
            click.echo(f"\n❌ Error: {e}", err=True)
            sys.exit(1)


async def _run_agent_capture(agent_mode, skip_timing, accountability, 
                            test_mode, resume_session, user_id):
    """Run the agent-based daily capture"""
    
    try:
        # Create the agent
        agent = create_daily_capture_agent(
            mode=agent_mode,
            test_mode=test_mode
        )
        
        if resume_session:
            # Resume an existing session
            click.echo(f"📂 Resuming session: {resume_session}")
            result = await agent.resume(resume_session)
        else:
            # Start new session
            # Prepare initial state
            initial_state = {}
            if user_id:
                initial_state['user_id'] = user_id
            
            # Session configuration
            session_config = {
                'accountability_mode': accountability,
                'skip_timing': skip_timing
            }
            
            # Run the agent
            result = await agent.run(
                initial_state=initial_state,
                session_config=session_config
            )
        
        # Display results
        if result['success']:
            click.echo("\n✅ Daily Capture Complete!")
            
            # Show summary
            summary = result.get('summary', {})
            click.echo(f"\n📊 Session Summary:")
            click.echo(f"   • Captured: {summary.get('captures', 0)} items")
            click.echo(f"   • Processed: {summary.get('processed', 0)} actions")
            click.echo(f"   • Projects: {summary.get('projects', 0)} created")
            
            if summary.get('focus_score'):
                click.echo(f"   • Focus Score: {summary['focus_score']}/100")
            
            if summary.get('patterns_detected'):
                click.echo(f"   • Patterns: {', '.join(summary['patterns_detected'])}")
            
            click.echo(f"\n⏱️  Duration: {result['duration']:.1f} seconds")
            
            # Save session ID for potential resume
            session_file = Path.home() / '.gtd-coach' / 'last_session.txt'
            session_file.parent.mkdir(exist_ok=True)
            session_file.write_text(result['session_id'])
            
        else:
            click.echo(f"\n❌ Session failed: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n\n🛑 Session interrupted")
        click.echo("💡 Tip: Use --resume to continue later")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        if test_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@click.command()
@click.option('--last', is_flag=True, default=False,
              help='Resume the last session')
def resume(last):
    """
    Resume an interrupted daily capture session
    
    Examples:
        # Resume last session
        gtd resume --last
        
        # Resume specific session
        gtd daily --resume session_20250101_100000
    """
    
    if last:
        # Get last session ID
        session_file = Path.home() / '.gtd-coach' / 'last_session.txt'
        if not session_file.exists():
            click.echo("❌ No previous session found", err=True)
            sys.exit(1)
        
        session_id = session_file.read_text().strip()
        click.echo(f"📂 Resuming last session: {session_id}")
        
        # Run with resume
        asyncio.run(_run_agent_capture(
            agent_mode='hybrid',
            skip_timing=False,
            accountability='adaptive',
            test_mode=False,
            resume_session=session_id,
            user_id=None
        ))
    else:
        click.echo("Please specify --last or use 'gtd daily --resume SESSION_ID'")


if __name__ == '__main__':
    daily_capture()