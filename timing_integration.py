#!/usr/bin/env python3
"""
Timing App API Integration for GTD Coach
Fetches project time data from Timing web API
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
import json

class TimingAPI:
    """Client for Timing App Web API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Timing API client
        
        Args:
            api_key: Timing API key (or reads from TIMING_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('TIMING_API_KEY')
        self.base_url = "https://web.timingapp.com/api/v1"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    def fetch_projects_last_week(self, min_minutes: int = 30) -> List[Dict]:
        """Fetch projects with time spent in the last 7 days
        
        Args:
            min_minutes: Minimum time in minutes to include project (default: 30)
        
        Returns:
            List of project dictionaries with name and time_spent fields
        """
        if not self.is_configured():
            self.logger.warning("Timing API key not configured")
            return []
        
        try:
            # Calculate date range for last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Format dates for API
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Build API request for report
            params = {
                'start_date_min': start_str,
                'start_date_max': end_str,
                'columns[]': 'project',
                'include_project_data': 1
                # Removed timespan_grouping_mode as it's causing validation errors
            }
            
            self.logger.info(f"Fetching Timing data from {start_str} to {end_str}")
            
            # Make API request with timeout
            response = self.session.get(
                f"{self.base_url}/report",
                params=params,
                timeout=3.0  # 3 second timeout for time-sensitive app
            )
            
            # Check response status but don't raise immediately
            if response.status_code != 200:
                self.logger.error(f"API returned status {response.status_code}: {response.text[:500]}")
                response.raise_for_status()
            data = response.json()
            
            # Process response data
            projects = []
            min_seconds = min_minutes * 60
            
            for item in data.get('data', []):
                duration_seconds = item.get('duration', 0)
                
                # Skip projects under minimum threshold
                if duration_seconds < min_seconds:
                    continue
                
                # Extract project info
                project_info = item.get('project')
                if project_info is None:
                    continue  # Skip entries without project data
                project_name = project_info.get('title', 'Unknown Project')
                
                # Convert seconds to hours (rounded to 1 decimal)
                hours_spent = round(duration_seconds / 3600, 1)
                
                projects.append({
                    'name': project_name,
                    'time_spent': hours_spent,
                    'duration_seconds': duration_seconds  # Keep raw value for sorting
                })
            
            # Sort by time spent (descending)
            projects.sort(key=lambda x: x['duration_seconds'], reverse=True)
            
            # Remove raw duration from output
            for p in projects:
                del p['duration_seconds']
            
            self.logger.info(f"Fetched {len(projects)} projects with >{min_minutes} minutes")
            
            # Log if projects look auto-generated (for organization guidance)
            app_like_names = [p for p in projects if self._looks_like_app_name(p['name'])]
            if len(app_like_names) > len(projects) * 0.5:
                self.logger.info("Many projects appear to be auto-generated app names - consider organizing in Timing")
            
            return projects[:15]  # Limit to 15 projects max for review phase
            
        except requests.exceptions.Timeout:
            self.logger.error("Timing API request timed out (3s limit)")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Timing API request failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching Timing data: {e}")
            return []
    
    def _looks_like_app_name(self, name: str) -> bool:
        """Check if project name looks like an auto-generated app name"""
        app_indicators = [
            '.app', 'Safari', 'Chrome', 'Firefox', 'Mail', 'Messages',
            'Slack', 'Discord', 'Zoom', 'Terminal', 'iTerm', 'Code',
            'Xcode', 'Finder', 'System Preferences', 'Activity Monitor'
        ]
        return any(indicator in name for indicator in app_indicators)
    
    async def fetch_projects_async(self, min_minutes: int = 30) -> List[Dict]:
        """Async wrapper for fetch_projects_last_week"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_projects_last_week, min_minutes)


def get_mock_projects() -> List[Dict]:
    """Get mock project data for testing or when API unavailable"""
    return [
        {"name": "Email Processing", "time_spent": 5.2},
        {"name": "Project Alpha Development", "time_spent": 12.5},
        {"name": "Team Meetings", "time_spent": 8.3},
        {"name": "Documentation", "time_spent": 3.1},
        {"name": "Code Reviews", "time_spent": 6.7},
    ]


def format_project_list(projects: List[Dict]) -> str:
    """Format project list for display"""
    if not projects:
        return "No projects found with significant time last week"
    
    lines = []
    for i, project in enumerate(projects, 1):
        lines.append(f"{i}. {project['name']}: {project['time_spent']} hours")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the API integration
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create API client
    api = TimingAPI()
    
    if not api.is_configured():
        print("Error: TIMING_API_KEY not configured")
        print("Please set TIMING_API_KEY in .env file")
        sys.exit(1)
    
    print("Fetching projects from last week...")
    projects = api.fetch_projects_last_week()
    
    if projects:
        print(f"\nFound {len(projects)} projects with >30 minutes last week:\n")
        print(format_project_list(projects))
    else:
        print("No projects found or API request failed")
        print("Using mock data:")
        print(format_project_list(get_mock_projects()))