#!/usr/bin/env python3
"""
Setup environment file with API keys
Run this to create your .env file with the provided API keys
"""

import os
from pathlib import Path

def create_env_file():
    """Create .env template file for user's API keys"""
    
    # Get API keys from environment or prompt user
    timing_key = os.environ.get('TIMING_API_KEY', '')
    todoist_key = os.environ.get('TODOIST_API_KEY', '')
    
    if not timing_key:
        print("⚠️  TIMING_API_KEY not found in environment")
        print("   Get your API key from https://web.timingapp.com")
        timing_key = input("Enter your Timing API key (or press Enter to skip): ").strip() or "YOUR_TIMING_API_KEY_HERE"
    
    if not todoist_key:
        print("⚠️  TODOIST_API_KEY not found in environment")
        print("   Get your API key from https://todoist.com/app/settings/integrations")
        todoist_key = input("Enter your Todoist API key (or press Enter to skip): ").strip() or "YOUR_TODOIST_API_KEY_HERE"
    
    env_content = f"""# ============================================
# GTD Coach Configuration
# ============================================
# IMPORTANT: Never commit this file to version control!
# Add .env to your .gitignore file

# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234/v1

# ============================================
# Todoist Integration
# ============================================
# Get your API key from https://todoist.com/app/settings/integrations
TODOIST_API_KEY={todoist_key}

# ============================================
# Timing App API Configuration  
# ============================================
# Get your API key from https://web.timingapp.com
# Requires Timing Connect subscription
TIMING_API_KEY={timing_key}

# Minimum time threshold in minutes
TIMING_MIN_MINUTES=5

# ============================================
# Daily Alignment Settings
# ============================================
ENABLE_DAILY_ALIGNMENT=true
DAILY_ALIGNMENT_TIME=09:00
DAILY_ALIGNMENT_NOTIFY=true

# ============================================
# Coach Behavior Settings
# ============================================
COACHING_STYLE=firm
SESSION_TIMEOUT_MINUTES=45
ENABLE_AUDIO_ALERTS=true

# ============================================
# Optional: Langfuse Configuration (if you have it)
# ============================================
# LANGFUSE_PUBLIC_KEY=
# LANGFUSE_SECRET_KEY=
# LANGFUSE_HOST=https://cloud.langfuse.com

# ============================================
# Optional: Graphiti Memory (if you have Neo4j)
# ============================================
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=
"""
    
    env_path = Path(__file__).parent / ".env"
    
    if env_path.exists():
        print(f"⚠️  .env file already exists at {env_path}")
        response = input("Do you want to overwrite it? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env file at {env_path}")
    print("   Your API keys have been configured.")
    return True

if __name__ == "__main__":
    create_env_file()