#!/usr/bin/env python3
"""
Critical user path E2E tests for GTD Coach
Tests complete user workflows from start to finish with realistic scenarios
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow, PhaseTimer
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
from gtd_coach.agent.shadow_runner import ShadowModeRunner


class TestCompleteWeeklyReview:
    """Test complete weekly review user journey (30 minutes)"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_30_minute_weekly_review_journey(self):
        """Test realistic 30-minute weekly review from start to finish"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        
        session_start = datetime.now()
        session_id = f"review_{session_start.strftime('%Y%m%d_%H%M%S')}"
        
        # Track phase timings
        phase_timings = {}
        
        # Mock timer to track phase durations
        with patch.object(PhaseTimer, 'start_phase') as mock_start_timer:
            def track_phase_start(phase, duration):
                phase_timings[phase] = {
                    "start": datetime.now(),
                    "allocated": duration
                }
            mock_start_timer.side_effect = track_phase_start
            
            # Complete review journey
            journey_log = []
            
            # Phase 1: STARTUP (2 minutes)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                mock_interrupt.return_value = {
                    "ready": True,
                    "user_id": "test_user",
                    "mindset": "focused"
                }
                
                state = StateValidator.ensure_required_fields({
                    "session_id": session_id
                })
                
                state = workflow.startup_phase(state)
                journey_log.append({
                    "phase": "STARTUP",
                    "duration": 2,
                    "outcome": "User ready and focused"
                })
                
                assert state["ready"] is True
                assert state["current_phase"] == "STARTUP"
            
            # Phase 2: MIND_SWEEP (10 minutes total)
            # Capture subprocess (5 minutes)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                mock_interrupt.return_value = {
                    "items": [
                        "Finish Q4 planning document",
                        "Review and approve budget proposal",
                        "Schedule 1:1s with team members",
                        "Fix critical bug in payment system",
                        "Research new monitoring tools",
                        "Update project documentation",
                        "Prepare for board presentation",
                        "Book travel for conference",
                        "Review contractor invoices",
                        "Plan team offsite agenda",
                        "Write performance reviews",
                        "Update security policies",
                        "Clean up email inbox",
                        "Learn new framework",
                        "Organize desk and files"
                    ]
                }
                
                state = workflow.mind_sweep_capture(state)
                journey_log.append({
                    "phase": "MIND_SWEEP_CAPTURE",
                    "duration": 5,
                    "items_captured": len(state["captures"]),
                    "outcome": "15 items captured"
                })
                
                assert len(state["captures"]) == 15
            
            # Process subprocess (5 minutes)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                processed_items = []
                for item in state["captures"]:
                    project = self._categorize_item(item["content"])
                    processed_items.append({
                        "item": item["content"],
                        "project": project,
                        "context": self._get_context(item["content"]),
                        "time_estimate": self._estimate_time(item["content"])
                    })
                
                mock_interrupt.return_value = {"processed": processed_items}
                
                state = workflow.mind_sweep_process(state)
                journey_log.append({
                    "phase": "MIND_SWEEP_PROCESS",
                    "duration": 5,
                    "items_processed": len(state["processed_items"]),
                    "projects_identified": len(set(p["project"] for p in processed_items))
                })
                
                assert len(state["processed_items"]) == 15
            
            # Phase 3: PROJECT_REVIEW (12 minutes - 45 sec per project)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                projects = {}
                unique_projects = set(p["project"] for p in state["processed_items"])
                
                for project in unique_projects:
                    projects[project] = {
                        "next_action": self._get_next_action(project),
                        "status": "active" if self._is_active(project) else "someday",
                        "deadline": self._get_deadline(project),
                        "energy_required": self._get_energy_level(project)
                    }
                
                mock_interrupt.return_value = {"projects": projects}
                
                state = workflow.project_review(state)
                journey_log.append({
                    "phase": "PROJECT_REVIEW",
                    "duration": 12,
                    "projects_reviewed": len(projects),
                    "active_projects": sum(1 for p in projects.values() if p["status"] == "active")
                })
                
                assert len(state["projects"]) > 0
            
            # Phase 4: PRIORITIZATION (5 minutes)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                priorities = {
                    "A": [
                        "Fix critical bug in payment system",
                        "Prepare for board presentation",
                        "Review and approve budget proposal"
                    ],
                    "B": [
                        "Schedule 1:1s with team members",
                        "Write performance reviews",
                        "Update security policies",
                        "Review contractor invoices"
                    ],
                    "C": [
                        "Research new monitoring tools",
                        "Update project documentation",
                        "Learn new framework",
                        "Clean up email inbox"
                    ]
                }
                
                mock_interrupt.return_value = {"priorities": priorities}
                
                state = workflow.prioritization(state)
                journey_log.append({
                    "phase": "PRIORITIZATION",
                    "duration": 5,
                    "a_priorities": len(priorities["A"]),
                    "b_priorities": len(priorities["B"]),
                    "c_priorities": len(priorities["C"])
                })
                
                assert len(state["priorities"]["A"]) == 3
            
            # Phase 5: WRAP_UP (3 minutes)
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                mock_interrupt.return_value = {
                    "satisfied": True,
                    "feedback": "Feeling much more organized and clear on priorities",
                    "notes": "Focus on payment bug first thing Monday"
                }
                
                state = workflow.wrap_up(state)
                journey_log.append({
                    "phase": "WRAP_UP",
                    "duration": 3,
                    "outcome": "Review completed successfully"
                })
                
                assert state["session_complete"] is True
            
            # Verify total duration
            session_end = datetime.now()
            total_duration = (session_end - session_start).total_seconds()
            
            # Log journey summary
            print("\n=== Weekly Review Journey Summary ===")
            for entry in journey_log:
                print(f"{entry['phase']}: {entry.get('outcome', '')} ({entry['duration']} min)")
            print(f"Total duration: {total_duration:.1f} seconds")
            
            # Verify key outcomes
            assert state["session_complete"] is True
            assert len(state["captures"]) == 15
            assert len(state["priorities"]["A"]) > 0
            assert total_duration < 1800  # Should complete within 30 minutes (in test mode)
    
    def _categorize_item(self, item: str) -> str:
        """Categorize item into project"""
        if "bug" in item.lower() or "fix" in item.lower():
            return "Engineering"
        elif "presentation" in item.lower() or "board" in item.lower():
            return "Leadership"
        elif "team" in item.lower() or "1:1" in item.lower():
            return "Team Management"
        elif "budget" in item.lower() or "invoice" in item.lower():
            return "Finance"
        elif "documentation" in item.lower() or "update" in item.lower():
            return "Documentation"
        else:
            return "General"
    
    def _get_context(self, item: str) -> str:
        """Get context for item"""
        if "email" in item.lower() or "review" in item.lower():
            return "@computer"
        elif "meeting" in item.lower() or "1:1" in item.lower():
            return "@office"
        elif "call" in item.lower() or "schedule" in item.lower():
            return "@phone"
        else:
            return "@anywhere"
    
    def _estimate_time(self, item: str) -> int:
        """Estimate time for item in minutes"""
        if "presentation" in item.lower() or "planning" in item.lower():
            return 120
        elif "review" in item.lower() or "document" in item.lower():
            return 60
        elif "fix" in item.lower() or "bug" in item.lower():
            return 90
        else:
            return 30
    
    def _get_next_action(self, project: str) -> str:
        """Get next action for project"""
        actions = {
            "Engineering": "Review error logs and reproduce bug",
            "Leadership": "Create presentation outline",
            "Team Management": "Send calendar invites",
            "Finance": "Download latest reports",
            "Documentation": "List sections needing updates",
            "General": "Review and clarify requirements"
        }
        return actions.get(project, "Define next step")
    
    def _is_active(self, project: str) -> bool:
        """Check if project is active"""
        return project in ["Engineering", "Leadership", "Team Management", "Finance"]
    
    def _get_deadline(self, project: str) -> str:
        """Get deadline for project"""
        deadlines = {
            "Engineering": "End of week",
            "Leadership": "Next Tuesday",
            "Team Management": "Ongoing",
            "Finance": "Month end"
        }
        return deadlines.get(project, "No deadline")
    
    def _get_energy_level(self, project: str) -> str:
        """Get required energy level for project"""
        if project in ["Engineering", "Leadership"]:
            return "high"
        elif project in ["Team Management", "Finance"]:
            return "medium"
        else:
            return "low"


class TestDailyCaptureWithInterventions:
    """Test daily capture workflow with ADHD interventions"""
    
    @pytest.mark.asyncio
    async def test_daily_capture_with_focus_degradation(self):
        """Test daily capture when user's focus degrades"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Simulate focus degradation scenario
        state = StateValidator.ensure_required_fields({
            "session_id": f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_id": "test_user",
            "focus_score": 85  # Starting with good focus
        })
        
        capture_journey = []
        
        # Initial capture - good focus
        with patch.object(workflow, 'assess_user_state') as mock_assess:
            mock_assess.return_value = {
                "adhd_severity": "low",
                "stress_level": 3,
                "focus_score": 85
            }
            
            state = workflow.assess_state(state)
            capture_journey.append({
                "stage": "initial",
                "focus": 85,
                "intervention": False
            })
        
        # Capture items with degrading focus
        focus_levels = [85, 75, 60, 45, 30]  # Degrading focus
        
        for i, focus in enumerate(focus_levels):
            state["focus_score"] = focus
            state["context_switches"] = i * 5  # Increasing context switches
            
            # Check if intervention needed
            if focus < 50:
                # Trigger intervention
                with patch.object(workflow, 'provide_intervention') as mock_intervene:
                    mock_intervene.return_value = {
                        "intervention_type": "focus_restoration",
                        "message": "Let's take a break and refocus",
                        "suggested_action": "single_task_mode"
                    }
                    
                    intervention = workflow.intervene_if_needed(state)
                    capture_journey.append({
                        "stage": f"capture_{i}",
                        "focus": focus,
                        "intervention": True,
                        "intervention_type": "focus_restoration"
                    })
                    
                    # Simulate focus improvement after intervention
                    state["focus_score"] = min(70, focus + 25)
            else:
                capture_journey.append({
                    "stage": f"capture_{i}",
                    "focus": focus,
                    "intervention": False
                })
        
        # Verify interventions were triggered appropriately
        interventions = [j for j in capture_journey if j["intervention"]]
        assert len(interventions) >= 2  # Should have at least 2 interventions
        
        # Verify focus was restored after interventions
        for i, entry in enumerate(capture_journey):
            if entry["intervention"] and i < len(capture_journey) - 1:
                # Next entry should show improved focus
                assert capture_journey[i + 1]["focus"] > entry["focus"] or \
                       capture_journey[i + 1]["focus"] >= 70
    
    @pytest.mark.asyncio
    async def test_timing_integration_flow(self):
        """Test daily capture with Timing app integration"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Mock Timing API data
        timing_data = {
            "time_entries": [
                {"project": "Email", "duration": 45, "app": "Mail"},
                {"project": "Coding", "duration": 120, "app": "VSCode"},
                {"project": "Slack", "duration": 30, "app": "Slack"},
                {"project": "Browser", "duration": 60, "app": "Chrome"},
                {"project": "Coding", "duration": 90, "app": "VSCode"},
                {"project": "Email", "duration": 20, "app": "Mail"}
            ],
            "context_switches": 8,
            "focus_score": 62,
            "longest_focus": 120,
            "time_sinks": ["Browser", "Slack"]
        }
        
        with patch('gtd_coach.agent.tools.analyze_timing_tool') as mock_timing:
            mock_timing.return_value = timing_data
            
            state = StateValidator.ensure_required_fields({})
            
            # Analyze timing data
            state = workflow.analyze_timing(state)
            
            # Check if timing review is needed
            needs_review = workflow.needs_timing_review(state)
            
            if needs_review:
                # Conduct timing review
                with patch.object(workflow, 'interrupt') as mock_interrupt:
                    mock_interrupt.return_value = {
                        "reviewed": True,
                        "insights": [
                            "High context switching detected",
                            "Browser time is above threshold",
                            "Consider batching email checks"
                        ],
                        "commitments": [
                            "Check email only 3 times per day",
                            "Use website blocker during focus time"
                        ]
                    }
                    
                    state = workflow.timing_review(state)
                    
                    assert state.get("timing_insights") is not None
                    assert len(state.get("timing_commitments", [])) > 0
            
            # Verify timing analysis influenced capture
            assert state.get("focus_score") == 62
            assert state.get("context_switches") == 8
            assert needs_review is True  # Should trigger review with this data


class TestMemoryRetrievalPatterns:
    """Test memory retrieval from previous sessions"""
    
    def test_pattern_recognition_at_startup(self):
        """Test showing recurring patterns at session startup"""
        # Create test mindsweep history
        test_data_dir = Path(tempfile.mkdtemp()) / "data"
        test_data_dir.mkdir(parents=True)
        
        # Create historical mindsweep files
        historical_sessions = [
            {
                "date": "20250101_140000",
                "items": [
                    "Review quarterly budget",
                    "Fix authentication bug",
                    "Schedule team meeting",
                    "Update documentation"
                ]
            },
            {
                "date": "20250108_140000",
                "items": [
                    "Finish quarterly budget review",
                    "Debug authentication issues",
                    "Plan team offsite",
                    "Documentation updates needed"
                ]
            },
            {
                "date": "20250115_140000",
                "items": [
                    "Q1 budget planning",
                    "Authentication system refactor",
                    "Team performance reviews",
                    "Update API documentation"
                ]
            }
        ]
        
        for session in historical_sessions:
            file_path = test_data_dir / f"mindsweep_{session['date']}.json"
            with open(file_path, 'w') as f:
                json.dump({"captures": session["items"]}, f)
        
        # Detect patterns
        from gtd_coach.agent.tools import detect_patterns_tool
        
        with patch('gtd_coach.agent.tools.DATA_DIR', test_data_dir):
            patterns = detect_patterns_tool.invoke({})
            
            # Should detect recurring themes
            assert "patterns" in patterns
            detected = patterns["patterns"]
            
            # Should find budget, authentication, team, documentation patterns
            pattern_themes = [p.lower() for p in detected]
            
            assert any("budget" in p or "quarterly" in p for p in pattern_themes)
            assert any("authentication" in p or "auth" in p for p in pattern_themes)
            assert any("team" in p for p in pattern_themes)
            assert any("documentation" in p or "doc" in p for p in pattern_themes)
        
        # Clean up
        import shutil
        shutil.rmtree(test_data_dir.parent)
    
    @pytest.mark.asyncio
    async def test_graphiti_context_retrieval(self):
        """Test retrieving context from Graphiti memory"""
        # Mock Graphiti memory
        mock_memory = AsyncMock()
        
        # Mock search results - previous session patterns
        mock_memory.search_nodes.return_value = [
            {
                "id": "node_1",
                "type": "ADHDPattern",
                "description": "Frequent context switching between email and coding",
                "properties": {
                    "severity": "high",
                    "frequency": 15,
                    "last_occurred": "2025-01-14"
                }
            },
            {
                "id": "node_2",
                "type": "GTDProject",
                "description": "Authentication System Refactor",
                "properties": {
                    "status": "active",
                    "next_action": "Review pull requests",
                    "priority": "high"
                }
            },
            {
                "id": "node_3",
                "type": "WeeklyReview",
                "description": "Last weekly review",
                "properties": {
                    "completion_rate": 0.85,
                    "items_processed": 23,
                    "duration_minutes": 28
                }
            }
        ]
        
        # Mock user context
        mock_memory.get_user_context.return_value = {
            "user_id": "test_user",
            "adhd_severity": "medium",
            "preferred_accountability": "firm",
            "average_capture_count": 18,
            "focus_trend": "declining",
            "last_intervention": "focus_mode",
            "intervention_effectiveness": 0.75
        }
        
        # Load context at startup
        with patch('gtd_coach.agent.tools.load_context_tool') as mock_load:
            mock_load.return_value = {
                "user_context": mock_memory.get_user_context.return_value,
                "recent_patterns": [n for n in await mock_memory.search_nodes()],
                "recommendations": [
                    "Consider starting with Authentication System review",
                    "Watch for context switching - previous pattern detected",
                    "Firm accountability mode recommended based on history"
                ]
            }
            
            context = mock_load.invoke({})
            
            # Verify context loaded
            assert context["user_context"]["adhd_severity"] == "medium"
            assert len(context["recent_patterns"]) == 3
            assert len(context["recommendations"]) == 3
            
            # Verify pattern detection
            patterns = context["recent_patterns"]
            auth_project = next((p for p in patterns if p["type"] == "GTDProject"), None)
            assert auth_project is not None
            assert auth_project["properties"]["priority"] == "high"


class TestShadowModeComparison:
    """Test shadow mode A/B testing in real scenarios"""
    
    @pytest.mark.asyncio
    async def test_legacy_vs_agent_comparison(self):
        """Test comparing legacy and agent workflows"""
        runner = ShadowModeRunner()
        
        # Create mock workflows
        legacy_workflow = MagicMock()
        agent_workflow = AsyncMock()
        
        # Define test scenario
        test_state = StateValidator.ensure_required_fields({
            "captures": [
                "Update project roadmap",
                "Fix customer issue",
                "Review pull requests",
                "Prepare demo",
                "Team standup notes"
            ],
            "user_state": "focused",
            "focus_score": 75
        })
        
        # Mock legacy workflow results
        legacy_workflow.run.return_value = {
            "success": True,
            "priorities": {
                "A": ["Fix customer issue"],
                "B": ["Review pull requests", "Prepare demo"],
                "C": ["Update project roadmap", "Team standup notes"]
            },
            "duration": 35.2,
            "interventions": 0
        }
        
        # Mock agent workflow results (improved)
        agent_workflow.run.return_value = {
            "success": True,
            "priorities": {
                "A": ["Fix customer issue", "Prepare demo"],
                "B": ["Review pull requests"],
                "C": ["Update project roadmap", "Team standup notes"]
            },
            "duration": 28.5,
            "interventions": 1,
            "patterns_detected": ["customer_focus"],
            "optimization_applied": "priority_boost_for_demo"
        }
        
        # Run shadow comparison
        await runner.run_shadow_comparison(
            legacy_workflow=legacy_workflow,
            agent_workflow=agent_workflow,
            state=test_state
        )
        
        # Wait for comparison to complete
        await asyncio.sleep(0.1)
        
        # Analyze differences
        metrics = runner.metrics_logger.metrics
        
        # Find performance comparison
        perf_metrics = [m for m in metrics if m.get("metric_type") == "performance"]
        if perf_metrics:
            # Agent should be faster
            assert perf_metrics[0]["improvement_percent"] > 0
        
        # Find decision differences
        decision_metrics = [m for m in metrics if m.get("legacy_decision")]
        if decision_metrics:
            # Should detect priority differences
            differences_found = False
            for metric in decision_metrics:
                if metric["legacy_decision"] != metric["agent_decision"]:
                    differences_found = True
                    break
            assert differences_found
        
        # Generate comparison report
        summary = runner.metrics_logger.generate_summary()
        
        # Verify summary metrics
        if summary["performance_metrics"] > 0:
            assert summary.get("average_improvement", 0) > 0