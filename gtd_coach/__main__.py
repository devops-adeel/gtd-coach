#!/usr/bin/env python3
"""
GTD Coach CLI entry point.
Allows running the package with: python -m gtd_coach
"""

import sys
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Main CLI entry point with command routing"""
    
    parser = argparse.ArgumentParser(
        prog="gtd_coach",
        description="GTD Coach - ADHD-optimized weekly review system with LangGraph agent architecture"
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Default command: weekly review
    review_parser = subparsers.add_parser(
        "review",
        help="Run weekly GTD review (default)"
    )
    review_parser.add_argument("--resume", action="store_true", help="Resume interrupted session")
    review_parser.add_argument("--check-config", action="store_true", help="Check configuration")
    
    # Setup Timing projects
    setup_parser = subparsers.add_parser(
        "setup-timing",
        help="Setup Timing projects based on GTD structure"
    )
    setup_parser.add_argument(
        "--include-contexts",
        action="store_true",
        help="Also create GTD context projects"
    )
    
    # Daily alignment check
    daily_parser = subparsers.add_parser(
        "daily",
        help="Run daily GTD-Timing alignment check"
    )
    daily_parser.add_argument(
        "--notify",
        action="store_true",
        help="Show macOS notification"
    )
    daily_parser.add_argument(
        "--email",
        action="store_true",
        help="Send email report"
    )
    
    # Daily capture & clarify
    capture_parser = subparsers.add_parser(
        "capture",
        help="Interactive daily capture & clarify session"
    )
    capture_parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice capture with Whisper"
    )
    capture_parser.add_argument(
        "--skip-timing",
        action="store_true",
        help="Skip Timing app review"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to review if no command specified
    if not args.command:
        args.command = "review"
    
    # Route to appropriate command
    if args.command == "review":
        # Check for environment variable to use legacy coach
        import os
        if os.getenv("USE_LEGACY_COACH", "false").lower() == "true":
            # Use legacy coach if requested
            from gtd_coach.coach import main as coach_main
            sys.exit(coach_main())
        else:
            # Use new LangGraph agent by default
            from gtd_coach.agent.runner import run_weekly_review
            sys.exit(run_weekly_review(resume=args.resume))
    
    elif args.command == "setup-timing":
        # Import and run Timing setup
        from gtd_coach.commands.setup_timing import TimingProjectSetup
        setup = TimingProjectSetup()
        success = setup.run(include_contexts=args.include_contexts)
        sys.exit(0 if success else 1)
    
    elif args.command == "daily":
        # Import and run daily alignment
        from gtd_coach.commands.daily_alignment import DailyAlignmentChecker
        checker = DailyAlignmentChecker()
        asyncio.run(checker.run(notify=args.notify, email=args.email))
        sys.exit(0)
    
    elif args.command == "capture":
        # Import and run daily capture & clarify
        from gtd_coach.commands.daily_capture import DailyCaptureCoach
        coach = DailyCaptureCoach()
        asyncio.run(coach.run())
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()