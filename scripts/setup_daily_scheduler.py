#!/usr/bin/env python3
"""
Setup daily scheduler for GTD Coach capture sessions
Creates launchd plist for macOS or cron job for Linux
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import time


def create_launchd_plist(hour: int = 9, minute: int = 0) -> bool:
    """Create launchd plist for macOS
    
    Args:
        hour: Hour to run (24-hour format)
        minute: Minute to run
    
    Returns:
        True if successful
    """
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gtdcoach.dailycapture</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>gtd_coach</string>
        <string>capture</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{Path.home() / 'gtd-coach'}</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{Path.home() / 'gtd-coach' / 'logs' / 'daily_capture.log'}</string>
    
    <key>StandardErrorPath</key>
    <string>{Path.home() / 'gtd-coach' / 'logs' / 'daily_capture_error.log'}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>"""
    
    # Create plist file
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.gtdcoach.dailycapture.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        
        # Load the launch agent
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_path)], check=True)
        
        print(f"✅ Daily capture scheduled for {hour:02d}:{minute:02d}")
        print(f"   Plist created at: {plist_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create launchd agent: {e}")
        return False


def create_cron_job(hour: int = 9, minute: int = 0) -> bool:
    """Create cron job for Linux
    
    Args:
        hour: Hour to run (24-hour format)
        minute: Minute to run
    
    Returns:
        True if successful
    """
    cron_line = f"{minute} {hour} * * * cd {Path.home() / 'gtd-coach'} && {sys.executable} -m gtd_coach capture >> logs/daily_capture.log 2>&1"
    
    try:
        # Get current crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # Check if already exists
        if "gtd_coach capture" in current_cron:
            print("⚠️  Daily capture job already exists in crontab")
            return True
        
        # Add new cron job
        new_cron = current_cron + "\n" + cron_line + "\n"
        
        # Write back to crontab
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)
        
        if process.returncode == 0:
            print(f"✅ Daily capture scheduled for {hour:02d}:{minute:02d}")
            print(f"   Cron job added: {cron_line}")
            return True
        else:
            print("❌ Failed to add cron job")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create cron job: {e}")
        return False


def setup_terminal_notification():
    """Setup terminal notification for interactive session"""
    print("\n📱 Setting up terminal notification...")
    print("   Since the capture session is interactive, you'll need a way to be notified.")
    print("\n   Options:")
    print("   1. Use terminal-notifier (macOS): brew install terminal-notifier")
    print("   2. Use notify-send (Linux): apt-get install libnotify-bin")
    print("   3. Keep a terminal window open with the session")
    print("\n   The daily capture will launch in your default terminal.")


def main():
    """Main setup function"""
    print("🗓️  GTD Coach Daily Capture Scheduler Setup")
    print("=" * 50)
    
    # Get desired time
    print("\n⏰ When would you like your daily capture session?")
    print("   (After your school run, recommended 9:00 AM)")
    
    time_input = input("\nEnter time (HH:MM, default 09:00): ").strip() or "09:00"
    
    try:
        hour, minute = map(int, time_input.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time")
    except:
        print("❌ Invalid time format. Using default 09:00")
        hour, minute = 9, 0
    
    # Detect platform and setup
    system = platform.system()
    
    if system == "Darwin":  # macOS
        print(f"\n🍎 Detected macOS. Setting up launchd agent...")
        success = create_launchd_plist(hour, minute)
    elif system == "Linux":
        print(f"\n🐧 Detected Linux. Setting up cron job...")
        success = create_cron_job(hour, minute)
    else:
        print(f"❌ Unsupported platform: {system}")
        print("   Please set up scheduling manually.")
        success = False
    
    if success:
        setup_terminal_notification()
        
        print("\n✅ Daily capture scheduling complete!")
        print("\n📝 Next steps:")
        print("   1. Ensure GTD Coach is properly configured (.env file)")
        print("   2. Test with: python -m gtd_coach capture")
        print("   3. The session will run automatically at the scheduled time")
        
        # Proactive reminders
        print("\n🔔 Proactive Features Available:")
        print("   • Morning check-in after scheduled time")
        print("   • End-of-day wrap-up reminder")
        print("   • Weekend review prompt")
        print("\n   Configure these in ~/.gtd-coach/settings.json")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())