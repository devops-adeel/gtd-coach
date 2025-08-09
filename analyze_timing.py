#!/usr/bin/env python3
"""
Analyze Timing App Data for GTD Alignment
Simple, ADHD-friendly analysis with actionable recommendations
"""

import os
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from timing_integration import TimingAPI

def analyze_project_patterns(projects):
    """Analyze projects to identify patterns and suggest groupings"""
    
    # Categories for auto-detection
    work_keywords = ['gtm', 'strategy', 'aws', 'bedrock', 'factory', 'teams', 'outlook', 
                     'slack', 'meeting', 'review', 'presentation', 'report']
    arabic_keywords = ['arabic', 'duolingo', 'nahw', 'sarf', 'tasheel', 'vocab']
    dev_keywords = ['claude', 'code', 'github', 'python', 'javascript', 'docker', 'orbstack']
    
    # Categorize projects
    categorized = {
        'Work Projects': [],
        'Arabic Learning': [],
        'Development': [],
        'Communication': [],
        'Auto-Generated Apps': [],
        'Other': []
    }
    
    for project in projects:
        name_lower = project['name'].lower()
        
        # Check for auto-generated app names
        if any(app in project['name'] for app in ['.app', 'Safari', 'Chrome', 'Mail', 
                                                   'Messages', 'Slack', 'Terminal', 'Finder']):
            categorized['Auto-Generated Apps'].append(project)
        # Check for work projects
        elif any(keyword in name_lower for keyword in work_keywords):
            categorized['Work Projects'].append(project)
        # Check for Arabic learning
        elif any(keyword in name_lower for keyword in arabic_keywords):
            categorized['Arabic Learning'].append(project)
        # Check for development
        elif any(keyword in name_lower for keyword in dev_keywords):
            categorized['Development'].append(project)
        # Communication apps
        elif any(comm in name_lower for comm in ['mail', 'message', 'slack', 'teams', 'zoom']):
            categorized['Communication'].append(project)
        else:
            categorized['Other'].append(project)
    
    return categorized

def suggest_simple_structure(categorized, total_hours):
    """Suggest a simple 5-project structure for ADHD-friendly organization"""
    
    print("\n" + "="*60)
    print("📊 TIMING DATA ANALYSIS")
    print("="*60)
    
    # Show current state
    print(f"\n📈 Last Week Summary:")
    print(f"   Total tracked time: {total_hours:.1f} hours")
    print(f"   Projects/Apps tracked: {sum(len(v) for v in categorized.values())}")
    
    # Show breakdown by category
    print("\n📁 Current Organization:")
    for category, items in categorized.items():
        if items:
            hours = sum(p['time_spent'] for p in items)
            print(f"\n   {category}: {hours:.1f} hours ({len(items)} items)")
            for item in items[:3]:  # Show top 3
                print(f"      • {item['name']}: {item['time_spent']}h")
            if len(items) > 3:
                print(f"      ... and {len(items)-3} more")
    
    # Suggest simple structure
    print("\n" + "="*60)
    print("✨ RECOMMENDED SIMPLE STRUCTURE (5 Projects)")
    print("="*60)
    
    suggestions = []
    
    # Calculate what should go into each project
    work_hours = sum(p['time_spent'] for p in categorized['Work Projects'] + 
                    [p for p in categorized['Auto-Generated Apps'] 
                     if any(w in p['name'].lower() for w in ['teams', 'outlook', 'slack'])])
    
    arabic_hours = sum(p['time_spent'] for p in categorized['Arabic Learning'] +
                      [p for p in categorized['Auto-Generated Apps']
                       if 'duolingo' in p['name'].lower()])
    
    dev_hours = sum(p['time_spent'] for p in categorized['Development'] +
                   [p for p in categorized['Auto-Generated Apps']
                    if any(d in p['name'].lower() for d in ['code', 'github', 'terminal'])])
    
    suggestions.append({
        'name': '1. GTM Strategy Work',
        'current_hours': work_hours * 0.5,  # Estimate half of work time
        'includes': ['Slack channels', 'Google Docs', 'Teams meetings', 'Strategy documents']
    })
    
    suggestions.append({
        'name': '2. AI Factory Work',
        'current_hours': work_hours * 0.5,  # Other half of work time
        'includes': ['AWS Console', 'Bedrock docs', 'Terminal/Ghostty', 'Claude for coding']
    })
    
    suggestions.append({
        'name': '3. Arabic Learning',
        'current_hours': arabic_hours,
        'includes': ['Duolingo', 'LMStudio for Arabic', 'Arabic websites', 'Study materials']
    })
    
    suggestions.append({
        'name': '4. Claude Development',
        'current_hours': dev_hours,
        'includes': ['Claude.ai', 'VS Code', 'GitHub', 'OrbStack', 'AI Tutor project']
    })
    
    suggestions.append({
        'name': '5. Other/Admin',
        'current_hours': total_hours - sum(s['current_hours'] for s in suggestions[:4]),
        'includes': ['Email', 'General browsing', 'System maintenance', 'Everything else']
    })
    
    # Print suggestions
    for s in suggestions:
        print(f"\n📌 {s['name']}")
        print(f"   Estimated time last week: {s['current_hours']:.1f} hours")
        print(f"   Would include:")
        for item in s['includes']:
            print(f"      • {item}")
    
    return suggestions

