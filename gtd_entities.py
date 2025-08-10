#!/usr/bin/env python3
"""
GTD-Specific Entity Models for Graphiti
Defines custom Pydantic models for GTD concepts to improve entity extraction
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class Priority(str, Enum):
    """GTD Priority levels"""
    A = "A"  # Critical/Urgent
    B = "B"  # Important
    C = "C"  # Nice to have
    NONE = "None"


class Energy(str, Enum):
    """Energy levels for tasks"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProjectStatus(str, Enum):
    """GTD Project status"""
    ACTIVE = "active"
    SOMEDAY = "someday"
    COMPLETED = "completed"
    STALLED = "stalled"


class GTDProject(BaseModel):
    """Represents a GTD Project"""
    project_name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(ProjectStatus.ACTIVE, description="Current project status")
    area_of_focus: Optional[str] = Field(None, description="Related area of focus or responsibility")
    next_action: Optional[str] = Field(None, description="The very next physical action")
    outcome: Optional[str] = Field(None, description="Desired outcome or successful completion criteria")
    deadline: Optional[str] = Field(None, description="Project deadline if applicable (ISO format)")
    review_frequency: Optional[str] = Field("weekly", description="How often to review this project")


class GTDAction(BaseModel):
    """Represents a Next Action in GTD"""
    description: str = Field(..., description="Clear description of the action")
    project: Optional[str] = Field(None, description="Associated project name")
    context: str = Field("@anywhere", description="Context where action can be done (@home, @office, @computer, @phone, @errands)")
    priority: Priority = Field(Priority.NONE, description="Priority level (A, B, C)")
    energy_required: Energy = Field(Energy.MEDIUM, description="Energy level required")
    time_estimate: Optional[int] = Field(None, description="Estimated time in minutes")
    waiting_for: Optional[str] = Field(None, description="Person or event this is waiting on")
    delegated_to: Optional[str] = Field(None, description="Person this is delegated to")
    due_date: Optional[str] = Field(None, description="Due date if applicable (ISO format)")


class GTDContext(BaseModel):
    """Represents a GTD Context (location/tool/person)"""
    context_name: str = Field(..., description="Context name (e.g., @home, @office, @computer)")
    available_time: Optional[int] = Field(None, description="Available time in this context (minutes)")
    energy_level: Energy = Field(Energy.MEDIUM, description="Current energy level in this context")
    tools_available: List[str] = Field(default_factory=list, description="Tools/resources available in this context")
    active: bool = Field(True, description="Whether this context is currently active/available")


class GTDAreaOfFocus(BaseModel):
    """Represents an Area of Focus/Responsibility"""
    area_name: str = Field(..., description="Area name (e.g., Health, Finance, Career)")
    description: Optional[str] = Field(None, description="Description of this area")
    projects: List[str] = Field(default_factory=list, description="Projects in this area")
    maintenance_tasks: List[str] = Field(default_factory=list, description="Recurring maintenance tasks")
    review_frequency: str = Field("weekly", description="How often to review this area")


class ADHDPattern(BaseModel):
    """Represents an ADHD behavioral pattern detected during GTD reviews"""
    pattern_type: Literal["task_switch", "hyperfocus", "scatter", "avoidance", "overwhelm"] = Field(
        ..., description="Type of ADHD pattern observed"
    )
    severity: Literal["low", "medium", "high"] = Field(..., description="Severity of the pattern")
    triggers: List[str] = Field(default_factory=list, description="Identified triggers for this pattern")
    timestamp: str = Field(..., description="When this pattern was observed (ISO format)")
    phase: str = Field(..., description="GTD review phase where pattern occurred")
    duration_seconds: Optional[float] = Field(None, description="Duration of the pattern episode")
    context_switches: Optional[int] = Field(None, description="Number of context switches if applicable")
    
    
class MindsweepItem(BaseModel):
    """Represents an item captured during Mind Sweep"""
    content: str = Field(..., description="The raw captured thought/task/idea")
    category: Optional[Literal["task", "project", "reference", "someday", "waiting"]] = Field(
        None, description="Initial categorization"
    )
    processed: bool = Field(False, description="Whether this item has been processed")
    converted_to: Optional[str] = Field(None, description="What this item was converted to (action/project UUID)")
    capture_time: str = Field(..., description="When this was captured (ISO format)")
    
    
