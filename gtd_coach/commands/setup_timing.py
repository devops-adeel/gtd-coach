#!/usr/bin/env python3
"""
Setup Timing Projects Command
Creates GTD-aligned project structure in Timing based on Todoist
"""

import os
import sys
import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gtd_coach.integrations.todoist import TodoistAPI
from gtd_coach.integrations.timing import TimingAPI


class TimingProjectSetup:
    """Setup Timing projects to match GTD structure"""
    
    def __init__(self):
        """Initialize with API clients"""
        self.todoist = TodoistAPI()
        self.timing = TimingAPI()
        self.logger = logging.getLogger(__name__)
        
        # Define project categories with colors and productivity scores
        self.categories = {
            "🚀 Active Work": {
                "color": "#4CAF50",  # Green
                "productivity_score": 1.0,
                "notes": "GTD work projects and professional tasks",
                "keywords": ["work", "agentic", "tech", "sales", "hash", "aws", "demo"]
            },
            "👨‍👩‍👧 Family & Personal": {
                "color": "#2196F3",  # Blue
                "productivity_score": 0.8,
                "notes": "Family care, children's education, home organization",
                "keywords": ["family", "children", "dad", "mum", "home", "personal", "minimalist"]
            },
            "💰 Admin & Finance": {
                "color": "#FF9800",  # Orange
                "productivity_score": 0.5,
                "notes": "Financial management, taxes, legal matters",
                "keywords": ["finance", "tax", "assessment", "bangladesh", "zakat", "admin", "legal"]
            },
            "📚 Learning & Development": {
                "color": "#9C27B0",  # Purple
                "productivity_score": 1.0,
                "notes": "Courses, AI/ML projects, professional development",
                "keywords": ["learn", "course", "ai", "ml", "build", "develop", "study", "arabic"]
            },
            "🔧 GTD System": {
                "color": "#00BCD4",  # Cyan
                "productivity_score": 0.8,
                "notes": "GTD reviews, system optimization, planning",
                "keywords": ["gtd", "review", "plan", "system", "organize"]
            },
            "⏸️ Breaks & Misc": {
                "color": "#9E9E9E",  # Gray
                "productivity_score": 0.0,
                "notes": "Uncategorized time, breaks, miscellaneous activities",
                "keywords": ["break", "misc", "other", "uncategorized"]
            }
        }
        
        self.created_projects = {}  # Track created project IDs
    
    def create_timing_project(self, title: str, parent_ref: Optional[str] = None, 
                            color: str = "#808080", productivity_score: float = 1.0, 
                            notes: str = "") -> Optional[str]:
        """Create a single project in Timing
        
        Args:
            title: Project title
            parent_ref: Parent project reference (e.g., "/projects/1")
            color: Hex color code
            productivity_score: -1 to 1
            notes: Project description
        
        Returns:
            Project reference ID if successful, None otherwise
        """
        if not self.timing.is_configured():
            self.logger.error("Timing API not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.timing.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "title": title,
            "color": color,
            "productivity_score": productivity_score,
            "notes": notes
        }
        
        if parent_ref:
            payload["parent"] = parent_ref
        
        try:
            response = requests.post(
                f"{self.timing.base_url}/projects",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                project_data = response.json()['data']
                project_ref = project_data['self']
                print(f"  ✅ Created: {title}")
                return project_ref
            else:
                print(f"  ❌ Failed to create {title}: {response.status_code}")
                if response.text:
                    print(f"     Error: {response.text[:200]}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create project {title}: {e}")
            return None
    
    def categorize_gtd_project(self, project_name: str) -> str:
        """Determine which category a GTD project belongs to
        
        Args:
            project_name: Name of the GTD project
        
        Returns:
            Category name
        """
        project_lower = project_name.lower()
        
        # Check each category's keywords
        for category, config in self.categories.items():
            for keyword in config["keywords"]:
                if keyword in project_lower:
                    return category
        
        # Default categorization based on specific project names
        if "authz" in project_lower or "techxchange" in project_lower:
            return "🚀 Active Work"
        elif "isa" in project_lower or "layla" in project_lower or "idris" in project_lower:
            return "👨‍👩‍👧 Family & Personal"
        elif "land" in project_lower or "asset" in project_lower:
            return "💰 Admin & Finance"
        elif "workflow" in project_lower or "agent" in project_lower:
            return "📚 Learning & Development"
        
        return "🚀 Active Work"  # Default to work
    
    def setup_base_categories(self) -> Dict[str, str]:
        """Create the base category projects in Timing
        
        Returns:
            Dictionary mapping category names to project references
        """
        print("\n📂 Creating base GTD categories in Timing...")
        print("=" * 50)
        
        for category, config in self.categories.items():
            project_ref = self.create_timing_project(
                title=category,
                color=config["color"],
                productivity_score=config["productivity_score"],
                notes=config["notes"]
            )
            
            if project_ref:
                self.created_projects[category] = project_ref
        
        return self.created_projects
    
    def setup_gtd_projects(self):
        """Create GTD projects from Todoist as sub-projects in Timing"""
        
        if not self.todoist.is_configured():
            print("\n⚠️  Todoist not configured - creating base structure only")
            return
        
        print("\n📋 Fetching GTD projects from Todoist...")
        gtd_projects = self.todoist.get_gtd_projects()
        
        if not gtd_projects:
            print("  No GTD projects found in Todoist")
            return
        
        print(f"  Found {len(gtd_projects)} GTD projects")
        
        # Group projects by category
        categorized_projects = {}
        for project in gtd_projects:
            # Only create active projects
            if project['phase'] in ['REFINE', 'REVISIT', 'CLARIFY']:
                category = self.categorize_gtd_project(project['name'])
                if category not in categorized_projects:
                    categorized_projects[category] = []
                categorized_projects[category].append(project)
        
        # Create sub-projects
        print("\n📂 Creating GTD sub-projects in Timing...")
        print("=" * 50)
        
        for category, projects in categorized_projects.items():
            if category in self.created_projects:
                parent_ref = self.created_projects[category]
                print(f"\n{category}:")
                
                for project in projects:
                    # Clean up project name
                    project_name = project['name']
                    if ' - ' in project_name:
                        project_name = project_name.split(' - ')[0]
                    
                    # Determine productivity score based on phase
                    if project['phase'] == 'REFINE':
                        prod_score = 1.0
                    elif project['phase'] == 'REVISIT':
                        prod_score = 0.8
                    else:
                        prod_score = 0.5
                    
                    self.create_timing_project(
                        title=project_name,
                        parent_ref=parent_ref,
                        color=self.categories[category]["color"],
                        productivity_score=prod_score,
                        notes=f"GTD Project ({project['phase']})"
                    )
    
    def setup_context_projects(self):
        """Create GTD context projects if they don't conflict with main categories"""
        
        if not self.todoist.is_configured():
            return
        
        print("\n📍 Setting up GTD contexts...")
        contexts = self.todoist.get_contexts()
        
        if not contexts:
            print("  No GTD contexts found")
            return
        
        # Create a contexts parent project
        contexts_ref = self.create_timing_project(
            title="📍 GTD Contexts",
            color="#607D8B",  # Blue Gray
            productivity_score=0.5,
            notes="GTD contexts for task organization"
        )
        
        if contexts_ref:
            # Create sub-projects for each context
            for context in contexts[:10]:  # Limit to top 10 contexts
                self.create_timing_project(
                    title=f"@{context['name']}",
                    parent_ref=contexts_ref,
                    color="#607D8B",
                    productivity_score=0.5,
                    notes=f"GTD Context: {context['type']}"
                )
    
    def run(self, include_contexts: bool = False):
        """Run the complete setup process
        
        Args:
            include_contexts: Whether to create context projects
        """
        print("\n" + "=" * 60)
        print("🚀 TIMING PROJECT SETUP FOR GTD")
        print("=" * 60)
        
        # Check API configurations
        if not self.timing.is_configured():
            print("\n❌ Error: Timing API not configured")
            print("   Please set TIMING_API_KEY in your .env file")
            return False
        
        print("\n✅ Timing API configured")
        
        if self.todoist.is_configured():
            print("✅ Todoist API configured")
        else:
            print("⚠️  Todoist API not configured (will create base structure only)")
        
        # Create base categories
        self.setup_base_categories()
        
        # Create GTD projects
        if self.todoist.is_configured():
            self.setup_gtd_projects()
            
            # Optionally create contexts
            if include_contexts:
                self.setup_context_projects()
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        
        print("\n📋 Next Steps:")
        print("1. Open Timing app and verify projects appear")
        print("2. Option-drag activities to projects to create rules:")
        print("   • github.com → 🚀 Active Work")
        print("   • todoist.com → 🔧 GTD System")
        print("   • Banking sites → 💰 Admin & Finance")
        print("   • Learning sites → 📚 Learning & Development")
        print("3. Run 'python -m gtd_coach daily' for alignment check")
        
        return True


def main():
    """Main entry point for the setup command"""
    import argparse
    from dotenv import load_dotenv
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Setup Timing projects for GTD")
    parser.add_argument(
        "--include-contexts",
        action="store_true",
        help="Also create GTD context projects"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run setup
    setup = TimingProjectSetup()
    success = setup.run(include_contexts=args.include_contexts)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()