def generate_quick_rules(categorized):
    """Generate simple rules for the most obvious categorizations"""
    
    print("\n" + "="*60)
    print("⚡ QUICK WIN RULES (2 minutes to set up)")
    print("="*60)
    
    print("\nIn Timing, ⌥-drag these activities to projects:")
    
    # Find the most obvious rules
    rules = []
    
    # Duolingo → Arabic
    duolingo = [p for p in categorized['Auto-Generated Apps'] if 'duolingo' in p['name'].lower()]
    if duolingo:
        rules.append("• Duolingo → Arabic Learning")
    
    # Teams/Outlook → Work
    work_apps = [p for p in categorized['Auto-Generated Apps'] 
                 if any(w in p['name'].lower() for w in ['teams', 'outlook'])]
    if work_apps:
        rules.append("• Microsoft Teams → GTM Strategy Work")
        rules.append("• Outlook → GTM Strategy Work")
    
    # Terminal with Arabic keywords → Arabic
    rules.append("• Terminal windows with 'arabic' in title → Arabic Learning")
    
    # AWS Console → AI Factory
    rules.append("• AWS Console browser tabs → AI Factory Work")
    
    # Claude.ai → Depends on context
    rules.append("• Claude.ai → Use ⌃⌥⌘P to manually select project")
    
    for rule in rules[:5]:  # Show top 5 quick wins
        print(rule)
    
    print("\n💡 Pro tip: Start with just these 5 rules. Add more as you notice patterns.")

def show_adhd_tips():
    """Show ADHD-specific tips for using Timing effectively"""
    
    print("\n" + "="*60)
    print("🧠 ADHD-OPTIMIZED WORKFLOW")
    print("="*60)
    
    tips = [
        "1. Set up ONE keyboard shortcut: ⌃⌥⌘P to switch projects",
        "2. Review time once per week during GTD review (not daily)",
        "3. Use the 'Other/Admin' project liberally - don't stress about perfect categorization",
        "4. If you forget to categorize for a few days, that's OK - batch process during weekly review",
        "5. Focus on patterns, not precision - 80% accurate is perfect"
    ]
    
    for tip in tips:
        print(f"\n✓ {tip}")
    
    print("\n🎯 Remember: Timing already tracks automatically.")
    print("   Your only job is occasional project switching when you remember.")
    print("   The system works even if you forget!")

def main():
    """Main analysis function"""
    
    print("\n" + "="*60)
    print("🔍 TIMING DATA ANALYZER FOR GTD")
    print("Simple • ADHD-Friendly • Actionable")
    print("="*60)
    
    # Load environment
    load_dotenv()
    
    # Check API configuration
    api_key = os.getenv('TIMING_API_KEY')
    if not api_key:
        print("\n❌ No API key found. Please set TIMING_API_KEY in .env file")
        return 1
    
    print(f"\n✓ API key configured")
    
    # Fetch data
    api = TimingAPI()
    print("\nFetching your Timing data from last 7 days...")
    
    try:
        # Get all projects (even small ones) for analysis
        projects = api.fetch_projects_last_week(min_minutes=5)  # Lower threshold for analysis
        
        if not projects:
            print("\n⚠️  No projects found. Using sample data for demonstration...")
            # Use sample data
            projects = [
                {"name": "Web Browsing", "time_spent": 10.9},
                {"name": "Communication", "time_spent": 8.6},
                {"name": "Ghostty", "time_spent": 5.2},
                {"name": "Claude.ai", "time_spent": 4.8},
                {"name": "Duolingo", "time_spent": 2.1},
                {"name": "Microsoft Teams", "time_spent": 3.4}
            ]
        
        # Calculate total hours
        total_hours = sum(p['time_spent'] for p in projects)
        
        # Analyze patterns
        categorized = analyze_project_patterns(projects)
        
        # Suggest simple structure
        suggestions = suggest_simple_structure(categorized, total_hours)
        
        # Generate quick rules
        generate_quick_rules(categorized)
        
        # Show ADHD tips
        show_adhd_tips()
        
        # Save analysis for GTD review integration
        analysis_data = {
            'timestamp': datetime.now().isoformat(),
            'total_hours': total_hours,
            'suggested_projects': [s['name'] for s in suggestions],
            'estimated_hours': {s['name']: s['current_hours'] for s in suggestions}
        }
        
        with open('data/timing_analysis.json', 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE")
        print("="*60)
        print("\n📝 Next steps:")
        print("   1. Open Timing app")
        print("   2. Create the 5 projects listed above")
        print("   3. Set up the quick win rules (⌥-drag)")
        print("   4. Start your next GTD review to see the integration!")
        
    except Exception as e:
        print(f"\n❌ Error analyzing data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())