class WeeklyReview(BaseModel):
    """Represents a complete weekly GTD review session"""
    session_id: str = Field(..., description="Unique session identifier")
    start_time: str = Field(..., description="Review start time (ISO format)")
    end_time: Optional[str] = Field(None, description="Review end time (ISO format)")
    items_captured: int = Field(0, description="Total items captured in mind sweep")
    projects_reviewed: int = Field(0, description="Number of projects reviewed")
    actions_created: int = Field(0, description="New actions created")
    decisions_made: int = Field(0, description="Decisions made during review")
    adhd_patterns_detected: List[str] = Field(default_factory=list, description="ADHD patterns observed")
    completion_percentage: float = Field(0.0, description="Percentage of review completed")
    phase_durations: dict = Field(default_factory=dict, description="Duration of each phase in seconds")
    

class TimingInsight(BaseModel):
    """Represents insights from Timing app integration"""
    focus_score: float = Field(..., description="Focus score 0-100")
    context_switches_per_hour: float = Field(..., description="Average context switches per hour")
    hyperfocus_periods: int = Field(0, description="Number of hyperfocus periods detected")
    scatter_periods: int = Field(0, description="Number of scatter periods detected")
    top_time_sinks: List[str] = Field(default_factory=list, description="Top unplanned time consumers")
    alignment_score: float = Field(0.0, description="How well time aligns with GTD priorities")
    productive_contexts: List[str] = Field(default_factory=list, description="Most productive contexts")
    

# Edge type definitions with properties for relationships between entities

class HasNextAction(BaseModel):
    """Relationship: Project has a next action"""
    strength: float = Field(1.0, description="Strength of the relationship (0-1)")
    confidence: float = Field(1.0, description="Confidence in this relationship (0-1)")
    is_current: bool = Field(True, description="Whether this is the current next action")


class RequiresContext(BaseModel):
    """Relationship: Action requires a specific context"""
    strength: float = Field(1.0, description="How strongly this action requires the context (0-1)")
    confidence: float = Field(1.0, description="Confidence in this relationship (0-1)")
    exclusive: bool = Field(False, description="Whether this context is exclusively required")


class BelongsToArea(BaseModel):
    """Relationship: Project belongs to an area of focus"""
    strength: float = Field(1.0, description="Strength of belonging (0-1)")
    confidence: float = Field(1.0, description="Confidence in this relationship (0-1)")
    primary: bool = Field(True, description="Whether this is the primary area")


class ProcessedInto(BaseModel):
    """Relationship: Mindsweep item was processed into action/project"""
    strength: float = Field(1.0, description="Completeness of processing (0-1)")
    confidence: float = Field(1.0, description="Confidence in the processing (0-1)")
    processing_notes: Optional[str] = Field(None, description="Notes from processing")


# Edge type mapping for Graphiti
EDGE_TYPE_MAP = {
    ("GTDProject", "GTDAction"): ["HasNextAction"],
    ("GTDAction", "GTDContext"): ["RequiresContext"],
    ("GTDProject", "GTDAreaOfFocus"): ["BelongsToArea"],
    ("MindsweepItem", "GTDAction"): ["ProcessedInto"],
    ("MindsweepItem", "GTDProject"): ["ProcessedInto"],
}


# Custom entity type list for Graphiti
GTD_ENTITY_TYPES = [
    GTDProject,
    GTDAction,
    GTDContext,
    GTDAreaOfFocus,
    ADHDPattern,
    MindsweepItem,
    WeeklyReview,
    TimingInsight,
]


# Edge type classes for Graphiti
GTD_EDGE_TYPES = [
    HasNextAction,
    RequiresContext,
    BelongsToArea,
    ProcessedInto,
]


def get_gtd_edge_map():
    """Returns the edge type mapping for GTD entities"""
    return EDGE_TYPE_MAP


def get_gtd_entities():
    """Returns list of all GTD entity types for Graphiti configuration"""
    return GTD_ENTITY_TYPES


def get_gtd_edge_types():
    """Returns list of all GTD edge types for Graphiti configuration"""
    return GTD_EDGE_TYPES