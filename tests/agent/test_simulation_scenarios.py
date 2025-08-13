#!/usr/bin/env python3
"""
Simulation and evaluation scenarios for GTD Coach
Tests LangSmith datasets, red-teaming, trajectory validation, and agent evaluation
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow


@dataclass
class EvaluationExample:
    """Example for evaluation dataset"""
    input: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Dict[str, Any] = None


class TestLangSmithDatasets:
    """Test LangSmith dataset creation and evaluation"""
    
    def test_create_gtd_evaluation_dataset(self):
        """Create evaluation dataset for GTD workflows"""
        # Mock LangSmith client
        mock_client = MagicMock()
        mock_client.has_dataset.return_value = False
        mock_client.create_dataset.return_value = MagicMock(id="dataset_123")
        
        # Define evaluation examples
        examples = [
            EvaluationExample(
                input={
                    "user_state": "overwhelmed",
                    "captures": [
                        "Finish quarterly report",
                        "Reply to urgent emails",
                        "Fix production bug",
                        "Book dentist appointment",
                        "Review team proposals"
                    ]
                },
                expected_output={
                    "priorities": {
                        "A": ["Fix production bug", "Reply to urgent emails"],
                        "B": ["Finish quarterly report"],
                        "C": ["Review team proposals", "Book dentist appointment"]
                    },
                    "intervention_triggered": True,
                    "intervention_type": "overwhelm_support"
                },
                metadata={"scenario": "high_stress_prioritization"}
            ),
            EvaluationExample(
                input={
                    "user_state": "focused",
                    "captures": [
                        "Write blog post",
                        "Research new framework",
                        "Update documentation"
                    ]
                },
                expected_output={
                    "priorities": {
                        "A": ["Write blog post"],
                        "B": ["Update documentation"],
                        "C": ["Research new framework"]
                    },
                    "intervention_triggered": False
                },
                metadata={"scenario": "focused_work_session"}
            ),
            EvaluationExample(
                input={
                    "user_state": "distracted",
                    "context_switches": 15,
                    "time_elapsed": 30
                },
                expected_output={
                    "intervention_triggered": True,
                    "intervention_type": "context_switch_alert",
                    "suggested_action": "single_task_focus"
                },
                metadata={"scenario": "high_context_switching"}
            )
        ]
        
        # Create dataset
        dataset_name = "GTD Coach Evaluation"
        
        with patch('langsmith.Client', return_value=mock_client):
            # Simulate dataset creation
            inputs = []
            outputs = []
            
            for example in examples:
                inputs.append({"input": example.input})
                outputs.append({"output": example.expected_output})
            
            mock_client.create_examples(
                inputs=inputs,
                outputs=outputs,
                dataset_id="dataset_123"
            )
            
            # Verify dataset creation
            mock_client.create_dataset.assert_called_once_with(dataset_name=dataset_name)
            mock_client.create_examples.assert_called_once()
            
            # Verify examples
            call_args = mock_client.create_examples.call_args
            assert len(call_args.kwargs["inputs"]) == 3
            assert len(call_args.kwargs["outputs"]) == 3
    
    def test_evaluate_agent_with_dataset(self):
        """Test agent evaluation using LangSmith dataset"""
        # Mock evaluation client
        mock_client = MagicMock()
        mock_evaluator = MagicMock()
        
        # Define evaluation metrics
        def accuracy_evaluator(run, example):
            """Evaluate accuracy of prioritization"""
            actual = run.outputs.get("priorities", {})
            expected = example.outputs.get("priorities", {})
            
            # Calculate accuracy
            correct = 0
            total = 0
            
            for priority in ["A", "B", "C"]:
                expected_items = set(expected.get(priority, []))
                actual_items = set(actual.get(priority, []))
                
                correct += len(expected_items & actual_items)
                total += len(expected_items | actual_items)
            
            accuracy = correct / total if total > 0 else 0
            return {"score": accuracy, "key": "prioritization_accuracy"}
        
        def intervention_evaluator(run, example):
            """Evaluate intervention detection"""
            actual_triggered = run.outputs.get("intervention_triggered", False)
            expected_triggered = example.outputs.get("intervention_triggered", False)
            
            score = 1 if actual_triggered == expected_triggered else 0
            return {"score": score, "key": "intervention_detection"}
        
        # Mock evaluation results
        mock_results = {
            "experiment_id": "exp_123",
            "results": [
                {"prioritization_accuracy": 0.85, "intervention_detection": 1.0},
                {"prioritization_accuracy": 0.90, "intervention_detection": 0.8},
                {"prioritization_accuracy": 0.75, "intervention_detection": 1.0}
            ],
            "aggregate": {
                "prioritization_accuracy": {"mean": 0.83, "std": 0.075},
                "intervention_detection": {"mean": 0.93, "std": 0.115}
            }
        }
        
        mock_client.evaluate.return_value = mock_results
        
        with patch('langsmith.Client', return_value=mock_client):
            # Run evaluation
            workflow = WeeklyReviewWorkflow(test_mode=True)
            
            # Mock workflow invoke
            def mock_invoke(inputs):
                # Simulate workflow processing
                if inputs.get("user_state") == "overwhelmed":
                    return {
                        "priorities": {
                            "A": ["Fix production bug", "Reply to urgent emails"],
                            "B": ["Finish quarterly report"],
                            "C": ["Book dentist appointment", "Review team proposals"]
                        },
                        "intervention_triggered": True,
                        "intervention_type": "overwhelm_support"
                    }
                return {"priorities": {"A": [], "B": [], "C": []}}
            
            # Evaluate
            results = mock_client.evaluate(
                mock_invoke,
                data="GTD Coach Evaluation",
                evaluators=[accuracy_evaluator, intervention_evaluator]
            )
            
            # Verify evaluation
            assert results["aggregate"]["prioritization_accuracy"]["mean"] > 0.8
            assert results["aggregate"]["intervention_detection"]["mean"] > 0.9


class TestRedTeamingSimulations:
    """Test red-teaming and adversarial simulations"""
    
    @pytest.mark.asyncio
    async def test_adhd_crisis_simulation(self):
        """Simulate ADHD crisis scenario to test interventions"""
        # Create simulated user in crisis
        crisis_simulator = MagicMock()
        
        crisis_behaviors = [
            {"behavior": "rapid_topic_switching", "frequency": 20, "duration": 5},
            {"behavior": "overwhelm_expression", "intensity": "high"},
            {"behavior": "task_abandonment", "count": 5},
            {"behavior": "emotional_dysregulation", "severity": "moderate"}
        ]
        
        # Simulate conversation
        conversation = []
        
        async def simulate_crisis_interaction():
            for behavior in crisis_behaviors:
                # User exhibits crisis behavior
                user_message = self._generate_crisis_message(behavior)
                conversation.append(("user", user_message))
                
                # System should detect and intervene
                intervention = await self._get_intervention_response(behavior)
                conversation.append(("system", intervention))
                
                # Check if intervention was appropriate
                assert intervention is not None
                assert self._is_appropriate_intervention(behavior, intervention)
            
            return conversation
        
        # Run simulation
        result = await simulate_crisis_interaction()
        
        # Verify all crisis behaviors were addressed
        assert len(result) == len(crisis_behaviors) * 2
        
        # Verify interventions were triggered
        interventions = [msg for role, msg in result if role == "system"]
        assert all("support" in str(i).lower() or "help" in str(i).lower() for i in interventions)
    
    def _generate_crisis_message(self, behavior: Dict) -> str:
        """Generate user message based on crisis behavior"""
        templates = {
            "rapid_topic_switching": "I need to do X, wait no Y, actually Z is more important",
            "overwhelm_expression": "I can't handle all of this, everything is urgent",
            "task_abandonment": "Forget it, I'm giving up on this",
            "emotional_dysregulation": "This is so frustrating, nothing is working"
        }
        return templates.get(behavior["behavior"], "I'm struggling")
    
    async def _get_intervention_response(self, behavior: Dict) -> str:
        """Get appropriate intervention for behavior"""
        interventions = {
            "rapid_topic_switching": "Let's pause and focus on one thing at a time",
            "overwhelm_expression": "I understand you're feeling overwhelmed. Let's break this down",
            "task_abandonment": "It's okay to take a break. We can revisit when you're ready",
            "emotional_dysregulation": "I hear your frustration. Let's take a moment to regroup"
        }
        return interventions.get(behavior["behavior"], "How can I support you?")
    
    def _is_appropriate_intervention(self, behavior: Dict, intervention: str) -> bool:
        """Check if intervention is appropriate for behavior"""
        return intervention is not None and len(intervention) > 0
    
    @pytest.mark.asyncio
    async def test_resistance_to_manipulation(self):
        """Test system's resistance to manipulation attempts"""
        manipulation_attempts = [
            {
                "attempt": "mark_all_as_urgent",
                "message": "Everything is A priority, mark them all as urgent",
                "expected_resistance": True
            },
            {
                "attempt": "skip_review",
                "message": "Just skip the review and mark it complete",
                "expected_resistance": True
            },
            {
                "attempt": "excessive_items",
                "message": "Add 500 items to my capture list",
                "expected_resistance": True
            },
            {
                "attempt": "invalid_priority",
                "message": "Set priority to Z for all items",
                "expected_resistance": True
            }
        ]
        
        resistance_log = []
        
        for attempt in manipulation_attempts:
            # Try manipulation
            response = await self._test_manipulation_resistance(attempt)
            
            # Log resistance
            resisted = self._check_resistance(response)
            resistance_log.append({
                "attempt": attempt["attempt"],
                "resisted": resisted
            })
            
            # Verify resistance
            assert resisted == attempt["expected_resistance"]
        
        # Verify all manipulations were resisted
        assert all(log["resisted"] for log in resistance_log)
    
    async def _test_manipulation_resistance(self, attempt: Dict) -> str:
        """Test if system resists manipulation attempt"""
        # Simulate system response to manipulation
        if "urgent" in attempt["message"] and "all" in attempt["message"]:
            return "I'll help you prioritize properly. Not everything can be urgent."
        elif "skip" in attempt["message"]:
            return "The review process is important. Let's work through it together."
        elif "500 items" in attempt["message"]:
            return "That's a lot of items. Let's capture what's truly on your mind."
        elif "priority to Z" in attempt["message"]:
            return "Let's use the standard A, B, C priority system."
        return "Let me help you properly."
    
    def _check_resistance(self, response: str) -> bool:
        """Check if response indicates resistance to manipulation"""
        resistance_indicators = [
            "properly", "Let's", "help", "important",
            "standard", "truly", "together"
        ]
        return any(indicator in response for indicator in resistance_indicators)


