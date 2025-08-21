#!/usr/bin/env python3
"""
Minimal Todoist API Integration for GTD Coach
Just the essentials: fetch inbox, mark complete, add to today
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

class TodoistClient:
    """Minimal Todoist integration - path of least resistance"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter"""
        self.api_key = api_key or os.getenv('TODOIST_API_KEY')
        self.logger = logging.getLogger(__name__)
        self.api = None
        
        if self.api_key:
            try:
                from todoist_api_python.api import TodoistAPI
                self.api = TodoistAPI(self.api_key)
                self.logger.info("Todoist API initialized successfully")
            except ImportError:
                self.logger.warning("todoist-api-python not installed. Run: pip install todoist-api-python")
            except Exception as e:
                self.logger.error(f"Failed to initialize Todoist API: {e}")
    
    def is_configured(self) -> bool:
        """Check if Todoist is properly configured"""
        return self.api is not None
    
    def get_inbox_tasks(self) -> List[Dict]:
        """Get all tasks from inbox - simple and direct"""
        if not self.is_configured():
            self.logger.warning("Todoist not configured, returning empty list")
            return []
        
        try:
            # First, find the inbox project ID
            # The projects API returns a paginator that yields lists
            projects_paginator = self.api.get_projects()
            inbox_project = None
            
            # Handle the paginator properly
            for batch in projects_paginator:
                if isinstance(batch, list):
                    for project in batch:
                        if hasattr(project, 'is_inbox_project') and project.is_inbox_project:
                            inbox_project = project
                            break
                else:
                    if hasattr(batch, 'is_inbox_project') and batch.is_inbox_project:
                        inbox_project = batch
                        break
                if inbox_project:
                    break
            
            if not inbox_project:
                self.logger.warning("Could not find inbox project")
                return []
            
            self.logger.info(f"Found inbox project '{inbox_project.name}' with ID: {inbox_project.id}")
            
            # Now get tasks from the inbox project - also returns a paginator
            inbox_tasks = []
            for batch in self.api.get_tasks(project_id=inbox_project.id):
                if isinstance(batch, list):
                    inbox_tasks.extend(batch)
                else:
                    inbox_tasks.append(batch)
            
            self.logger.info(f"Found {len(inbox_tasks)} tasks in inbox")
            
            # Return simplified task data
            return [{
                "id": task.id,
                "content": task.content,
                "labels": task.labels if task.labels else [],
                "description": task.description if task.description else ""
            } for task in inbox_tasks]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch inbox tasks: {e}")
            return []
    
    def mark_complete(self, task_id: str) -> bool:
        """Mark a task as complete"""
        if not self.is_configured():
            return False
        
        try:
            # The correct method is complete_task, not close_task
            self.api.complete_task(task_id=task_id)
            return True
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    def add_to_today(self, content: str, is_deep_work: bool = False) -> Optional[str]:
        """Add task to today with optional time block for deep work"""
        if not self.is_configured():
            return None
        
        try:
            if is_deep_work:
                # Add with 2-hour time block for deep work
                # User can adjust time in Todoist if needed
                task = self.api.add_task(
                    content=content,
                    due_string="today 10am for 2h",
                    labels=["deep"]
                )
            else:
                # Just add to today without specific time
                task = self.api.add_task(
                    content=content,
                    due_string="today"
                )
            
            self.logger.info(f"Added task to today: {content[:50]}...")
            return task.id
            
        except Exception as e:
            self.logger.error(f"Failed to add task: {e}")
            return None
    
    def get_today_tasks(self) -> List[Dict]:
        """Get all tasks in Today view - includes overdue and today's tasks"""
        if not self.is_configured():
            return []
        
        try:
            from datetime import date
            today = date.today()
            
            # Get all tasks - API returns a paginator that yields lists
            all_tasks = []
            for batch in self.api.get_tasks():
                # Each batch is a list of tasks
                if isinstance(batch, list):
                    all_tasks.extend(batch)
                else:
                    all_tasks.append(batch)
            
            # Filter for Today view: tasks due today OR overdue tasks
            today_tasks = []
            for task in all_tasks:
                if task.due and task.due.date:
                    # task.due.date is already a datetime.date object
                    task_date = task.due.date
                    
                    # Include if due today or overdue
                    if task_date <= today:
                        today_tasks.append(task)
            
            # Sort by due date (and parse time from string if available)
            today_tasks.sort(key=lambda t: (
                t.due.date,
                t.due.string if t.due.string else ""
            ))
            
            result = []
            for task in today_tasks:
                task_date = task.due.date
                
                # Check if task has a specific time in the string (e.g., "today 10am")
                has_time = any(indicator in (task.due.string or "").lower() 
                              for indicator in ['am', 'pm', ':', 'morning', 'afternoon', 'evening'])
                
                result.append({
                    "id": task.id,
                    "content": task.content,
                    "labels": task.labels if task.labels else [],
                    "has_time": has_time,
                    "is_overdue": task_date < today,
                    "due_string": task.due.string if task.due.string else ""
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to fetch today's tasks: {e}")
            return []


def get_mock_tasks() -> List[Dict]:
    """Get mock tasks for testing when API unavailable"""
    return [
        {"id": "1", "content": "Write project proposal", "labels": [], "description": ""},
        {"id": "2", "content": "Reply to John's email", "labels": ["quick"], "description": ""},
        {"id": "3", "content": "Review code changes", "labels": [], "description": ""},
        {"id": "4", "content": "Call dentist", "labels": ["quick"], "description": ""},
        {"id": "5", "content": "Design new architecture", "labels": [], "description": ""}
    ]


if __name__ == "__main__":
    # Simple test
    from dotenv import load_dotenv
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    client = TodoistClient()
    
    if client.is_configured():
        print("Testing Todoist integration...")
        
        # Get inbox tasks
        tasks = client.get_inbox_tasks()
        print(f"\nFound {len(tasks)} tasks in inbox")
        
        for task in tasks[:3]:  # Show first 3
            print(f"  - {task['content']}")
        
        # Get today's tasks
        today = client.get_today_tasks()
        print(f"\n{len(today)} tasks scheduled for today")
    else:
        print("Todoist not configured. Using mock data:")
        for task in get_mock_tasks():
            print(f"  - {task['content']}")