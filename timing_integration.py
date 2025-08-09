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
    
    def fetch_time_entries_last_week(self, max_entries: int = 100) -> List[Dict]:
        """Fetch individual time entries from the last 7 days
        
        Args:
            max_entries: Maximum number of entries to fetch (default: 100)
        
        Returns:
            List of time entry dictionaries with project, start_time, duration
        """
        if not self.is_configured():
            self.logger.warning("Timing API key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            params = {
                'start_date_min': start_date.strftime("%Y-%m-%d"),
                'start_date_max': end_date.strftime("%Y-%m-%d"),
                'limit': max_entries,
                'sort': 'start_date',
                'sort_direction': 'desc'
            }
            
            self.logger.info(f"Fetching individual time entries from last 7 days")
            
            response = self.session.get(
                f"{self.base_url}/time-entries",
                params=params,
                timeout=3.0
            )
            
            if response.status_code != 200:
                self.logger.error(f"API returned status {response.status_code}")
                return []
            
            data = response.json()
            entries = []
            
            for item in data.get('data', []):
                # Parse entry data - handle both dict and None for nested fields
                project_data = item.get('project') or {}
                app_data = item.get('application') or {}
                
                entry = {
                    'id': item.get('id'),
                    'project': project_data.get('title', 'Unknown') if project_data else 'Unknown',
                    'start_time': item.get('start_date'),
                    'end_time': item.get('end_date'),
                    'duration_seconds': item.get('duration', 0),
                    'application': app_data.get('name', '') if app_data else '',
                    'title': item.get('title', '')
                }
                entries.append(entry)
            
            self.logger.info(f"Fetched {len(entries)} time entries")
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to fetch time entries: {e}")
            return []
    
    def detect_context_switches(self, entries: List[Dict], 
                               switch_threshold_minutes: int = 5) -> Dict:
        """Analyze time entries to detect context switches
        
        Args:
            entries: List of time entries from fetch_time_entries_last_week
            switch_threshold_minutes: Minutes between entries to count as switch
        
        Returns:
            Dictionary with switch analysis results
        """
        if not entries:
            return {
                'total_switches': 0,
                'switches_per_hour': 0,
                'switch_patterns': [],
                'focus_periods': [],
                'scatter_periods': []
            }
        
        # Sort entries by start time
        sorted_entries = sorted(entries, key=lambda x: x['start_time'])
        
        switches = []
        focus_periods = []  # Periods > 30 min on same project
        current_focus_start = None
        current_focus_project = None
        
        for i in range(1, len(sorted_entries)):
            prev = sorted_entries[i-1]
            curr = sorted_entries[i]
            
            # Check if this is a context switch
            if prev['project'] != curr['project']:
                # Calculate gap between entries
                prev_end = datetime.fromisoformat(prev['end_time'].replace('Z', '+00:00'))
                curr_start = datetime.fromisoformat(curr['start_time'].replace('Z', '+00:00'))
                gap_minutes = (curr_start - prev_end).total_seconds() / 60
                
                # Record switch if gap is small enough
                if gap_minutes <= switch_threshold_minutes:
                    switches.append({
                        'from_project': prev['project'],
                        'to_project': curr['project'],
                        'from_app': prev['application'],
                        'to_app': curr['application'],
                        'timestamp': curr['start_time'],
                        'gap_minutes': gap_minutes
                    })
                
                # Check if previous was a focus period
                if current_focus_start and current_focus_project:
                    focus_duration = prev['duration_seconds']
                    if focus_duration >= 1800:  # 30 minutes
                        focus_periods.append({
                            'project': current_focus_project,
                            'duration_minutes': focus_duration / 60,
                            'start_time': current_focus_start
                        })
                
                # Start tracking new potential focus period
                current_focus_start = curr['start_time']
                current_focus_project = curr['project']
            else:
                # Same project, accumulate focus time
                if not current_focus_start:
                    current_focus_start = prev['start_time']
                    current_focus_project = prev['project']
        
        # Calculate metrics
        total_hours = sum(e['duration_seconds'] for e in entries) / 3600
        switches_per_hour = len(switches) / total_hours if total_hours > 0 else 0
        
        # Identify scatter periods (high switch frequency)
        scatter_periods = []
        for i in range(len(switches) - 2):
            # Check if 3+ switches happen within 15 minutes
            time_window = 15
            window_switches = [switches[i]]
            
            for j in range(i + 1, len(switches)):
                switch_time = datetime.fromisoformat(switches[j]['timestamp'].replace('Z', '+00:00'))
                window_start = datetime.fromisoformat(switches[i]['timestamp'].replace('Z', '+00:00'))
                
                if (switch_time - window_start).total_seconds() <= time_window * 60:
                    window_switches.append(switches[j])
                else:
                    break
            
            if len(window_switches) >= 3:
                scatter_periods.append({
                    'timestamp': switches[i]['timestamp'],
                    'switches_count': len(window_switches),
                    'projects_involved': list(set([s['from_project'] for s in window_switches] + 
                                                  [s['to_project'] for s in window_switches]))
                })
        
        # Identify most common switch patterns
        switch_patterns = {}
        for switch in switches:
            pattern = f"{switch['from_project']} → {switch['to_project']}"
            switch_patterns[pattern] = switch_patterns.get(pattern, 0) + 1
        
        # Sort patterns by frequency
        sorted_patterns = sorted(switch_patterns.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_switches': len(switches),
            'switches_per_hour': round(switches_per_hour, 2),
            'switch_patterns': sorted_patterns[:5],  # Top 5 patterns
            'focus_periods': focus_periods,
            'scatter_periods': scatter_periods,
            'switches': switches[:10]  # Sample of switches for debugging
        }
    
    def calculate_focus_metrics(self, switch_analysis: Dict) -> Dict:
        """Calculate ADHD-relevant focus metrics from switch analysis
        
        Args:
            switch_analysis: Results from detect_context_switches
        
        Returns:
            Dictionary with focus metrics and scores
        """
        # Base focus score (0-100)
        # Fewer switches = higher score
        # Baseline: 3 switches/hour is normal, 10+ is high
        switches_per_hour = switch_analysis['switches_per_hour']
        
        if switches_per_hour <= 3:
            focus_score = 90 + (3 - switches_per_hour) * 3  # 90-100
        elif switches_per_hour <= 6:
            focus_score = 70 + (6 - switches_per_hour) * 6.67  # 70-90
        elif switches_per_hour <= 10:
            focus_score = 40 + (10 - switches_per_hour) * 7.5  # 40-70
        else:
            focus_score = max(10, 40 - (switches_per_hour - 10) * 3)  # 10-40
        
        # Adjust for focus periods
        focus_bonus = min(20, len(switch_analysis['focus_periods']) * 5)
        focus_score = min(100, focus_score + focus_bonus)
        
        # Adjust for scatter periods
        scatter_penalty = min(30, len(switch_analysis['scatter_periods']) * 10)
        focus_score = max(0, focus_score - scatter_penalty)
        
        # Calculate hyperfocus score
        hyperfocus_score = 0
        if switch_analysis['focus_periods']:
            avg_focus_duration = sum(p['duration_minutes'] for p in switch_analysis['focus_periods']) / len(switch_analysis['focus_periods'])
            if avg_focus_duration >= 60:
                hyperfocus_score = min(100, avg_focus_duration / 60 * 50)
        
        return {
            'focus_score': round(focus_score),
            'hyperfocus_score': round(hyperfocus_score),
            'switches_per_hour': switches_per_hour,
            'focus_periods_count': len(switch_analysis['focus_periods']),
            'scatter_periods_count': len(switch_analysis['scatter_periods']),
            'interpretation': self._interpret_focus_score(focus_score)
        }
    
    def _interpret_focus_score(self, score: float) -> str:
        """Provide interpretation of focus score"""
        if score >= 80:
            return "Excellent focus - minimal context switching"
        elif score >= 60:
            return "Good focus - manageable switching patterns"
        elif score >= 40:
            return "Moderate focus - frequent but controlled switching"
        elif score >= 20:
            return "Scattered focus - high context switching"
        else:
            return "Very scattered - extreme context switching patterns"
    
    async def fetch_projects_async(self, min_minutes: int = 30) -> List[Dict]:
        """Async wrapper for fetch_projects_last_week"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_projects_last_week, min_minutes)
    
    async def fetch_time_entries_async(self, max_entries: int = 100) -> List[Dict]:
        """Async wrapper for fetch_time_entries_last_week"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_time_entries_last_week, max_entries)
    
    async def analyze_timing_patterns_async(self) -> Dict:
        """Async method to fetch and analyze timing patterns"""
        # Fetch time entries
        entries = await self.fetch_time_entries_async()
        
        if not entries:
            # Fall back to project summary if entries unavailable
            projects = await self.fetch_projects_async()
            return {
                'data_type': 'summary',
                'projects': projects,
                'focus_metrics': None,
                'switch_analysis': None
            }
        
        # Analyze switches and calculate focus metrics
        switch_analysis = self.detect_context_switches(entries)
        focus_metrics = self.calculate_focus_metrics(switch_analysis)
        
        # Also get project summary for comparison
        projects = await self.fetch_projects_async()
        
        return {
            'data_type': 'detailed',
            'projects': projects,
            'entries': entries[:20],  # Sample for memory storage
            'focus_metrics': focus_metrics,
            'switch_analysis': switch_analysis
        }


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