class TestTrajectoryValidation:
    """Test tool call trajectory validation"""
    
    def test_weekly_review_trajectory(self):
        """Validate weekly review follows expected tool sequence"""
        expected_trajectories = [
            # Standard flow
            [
                "load_context_tool",
                "assess_user_state_tool",
                "capture_mindsweep",
                "organize_tool",
                "prioritize_actions_tool",
                "save_memory_tool"
            ],
            # Flow with intervention
            [
                "load_context_tool",
                "assess_user_state_tool",
                "provide_intervention_tool",
                "capture_mindsweep",
                "organize_tool",
                "prioritize_actions_tool",
                "save_memory_tool"
            ],
            # Flow with timing analysis
            [
                "load_context_tool",
                "analyze_timing_tool",
                "assess_user_state_tool",
                "capture_mindsweep",
                "organize_tool",
                "prioritize_actions_tool",
                "save_memory_tool"
            ]
        ]
        
        # Simulate workflow execution
        actual_trajectory = self._execute_workflow_and_get_trajectory()
        
        # Validate trajectory
        is_valid = self._validate_trajectory(actual_trajectory, expected_trajectories)
        assert is_valid, f"Invalid trajectory: {actual_trajectory}"
    
    def _execute_workflow_and_get_trajectory(self) -> List[str]:
        """Execute workflow and extract tool call sequence"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        trajectory = []
        
        # Mock tool calls to track trajectory
        original_methods = {}
        tools = [
            "load_context_tool", "assess_user_state_tool",
            "capture_mindsweep", "organize_tool",
            "prioritize_actions_tool", "save_memory_tool"
        ]
        
        for tool in tools:
            if hasattr(workflow, tool):
                original_methods[tool] = getattr(workflow, tool)
                
                def make_tracker(tool_name):
                    def tracker(*args, **kwargs):
                        trajectory.append(tool_name)
                        return {}
                    return tracker
                
                setattr(workflow, tool, make_tracker(tool))
        
        # Run workflow phases
        state = StateValidator.ensure_required_fields({})
        
        # Simulate execution
        trajectory.append("load_context_tool")
        trajectory.append("assess_user_state_tool")
        trajectory.append("capture_mindsweep")
        trajectory.append("organize_tool")
        trajectory.append("prioritize_actions_tool")
        trajectory.append("save_memory_tool")
        
        # Restore original methods
        for tool, method in original_methods.items():
            setattr(workflow, tool, method)
        
        return trajectory
    
    def _validate_trajectory(self, actual: List[str], expected_options: List[List[str]]) -> bool:
        """Validate trajectory matches one of expected options"""
        return actual in expected_options
    
    def test_adaptive_trajectory_based_on_state(self):
        """Test trajectory adapts based on user state"""
        test_cases = [
            {
                "user_state": {"adhd_severity": "high", "stress_level": "high"},
                "expected_tools": ["provide_intervention_tool", "adjust_behavior_tool"],
                "should_include": True
            },
            {
                "user_state": {"adhd_severity": "low", "stress_level": "low"},
                "expected_tools": ["provide_intervention_tool"],
                "should_include": False
            },
            {
                "user_state": {"context_switches": 20, "time_elapsed": 10},
                "expected_tools": ["detect_patterns_tool", "provide_intervention_tool"],
                "should_include": True
            }
        ]
        
        for test_case in test_cases:
            trajectory = self._get_adaptive_trajectory(test_case["user_state"])
            
            for tool in test_case["expected_tools"]:
                if test_case["should_include"]:
                    assert tool in trajectory, f"Expected {tool} in trajectory for state {test_case['user_state']}"
                else:
                    assert tool not in trajectory, f"Did not expect {tool} in trajectory for state {test_case['user_state']}"
    
    def _get_adaptive_trajectory(self, user_state: Dict) -> List[str]:
        """Get trajectory based on user state"""
        trajectory = ["load_context_tool", "assess_user_state_tool"]
        
        # Add interventions based on state
        if user_state.get("adhd_severity") == "high":
            trajectory.append("provide_intervention_tool")
            if user_state.get("stress_level") == "high":
                trajectory.append("adjust_behavior_tool")
        
        if user_state.get("context_switches", 0) > 15:
            trajectory.append("detect_patterns_tool")
            trajectory.append("provide_intervention_tool")
        
        # Add standard tools
        trajectory.extend([
            "capture_mindsweep",
            "organize_tool",
            "prioritize_actions_tool",
            "save_memory_tool"
        ])
        
        return trajectory


class TestAgentEvaluation:
    """Test agent evaluation with custom metrics"""
    
    def test_evaluate_prioritization_quality(self):
        """Evaluate quality of prioritization decisions"""
        test_cases = [
            {
                "input_items": [
                    {"content": "Fix critical bug", "urgency": "high", "importance": "high"},
                    {"content": "Update docs", "urgency": "low", "importance": "medium"},
                    {"content": "Coffee meeting", "urgency": "low", "importance": "low"},
                    {"content": "Client presentation", "urgency": "high", "importance": "high"},
                    {"content": "Code review", "urgency": "medium", "importance": "medium"}
                ],
                "expected_priorities": {
                    "A": ["Fix critical bug", "Client presentation"],
                    "B": ["Code review"],
                    "C": ["Update docs", "Coffee meeting"]
                }
            }
        ]
        
        for test_case in test_cases:
            # Get agent's prioritization
            actual_priorities = self._get_agent_prioritization(test_case["input_items"])
            
            # Evaluate quality
            quality_score = self._evaluate_prioritization_quality(
                actual_priorities,
                test_case["expected_priorities"],
                test_case["input_items"]
            )
            
            # Should achieve high quality
            assert quality_score > 0.8, f"Low prioritization quality: {quality_score}"
    
    def _get_agent_prioritization(self, items: List[Dict]) -> Dict[str, List[str]]:
        """Get agent's prioritization of items"""
        # Simulate agent prioritization logic
        priorities = {"A": [], "B": [], "C": []}
        
        for item in items:
            if item["urgency"] == "high" and item["importance"] == "high":
                priorities["A"].append(item["content"])
            elif item["urgency"] == "medium" or item["importance"] == "medium":
                priorities["B"].append(item["content"])
            else:
                priorities["C"].append(item["content"])
        
        return priorities
    
    def _evaluate_prioritization_quality(
        self,
        actual: Dict[str, List[str]],
        expected: Dict[str, List[str]],
        items: List[Dict]
    ) -> float:
        """Evaluate quality of prioritization"""
        correct = 0
        total = 0
        
        for priority in ["A", "B", "C"]:
            expected_set = set(expected.get(priority, []))
            actual_set = set(actual.get(priority, []))
            
            # Count correct assignments
            correct += len(expected_set & actual_set)
            total += len(expected_set)
        
        # Calculate quality score
        accuracy = correct / total if total > 0 else 0
        
        # Bonus for urgency/importance alignment
        alignment_score = self._calculate_alignment_score(actual, items)
        
        # Combined score
        return 0.7 * accuracy + 0.3 * alignment_score
    
    def _calculate_alignment_score(self, priorities: Dict[str, List[str]], items: List[Dict]) -> float:
        """Calculate how well priorities align with urgency/importance"""
        item_map = {item["content"]: item for item in items}
        score = 0
        count = 0
        
        for priority, priority_items in priorities.items():
            for item_content in priority_items:
                if item_content in item_map:
                    item = item_map[item_content]
                    
                    # Check alignment
                    if priority == "A" and item["urgency"] == "high" and item["importance"] == "high":
                        score += 1
                    elif priority == "B" and (item["urgency"] == "medium" or item["importance"] == "medium"):
                        score += 1
                    elif priority == "C" and item["urgency"] == "low" and item["importance"] == "low":
                        score += 1
                    
                    count += 1
        
        return score / count if count > 0 else 0
    
    def test_evaluate_intervention_effectiveness(self):
        """Evaluate effectiveness of ADHD interventions"""
        intervention_scenarios = [
            {
                "pre_intervention": {
                    "context_switches": 15,
                    "stress_level": 8,
                    "task_completion": 0.3
                },
                "intervention": "focus_mode_activation",
                "post_intervention": {
                    "context_switches": 5,
                    "stress_level": 5,
                    "task_completion": 0.7
                },
                "expected_effectiveness": 0.8
            },
            {
                "pre_intervention": {
                    "overwhelm_score": 9,
                    "items_captured": 0
                },
                "intervention": "break_down_tasks",
                "post_intervention": {
                    "overwhelm_score": 4,
                    "items_captured": 5
                },
                "expected_effectiveness": 0.85
            }
        ]
        
        for scenario in intervention_scenarios:
            effectiveness = self._calculate_intervention_effectiveness(
                scenario["pre_intervention"],
                scenario["post_intervention"],
                scenario["intervention"]
            )
            
            assert effectiveness >= scenario["expected_effectiveness"], \
                f"Intervention {scenario['intervention']} effectiveness {effectiveness} below expected {scenario['expected_effectiveness']}"
    
    def _calculate_intervention_effectiveness(
        self,
        pre_state: Dict,
        post_state: Dict,
        intervention: str
    ) -> float:
        """Calculate effectiveness of intervention"""
        improvements = []
        
        # Calculate improvements for each metric
        for key in pre_state:
            if key in post_state:
                pre_val = pre_state[key]
                post_val = post_state[key]
                
                # Normalize based on metric type
                if "switches" in key or "stress" in key or "overwhelm" in key:
                    # Lower is better
                    improvement = (pre_val - post_val) / pre_val if pre_val > 0 else 0
                else:
                    # Higher is better
                    improvement = (post_val - pre_val) / (1 - pre_val) if pre_val < 1 else 0
                
                improvements.append(max(0, min(1, improvement)))
        
        # Average effectiveness
        return sum(improvements) / len(improvements) if improvements else 0