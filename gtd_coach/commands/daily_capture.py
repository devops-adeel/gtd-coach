#!/usr/bin/env python3
"""
Daily Interactive Capture & Clarify Command
A conversational GTD coach that guides users through inbox processing
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
import tempfile
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langfuse.callback import CallbackHandler
from langfuse.openai import OpenAI
from pydantic import BaseModel, Field

from gtd_coach.integrations.gtd_entities import (
    MindsweepItem, GTDAction, GTDProject, GTDContext,
    Priority, Energy, ProjectStatus
)
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.integrations.timing import TimingAPI


class InboxSource(str, Enum):
    """Supported inbox sources"""
    OUTLOOK = "outlook"
    PHYSICAL = "physical"
    BEEPER = "beeper"
    SLACK = "slack"
    CALENDAR = "calendar"
    TIMING = "timing"
    VOICE = "voice"


class CapturePhase(str, Enum):
    """Phases of the daily capture process"""
    STARTUP = "startup"
    TIMING_REVIEW = "timing_review"
    INBOX_SCAN = "inbox_scan"
    CAPTURE = "capture"
    CLARIFY = "clarify"
    ORGANIZE = "organize"
    WRAPUP = "wrapup"


class DailyCapture(MindsweepItem):
    """Extended mindsweep item for daily capture with rich metadata"""
    source: InboxSource = Field(..., description="Where this item came from")
    clarified: bool = Field(False, description="Has been through clarification")
    actionable: bool = Field(False, description="Is this actionable?")
    two_minute_rule: bool = Field(False, description="Can be done in 2 minutes?")
    project_id: Optional[str] = Field(None, description="Associated project UUID if applicable")
    context_required: Optional[str] = Field(None, description="GTD context needed")
    energy_level: Optional[Energy] = Field(None, description="Energy required")
    time_estimate: Optional[int] = Field(None, description="Estimated minutes")
    delegate_to: Optional[str] = Field(None, description="Person to delegate to")
    defer_until: Optional[str] = Field(None, description="When to revisit (ISO format)")
    reference_material: Optional[Dict] = Field(None, description="Additional reference data")
    ai_suggestions: Optional[List[str]] = Field(None, description="Coach's suggestions")


class ConversationState(BaseModel):
    """State for the LangGraph conversation"""
    phase: CapturePhase = Field(CapturePhase.STARTUP)
    messages: List[Dict[str, str]] = Field(default_factory=list)
    captures: List[DailyCapture] = Field(default_factory=list)
    current_inbox: Optional[InboxSource] = None
    current_item_index: int = 0
    timing_data: Optional[Dict] = None
    user_context: Optional[Dict] = None
    session_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    accountability_mode: Literal["gentle", "firm", "adaptive"] = "adaptive"
    focus_score: Optional[float] = None
    adhd_patterns_detected: List[str] = Field(default_factory=list)


class DailyCaptureCoach:
    """Conversational GTD coach for daily capture and clarify"""
    
    def __init__(self):
        """Initialize the coach with all integrations"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize APIs
        self.timing_api = TimingAPI() if os.getenv('TIMING_API_KEY') else None
        self.memory = GraphitiMemory() if os.getenv('NEO4J_PASSWORD') else None
        
        # Initialize Langfuse
        self.langfuse_handler = None
        if os.getenv('LANGFUSE_PUBLIC_KEY'):
            self.langfuse_handler = CallbackHandler(
                public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
                secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
                host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
            )
        
        # Initialize LLM client with Langfuse wrapper
        self.llm_client = OpenAI(
            base_url=os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
            api_key="lm-studio",
            default_headers={"X-Custom-Header": "gtd-coach"}
        )
        
        # Data directory
        self.data_dir = Path.home() / "gtd-coach" / "data" / "daily_captures"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LangGraph
        self.graph = self._build_graph()
        self.memory_saver = MemorySaver()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for conversation flow"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes for each phase
        workflow.add_node("startup", self.startup_node)
        workflow.add_node("timing_review", self.timing_review_node)
        workflow.add_node("inbox_scan", self.inbox_scan_node)
        workflow.add_node("capture", self.capture_node)
        workflow.add_node("clarify", self.clarify_node)
        workflow.add_node("organize", self.organize_node)
        workflow.add_node("wrapup", self.wrapup_node)
        
        # Add edges defining the flow
        workflow.set_entry_point("startup")
        workflow.add_edge("startup", "timing_review")
        workflow.add_edge("timing_review", "inbox_scan")
        workflow.add_edge("inbox_scan", "capture")
        workflow.add_edge("capture", "clarify")
        workflow.add_edge("clarify", "organize")
        workflow.add_edge("organize", "wrapup")
        workflow.add_edge("wrapup", END)
        
        return workflow.compile(checkpointer=self.memory_saver)
    
    async def startup_node(self, state: ConversationState) -> ConversationState:
        """Initialize session and greet user"""
        # Load user context from Graphiti if available
        if self.memory:
            user_context = await self.memory.get_user_context()
            state.user_context = user_context
            
            # Determine accountability mode based on patterns
            if user_context.get('adhd_severity', 'medium') == 'high':
                state.accountability_mode = 'firm'
            elif user_context.get('adhd_severity') == 'low':
                state.accountability_mode = 'gentle'
        
        # Generate personalized greeting
        greeting = await self._generate_greeting(state)
        state.messages.append({"role": "assistant", "content": greeting})
        
        # Show recurring patterns from memory
        if state.user_context and state.user_context.get('recurring_patterns'):
            patterns_msg = "💭 On your mind lately:\n"
            for pattern in state.user_context['recurring_patterns'][:3]:
                patterns_msg += f"  • {pattern}\n"
            state.messages.append({"role": "assistant", "content": patterns_msg})
        
        state.phase = CapturePhase.TIMING_REVIEW
        return state
    
    async def timing_review_node(self, state: ConversationState) -> ConversationState:
        """Quick 2-minute review of uncategorized time"""
        if not self.timing_api:
            state.messages.append({
                "role": "assistant",
                "content": "No Timing app configured, skipping time review."
            })
            state.phase = CapturePhase.INBOX_SCAN
            return state
        
        # Fetch yesterday's uncategorized time
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        timing_data = await self._fetch_timing_data(yesterday)
        state.timing_data = timing_data
        
        # Calculate focus score
        if timing_data.get('focus_metrics'):
            state.focus_score = timing_data['focus_metrics']['focus_score']
        
        # Identify uncategorized blocks
        uncategorized = self._identify_uncategorized_time(timing_data)
        
        if uncategorized['total_minutes'] > 30:
            msg = f"📊 Yesterday you had {uncategorized['total_minutes']} minutes of uncategorized time.\n"
            msg += "Let's quickly categorize the main blocks:\n"
            
            for block in uncategorized['blocks'][:3]:
                msg += f"\n🕐 {block['time_range']}: {block['apps']}\n"
                msg += "What were you working on? (or 'skip' to move on): "
                
            state.messages.append({"role": "assistant", "content": msg})
            
            # Capture categorization
            # This would be interactive in real implementation
            categorization = await self._get_user_input("Categorization")
            if categorization.lower() != 'skip':
                capture = DailyCapture(
                    content=f"Categorize time: {categorization}",
                    source=InboxSource.TIMING,
                    category="reference",
                    capture_time=datetime.now().isoformat()
                )
                state.captures.append(capture)
        
        state.phase = CapturePhase.INBOX_SCAN
        return state
    
    async def inbox_scan_node(self, state: ConversationState) -> ConversationState:
        """Guide through each inbox source"""
        inboxes = [
            InboxSource.OUTLOOK,
            InboxSource.PHYSICAL,
            InboxSource.BEEPER,
            InboxSource.SLACK,
            InboxSource.CALENDAR
        ]
        
        msg = "Let's scan your inboxes. I'll guide you through each one.\n"
        msg += "For each inbox, capture anything that needs attention.\n\n"
        
        for inbox in inboxes:
            msg += f"📥 {inbox.value.title()} Inbox\n"
            
            if inbox == InboxSource.OUTLOOK:
                msg += "Open Outlook. Scan subject lines. What needs capturing?\n"
            elif inbox == InboxSource.PHYSICAL:
                msg += "Check your physical inbox/desk. Any papers or notes?\n"
            elif inbox == InboxSource.BEEPER:
                msg += "Open Beeper/texts. Any messages needing action?\n"
            elif inbox == InboxSource.SLACK:
                msg += "Check Slack. Any DMs or mentions to process?\n"
            elif inbox == InboxSource.CALENDAR:
                msg += "Review calendar. Any prep needed for upcoming events?\n"
            
            msg += "(Type items one per line, 'voice' to dictate, or 'next' when done)\n"
            
            state.current_inbox = inbox
            state.messages.append({"role": "assistant", "content": msg})
            
            # Capture items for this inbox
            # This would be interactive in real implementation
            items = await self._capture_inbox_items(inbox)
            for item_text in items:
                capture = DailyCapture(
                    content=item_text,
                    source=inbox,
                    capture_time=datetime.now().isoformat()
                )
                state.captures.append(capture)
        
        state.phase = CapturePhase.CAPTURE
        return state
    
    async def capture_node(self, state: ConversationState) -> ConversationState:
        """Brain dump - capture everything else on mind"""
        msg = "🧠 Brain Dump Time!\n"
        msg += "What else is on your mind? Don't filter, just capture.\n"
        msg += "(Type 'voice' to dictate, or 'done' when complete)\n"
        
        state.messages.append({"role": "assistant", "content": msg})
        
        # Detect ADHD patterns during capture
        rapid_switches = 0
        last_topic = None
        
        # Interactive capture loop
        # This would be interactive in real implementation
        brain_dump = await self._brain_dump_capture()
        
        for item_text in brain_dump:
            # Simple topic detection
            current_topic = self._detect_topic(item_text)
            if last_topic and current_topic != last_topic:
                rapid_switches += 1
            last_topic = current_topic
            
            capture = DailyCapture(
                content=item_text,
                source=InboxSource.VOICE if "voice" in item_text.lower() else InboxSource.PHYSICAL,
                capture_time=datetime.now().isoformat()
            )
            state.captures.append(capture)
        
        # Record ADHD pattern if detected
        if rapid_switches > 5:
            state.adhd_patterns_detected.append("rapid_topic_switching")
            if state.accountability_mode == "adaptive":
                state.accountability_mode = "firm"
                msg = "I notice you're jumping between topics. Let's add some structure."
                state.messages.append({"role": "assistant", "content": msg})
        
        state.phase = CapturePhase.CLARIFY
        return state
    
    async def clarify_node(self, state: ConversationState) -> ConversationState:
        """Process each capture through GTD clarification"""
        msg = f"Great! You captured {len(state.captures)} items. Let's clarify them.\n"
        state.messages.append({"role": "assistant", "content": msg})
        
        for i, capture in enumerate(state.captures):
            if capture.clarified:
                continue
            
            state.current_item_index = i
            
            # Generate clarifying questions
            questions = await self._generate_clarifying_questions(capture)
            
            msg = f"\n📝 Item {i+1}/{len(state.captures)}: {capture.content}\n"
            msg += questions
            
            state.messages.append({"role": "assistant", "content": msg})
            
            # Get clarification (interactive in real implementation)
            clarification = await self._get_clarification(capture)
            
            # Update capture with clarification
            capture.clarified = True
            capture.actionable = clarification.get('actionable', False)
            
            if capture.actionable:
                capture.two_minute_rule = clarification.get('two_minute', False)
                capture.context_required = clarification.get('context')
                capture.energy_level = Energy(clarification.get('energy', 'medium'))
                capture.time_estimate = clarification.get('time_estimate', 15)
                
                # AI suggestions based on patterns
                suggestions = await self._generate_suggestions(capture, state)
                capture.ai_suggestions = suggestions
        
        state.phase = CapturePhase.ORGANIZE
        return state
    
    async def organize_node(self, state: ConversationState) -> ConversationState:
        """Organize clarified items into GTD system"""
        msg = "📂 Let's organize everything into your GTD system.\n"
        
        # Group by category
        actions = [c for c in state.captures if c.actionable and not c.two_minute_rule]
        two_minutes = [c for c in state.captures if c.two_minute_rule]
        someday = [c for c in state.captures if c.category == "someday"]
        reference = [c for c in state.captures if c.category == "reference"]
        
        if two_minutes:
            msg += f"\n⚡ {len(two_minutes)} two-minute tasks to do now:\n"
            for item in two_minutes:
                msg += f"  • {item.content}\n"
        
        if actions:
            msg += f"\n📋 {len(actions)} next actions created\n"
        
        if someday:
            msg += f"\n💭 {len(someday)} items added to someday/maybe\n"
        
        if reference:
            msg += f"\n📚 {len(reference)} items filed as reference\n"
        
        state.messages.append({"role": "assistant", "content": msg})
        
        # Save to Graphiti
        if self.memory:
            await self._save_to_graphiti(state)
        
        state.phase = CapturePhase.WRAPUP
        return state
    
    async def wrapup_node(self, state: ConversationState) -> ConversationState:
        """Celebrate completion and save session"""
        # Calculate session metrics
        total_captured = len(state.captures)
        total_clarified = len([c for c in state.captures if c.clarified])
        total_actionable = len([c for c in state.captures if c.actionable])
        
        # Generate personalized celebration
        celebration = await self._generate_celebration(state, {
            'captured': total_captured,
            'clarified': total_clarified,
            'actionable': total_actionable,
            'focus_score': state.focus_score
        })
        
        state.messages.append({"role": "assistant", "content": celebration})
        
        # Save session to file
        self._save_session(state)
        
        # Update user context for next time
        if self.memory:
            await self._update_user_context(state)
        
        return state
    
    async def _generate_greeting(self, state: ConversationState) -> str:
        """Generate personalized greeting based on user context"""
        if state.accountability_mode == "firm":
            return "Good morning! Time for your daily capture. Let's be efficient - we have 15 minutes."
        elif state.accountability_mode == "gentle":
            return "Good morning! Ready for a quick check-in? We'll go at your pace."
        else:
            return "Good morning! Let's capture what's on your mind and get you organized for the day."
    
    async def _fetch_timing_data(self, date: str) -> Dict:
        """Fetch timing data for specified date"""
        if not self.timing_api:
            return {}
        
        try:
            entries = self.timing_api.fetch_time_entries_last_week(max_entries=200)
            projects = self.timing_api.fetch_projects_last_week(min_minutes=5)
            
            # Filter to specific date
            date_entries = [e for e in entries if date in e.get('start_time', '')]
            
            # Analyze patterns
            switch_analysis = self.timing_api.detect_context_switches(date_entries)
            focus_metrics = self.timing_api.calculate_focus_metrics(switch_analysis)
            
            return {
                'entries': date_entries,
                'projects': projects,
                'focus_metrics': focus_metrics,
                'switch_analysis': switch_analysis
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch timing data: {e}")
            return {}
    
    def _identify_uncategorized_time(self, timing_data: Dict) -> Dict:
        """Identify uncategorized time blocks"""
        uncategorized = {
            'total_minutes': 0,
            'blocks': []
        }
        
        if not timing_data.get('entries'):
            return uncategorized
        
        for entry in timing_data['entries']:
            if 'uncategorized' in entry.get('project', '').lower() or \
               'misc' in entry.get('project', '').lower():
                duration = entry.get('duration', 0)
                uncategorized['total_minutes'] += duration
                
                if duration > 15:  # Only show blocks > 15 minutes
                    uncategorized['blocks'].append({
                        'time_range': f"{entry.get('start_time', 'unknown')} - {entry.get('end_time', 'unknown')}",
                        'apps': entry.get('app', 'Unknown'),
                        'duration': duration
                    })
        
        return uncategorized
    
    async def _capture_inbox_items(self, inbox: InboxSource) -> List[str]:
        """Capture items from a specific inbox (placeholder for interactive capture)"""
        # In real implementation, this would be interactive
        # For now, return empty list
        return []
    
    async def _brain_dump_capture(self) -> List[str]:
        """Capture brain dump items (placeholder for interactive capture)"""
        # In real implementation, this would be interactive
        # For now, return empty list
        return []
    
    async def _generate_clarifying_questions(self, capture: DailyCapture) -> str:
        """Generate clarifying questions for a capture"""
        prompt = f"""
        For this captured item: "{capture.content}"
        Generate 2-3 quick clarifying questions following GTD methodology:
        1. Is it actionable?
        2. If yes, what's the next physical action?
        3. Can it be done in 2 minutes?
        Keep questions brief and focused.
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="meta-llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": "You are a GTD coach helping clarify captured items."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Failed to generate questions: {e}")
            return "Is this actionable? What's the next action?"
    
    async def _get_clarification(self, capture: DailyCapture) -> Dict:
        """Get clarification for a capture (placeholder for interactive)"""
        # In real implementation, this would be interactive
        return {
            'actionable': True,
            'two_minute': False,
            'context': '@computer',
            'energy': 'medium',
            'time_estimate': 30
        }
    
    async def _generate_suggestions(self, capture: DailyCapture, state: ConversationState) -> List[str]:
        """Generate AI suggestions based on patterns and context"""
        suggestions = []
        
        # Check for similar past items
        if state.user_context and state.user_context.get('recurring_patterns'):
            for pattern in state.user_context['recurring_patterns']:
                if pattern.lower() in capture.content.lower():
                    suggestions.append(f"This relates to recurring theme: {pattern}")
        
        # Energy-based suggestions
        if state.focus_score and state.focus_score < 50:
            if capture.energy_level == Energy.HIGH:
                suggestions.append("Consider scheduling this for a high-focus time block")
        
        # Context-based suggestions
        if capture.context_required == "@computer" and state.timing_data:
            productive_hours = self._identify_productive_hours(state.timing_data)
            if productive_hours:
                suggestions.append(f"Your most productive computer time: {productive_hours}")
        
        return suggestions
    
    def _identify_productive_hours(self, timing_data: Dict) -> Optional[str]:
        """Identify most productive hours from timing data"""
        if not timing_data.get('focus_metrics'):
            return None
        
        # Simplified - in real implementation would analyze time patterns
        if timing_data['focus_metrics']['focus_score'] > 70:
            return "Morning (9-11am)"
        else:
            return "Afternoon (2-4pm)"
    
    def _detect_topic(self, text: str) -> str:
        """Simple topic detection for ADHD pattern analysis"""
        # Simplified keyword-based detection
        work_keywords = ['project', 'meeting', 'email', 'report', 'deadline']
        personal_keywords = ['home', 'family', 'health', 'exercise', 'personal']
        
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in work_keywords):
            return "work"
        elif any(kw in text_lower for kw in personal_keywords):
            return "personal"
        else:
            return "other"
    
    async def _generate_celebration(self, state: ConversationState, metrics: Dict) -> str:
        """Generate personalized celebration message"""
        msg = "🎉 Daily Capture Complete!\n\n"
        msg += f"📊 Session Summary:\n"
        msg += f"  • Captured: {metrics['captured']} items\n"
        msg += f"  • Clarified: {metrics['clarified']} items\n"
        msg += f"  • Actionable: {metrics['actionable']} next actions\n"
        
        if metrics.get('focus_score'):
            msg += f"  • Yesterday's Focus Score: {metrics['focus_score']}/100\n"
        
        if state.adhd_patterns_detected:
            msg += f"\n💡 Patterns noticed: {', '.join(state.adhd_patterns_detected)}\n"
            msg += "I'll adapt tomorrow's session based on this.\n"
        
        if state.accountability_mode == "firm":
            msg += "\n💪 Well done! You stayed on track. Same time tomorrow."
        elif state.accountability_mode == "gentle":
            msg += "\n🌟 Great job! You're building a solid capture habit."
        else:
            msg += "\n✅ Nice work! Your system is getting stronger."
        
        return msg
    
    async def _save_to_graphiti(self, state: ConversationState):
        """Save session data to Graphiti knowledge graph"""
        if not self.memory:
            return
        
        try:
            # Create session episode
            session_data = {
                "type": "daily_capture_session",
                "session_id": state.session_id,
                "date": datetime.now().isoformat(),
                "metrics": {
                    "total_captured": len(state.captures),
                    "total_clarified": len([c for c in state.captures if c.clarified]),
                    "total_actionable": len([c for c in state.captures if c.actionable]),
                    "focus_score": state.focus_score,
                    "adhd_patterns": state.adhd_patterns_detected
                },
                "captures": [c.dict() for c in state.captures]
            }
            
            await self.memory.add_episode(
                session_data,
                f"Daily capture session {state.session_id}"
            )
            
            # Create GTD entities for actionable items
            for capture in state.captures:
                if capture.actionable and not capture.two_minute_rule:
                    action = GTDAction(
                        description=capture.content,
                        context=capture.context_required or "@anywhere",
                        priority=Priority.B,
                        energy_required=capture.energy_level or Energy.MEDIUM,
                        time_estimate=capture.time_estimate
                    )
                    
                    await self.memory.add_gtd_entity(action, "action")
            
            self.logger.info(f"Saved session {state.session_id} to Graphiti")
            
        except Exception as e:
            self.logger.error(f"Failed to save to Graphiti: {e}")
    
    async def _update_user_context(self, state: ConversationState):
        """Update user context in Graphiti for personalization"""
        if not self.memory:
            return
        
        try:
            # Update ADHD severity based on patterns
            severity = "low"
            if len(state.adhd_patterns_detected) > 2:
                severity = "high"
            elif len(state.adhd_patterns_detected) > 0:
                severity = "medium"
            
            context_update = {
                "last_session": state.session_id,
                "last_session_date": datetime.now().isoformat(),
                "adhd_severity": severity,
                "preferred_accountability": state.accountability_mode,
                "average_capture_count": len(state.captures),
                "focus_trend": state.focus_score
            }
            
            await self.memory.update_user_context(context_update)
            
        except Exception as e:
            self.logger.error(f"Failed to update user context: {e}")
    
    def _save_session(self, state: ConversationState):
        """Save session to JSON file"""
        try:
            session_file = self.data_dir / f"session_{state.session_id}.json"
            
            session_data = {
                "session_id": state.session_id,
                "date": datetime.now().isoformat(),
                "phase": state.phase.value,
                "messages": state.messages,
                "captures": [c.dict() for c in state.captures],
                "timing_data": state.timing_data,
                "focus_score": state.focus_score,
                "adhd_patterns": state.adhd_patterns_detected,
                "accountability_mode": state.accountability_mode
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved session to {session_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    async def run(self) -> Dict:
        """Run the daily capture session"""
        print("\n🌅 Starting Daily Capture & Clarify Session\n")
        print("=" * 60)
        
        # Initialize state
        initial_state = ConversationState()
        
        # Run the graph
        config = {"configurable": {"thread_id": initial_state.session_id}}
        
        try:
            # Execute the workflow
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Print conversation history
            for msg in final_state['messages']:
                if msg['role'] == 'assistant':
                    print(f"\n🤖 Coach: {msg['content']}")
                else:
                    print(f"\n👤 You: {msg['content']}")
            
            return {
                'session_id': final_state['session_id'],
                'captures': len(final_state['captures']),
                'clarified': len([c for c in final_state['captures'] if c.clarified]),
                'actionable': len([c for c in final_state['captures'] if c.actionable]),
                'focus_score': final_state.get('focus_score')
            }
            
        except Exception as e:
            self.logger.error(f"Session failed: {e}")
            print(f"\n❌ Session error: {e}")
            return {}


class WhisperTranscriber:
    """Voice transcription using OpenAI Whisper"""
    
    def __init__(self):
        """Initialize Whisper for voice capture"""
        self.logger = logging.getLogger(__name__)
        self.temp_dir = Path(tempfile.gettempdir()) / "gtd_voice"
        self.temp_dir.mkdir(exist_ok=True)
    
    def record_audio(self, duration: int = 30) -> Path:
        """Record audio using system microphone
        
        Args:
            duration: Maximum recording duration in seconds
        
        Returns:
            Path to recorded audio file
        """
        audio_file = self.temp_dir / f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        try:
            # Use sox or ffmpeg for cross-platform recording
            if sys.platform == "darwin":  # macOS
                cmd = [
                    "sox", "-d", "-r", "16000", "-c", "1",
                    str(audio_file), "trim", "0", str(duration)
                ]
            else:  # Linux/Windows with ffmpeg
                cmd = [
                    "ffmpeg", "-f", "alsa", "-i", "default",
                    "-t", str(duration), "-ar", "16000", "-ac", "1",
                    str(audio_file)
                ]
            
            print(f"🎤 Recording for up to {duration} seconds... (Press Ctrl+C to stop)")
            subprocess.run(cmd, check=True)
            
            return audio_file
            
        except Exception as e:
            self.logger.error(f"Failed to record audio: {e}")
            return None
    
    def transcribe(self, audio_file: Path) -> Optional[str]:
        """Transcribe audio file using Whisper
        
        Args:
            audio_file: Path to audio file
        
        Returns:
            Transcribed text or None if failed
        """
        try:
            import whisper
            
            # Load base model for speed
            model = whisper.load_model("base")
            
            # Transcribe
            result = model.transcribe(str(audio_file))
            
            # Clean up audio file
            audio_file.unlink()
            
            return result["text"]
            
        except ImportError:
            self.logger.error("Whisper not installed. Run: pip install openai-whisper")
            return None
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return None


def main():
    """Main entry point for daily capture command"""
    import argparse
    from dotenv import load_dotenv
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Daily GTD Capture & Clarify")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice capture with Whisper"
    )
    parser.add_argument(
        "--skip-timing",
        action="store_true",
        help="Skip Timing app review"
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
    
    # Run daily capture
    coach = DailyCaptureCoach()
    
    # Enable voice if requested
    if args.voice:
        transcriber = WhisperTranscriber()
        # Add transcriber to coach (would need to integrate into workflow)
    
    # Run session
    asyncio.run(coach.run())


if __name__ == "__main__":
    main()