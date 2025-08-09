#!/usr/bin/env python3
"""
Test script for Timing API integration
Run this to verify your API key and see what data will be fetched
"""

import sys
import os
from dotenv import load_dotenv
from timing_integration import TimingAPI, format_project_list, get_mock_projects

def main():
    print("="*50)
    print("TIMING API INTEGRATION TEST")
    print("="*50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if API key is configured
    api_key = os.getenv('TIMING_API_KEY')
    if not api_key:
        print("\n❌ TIMING_API_KEY not found in environment")
        print("\nTo set up:")
        print("1. Copy .env.example to .env")
        print("2. Get your API key from https://web.timingapp.com")
        print("3. Add the key to your .env file")
        print("\nShowing mock data instead:")
        print("-"*30)
        print(format_project_list(get_mock_projects()))
        return 1
    
    print(f"\n✓ API key configured (ends with ...{api_key[-4:]})")
    
    # Create API client
    api = TimingAPI()
    
    # Test fetching projects
    min_minutes = int(os.getenv('TIMING_MIN_MINUTES', '30'))
    print(f"\nFetching projects with >{min_minutes} minutes from last 7 days...")
    print("-"*30)
    
    try:
        projects = api.fetch_projects_last_week(min_minutes)
        
        if projects:
            print(f"\n✓ Successfully fetched {len(projects)} projects!\n")
            print(format_project_list(projects))
            
            # Check for auto-generated names
            app_names = ['Safari', 'Chrome', 'Mail', 'Slack', 'Terminal', 'Code', '.app']
            auto_generated = [p for p in projects 
                            if any(app in p['name'] for app in app_names)]
            
            if auto_generated:
                print(f"\n⚠️  {len(auto_generated)} projects look like auto-generated app names:")
                for p in auto_generated[:5]:  # Show first 5
                    print(f"   - {p['name']}")
                print("\nConsider organizing these in Timing for better GTD reviews!")
        else:
            print("\n⚠️  No projects found with significant time")
            print("This could mean:")
            print("- No projects had >{} minutes last week".format(min_minutes))
            print("- API request failed (check your API key)")
            print("- Network issue")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your API key is correct")
        print("2. Check you have Timing Connect subscription")
        print("3. Ensure you're connected to the internet")
        return 1
    
    print("\n" + "="*50)
    print("Test complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())