#!/usr/bin/env python3
"""
Test helpers for GTD Coach agent tools
Provides utilities for testing tools with and without state injection
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool


class ToolTestHelper:
    """Helper for testing LangGraph tools with proper state injection"""
    
    @staticmethod
    async def invoke_with_state(tool: BaseTool, args: Dict[str, Any], state: Dict) -> Dict:
        """
        Invoke a tool that requires InjectedState using ToolNode.
        This properly handles state injection at runtime.
        
        Args:
            tool: The tool to invoke
            args: Arguments to pass to the tool
            state: The state to inject
            
        Returns:
            The tool's response as a dictionary
        """
        # Create ToolNode with the single tool
        tool_node = ToolNode([tool])
        
        # Create AIMessage with tool_call
        tool_call = {
            "id": f"test_{tool.name}_1",
            "name": tool.name,
            "args": args
        }
        
        ai_message = AIMessage(
            content="",
            tool_calls=[tool_call]
        )
        
        # Ensure messages list exists in state
        if 'messages' not in state:
            state['messages'] = []
        state['messages'].append(ai_message)
        
        # Invoke ToolNode which handles state injection
        result = await tool_node.ainvoke(state)
        
        # Extract tool response from result messages
        if 'messages' in result:
            for msg in result['messages']:
                if isinstance(msg, ToolMessage):
                    # Return the content, which should be the tool's response
                    return msg.content if isinstance(msg.content, dict) else {"result": msg.content}
        
        return {"error": f"No response from {tool.name}"}
    
    @staticmethod
    async def invoke_stateless(tool: BaseTool, args: Dict[str, Any]) -> Dict:
        """
        Directly invoke a tool that doesn't require state injection.
        Use this for simple tools without InjectedState dependencies.
        
        Args:
            tool: The tool to invoke
            args: Arguments to pass to the tool
            
        Returns:
            The tool's response
        """
        return await tool.ainvoke(args)
    
    @staticmethod
    def create_test_state(overrides: Optional[Dict] = None) -> Dict:
        """
        Create a properly initialized test state with common fields.
        
        Args:
            overrides: Optional dictionary of fields to override
            
        Returns:
            A test state dictionary
        """
        from gtd_coach.agent.state import StateValidator
        from datetime import datetime
        
        # Start with required fields - use StateValidator to get ALL required fields
        state = StateValidator.ensure_required_fields({})
        
        # Update with test-specific values and ensure ALL required fields are present
        default_test_fields = {
            'session_id': 'test_session_123',
            'workflow_type': 'daily_capture',
            'captures': [],
            'processed_items': [],
            'adhd_patterns': [],
            'focus_score': 50,
            'messages': [],  # Required for ToolNode
            'context_switches': [],
            'tool_history': [],
            'phase_durations': {},
            'pattern_analysis': {'severity': 'medium'},
            'accountability_mode': 'adaptive',
            'interventions': [],
            # Add ALL required fields that StateValidator expects
            'user_id': 'test_user',
            'previous_session': None,
            'recurring_patterns': [],
            'user_energy': 'medium',
            'focus_level': 'moderate',
            'stress_indicators': [],
            'weekly_priorities': [],
            'timing_data': {},
            'uncategorized_minutes': 0,
            'phase_start_time': datetime.now().isoformat(),
            'phase_time_limit': 300,  # 5 minutes
            'total_elapsed': 0,
            'time_warnings': [],
            'last_time_check': datetime.now().isoformat(),
            'time_pressure_mode': False,
            'interaction_mode': 'structured',  # Must be one of: conversational, structured, urgent
            'awaiting_input': False,
            'input_timeout': None,
            'context_usage': {},  # Must be dict, not int
            'message_summary': '',  # Must be string, not list
            'phase_summary': '',  # Must be string, not None
            'phase_changed': False,
            'context_overflow_count': 0,
            'last_checkpoint': None
        }
        
        # First update with defaults, then ensure required fields
        state.update(default_test_fields)
        
        # Ensure all required fields are present again
        state = StateValidator.ensure_required_fields(state)
        
        # Apply any overrides last
        if overrides:
            state.update(overrides)
        
        return state
    
    @staticmethod
    def create_tool_call_message(tool_name: str, args: Dict[str, Any]) -> AIMessage:
        """
        Create an AIMessage with a tool call for testing.
        
        Args:
            tool_name: Name of the tool to call
            args: Arguments for the tool
            
        Returns:
            An AIMessage with the tool call
        """
        tool_call = {
            "id": f"call_{tool_name}_test",
            "name": tool_name,
            "args": args
        }
        
        return AIMessage(
            content="",
            tool_calls=[tool_call]
        )
    
    @staticmethod
    def extract_tool_response(result: Dict) -> Optional[Dict]:
        """
        Extract the tool response from a ToolNode result.
        
        Args:
            result: The result from ToolNode.ainvoke()
            
        Returns:
            The tool response or None if not found
        """
        if 'messages' in result:
            for msg in result['messages']:
                if isinstance(msg, ToolMessage):
                    if isinstance(msg.content, dict):
                        return msg.content
                    else:
                        return {"result": msg.content}
        return None


class MockToolNode:
    """
    A mock ToolNode for testing without actual tool execution.
    Useful for testing workflow logic without tool dependencies.
    """
    
    def __init__(self, tools: List[BaseTool], mock_responses: Optional[Dict] = None):
        """
        Initialize mock ToolNode.
        
        Args:
            tools: List of tools (for validation)
            mock_responses: Dict mapping tool names to mock responses
        """
        self.tools = {tool.name: tool for tool in tools}
        self.mock_responses = mock_responses or {}
    
    async def ainvoke(self, state: Dict) -> Dict:
        """Mock invoke that returns predefined responses"""
        messages = state.get('messages', [])
        
        if not messages:
            return state
        
        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return state
        
        response_messages = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call['name']
            
            # Get mock response or default
            if tool_name in self.mock_responses:
                content = self.mock_responses[tool_name]
            else:
                content = {"status": "success", "message": f"Mock response for {tool_name}"}
            
            response_messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id=tool_call['id']
                )
            )
        
        # Return updated state with response messages
        return {
            **state,
            'messages': state.get('messages', []) + response_messages
        }