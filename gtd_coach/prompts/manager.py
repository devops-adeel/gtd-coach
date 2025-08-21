#!/usr/bin/env python3
"""
Prompt Manager for GTD Coach
Fetches and manages prompts from Langfuse with fallback to local files
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompts from Langfuse with local fallback
    Following the pattern from the Langfuse documentation
    """
    
    def __init__(self):
        """Initialize the prompt manager"""
        self.langfuse = None
        self.local_prompts_dir = Path.home() / "gtd-coach" / "config" / "prompts"
        
        if LANGFUSE_AVAILABLE and os.getenv('LANGFUSE_PUBLIC_KEY'):
            try:
                self.langfuse = Langfuse()
                logger.info("PromptManager: Using Langfuse for prompt management")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                logger.info("PromptManager: Falling back to local prompts")
        else:
            logger.info("PromptManager: Using local prompts (Langfuse not configured)")
    
    @lru_cache(maxsize=128)
    def get_prompt(self, name: str, label: str = "production", 
                   cache_ttl_seconds: int = 300) -> str:
        """
        Get a prompt from Langfuse or local fallback
        
        Args:
            name: Prompt name in Langfuse
            label: Prompt version label (default: "production")
            cache_ttl_seconds: Cache duration for the prompt
            
        Returns:
            Prompt text string
        """
        # Try Langfuse first
        if self.langfuse:
            try:
                prompt_obj = self.langfuse.get_prompt(
                    name=name,
                    label=label,
                    cache_ttl_seconds=cache_ttl_seconds
                )
                
                # Get the Langchain-compatible prompt
                # This can return either a string (text prompt) or list (chat prompt)
                langchain_result = prompt_obj.get_langchain_prompt()
                
                if isinstance(langchain_result, str):
                    # Text prompt - return as is
                    prompt_text = langchain_result
                elif isinstance(langchain_result, list):
                    # Chat prompt - extract system message or concatenate
                    if langchain_result:
                        # Try to find system message first
                        system_msg = None
                        for msg in langchain_result:
                            # Handle both dict and tuple formats
                            if isinstance(msg, dict) and msg.get('role') == 'system':
                                system_msg = msg
                                break
                            elif isinstance(msg, (tuple, list)) and len(msg) >= 2 and msg[0] == 'system':
                                system_msg = {'role': 'system', 'content': msg[1]}
                                break
                        
                        if system_msg:
                            prompt_text = system_msg.get('content', '')
                        else:
                            # Fallback: use first message or concatenate all
                            texts = []
                            for msg in langchain_result:
                                if isinstance(msg, dict):
                                    texts.append(msg.get('content', ''))
                                elif isinstance(msg, (tuple, list)) and len(msg) >= 2:
                                    texts.append(str(msg[1]))
                                else:
                                    texts.append(str(msg))
                            prompt_text = ' '.join(texts)
                    else:
                        prompt_text = ""
                else:
                    logger.warning(f"Unexpected type from get_langchain_prompt for '{name}': {type(langchain_result)}")
                    prompt_text = str(langchain_result)
                
                logger.debug(f"Fetched prompt '{name}' from Langfuse (type: {type(langchain_result).__name__})")
                return prompt_text
                
            except Exception as e:
                logger.warning(f"Failed to fetch prompt '{name}' from Langfuse: {e}")
        
        # Fallback to local file
        return self._get_local_prompt(name)
    
    def get_prompt_with_config(self, name: str, label: str = "production") -> Dict[str, Any]:
        """
        Get prompt with its configuration (model, temperature, etc.)
        
        Args:
            name: Prompt name
            label: Version label
            
        Returns:
            Dict with 'prompt' and 'config' keys
        """
        if self.langfuse:
            try:
                prompt_obj = self.langfuse.get_prompt(name=name, label=label)
                langchain_result = prompt_obj.get_langchain_prompt()
                
                # Handle both text and chat prompts
                if isinstance(langchain_result, str):
                    prompt_text = langchain_result
                elif isinstance(langchain_result, list):
                    # Extract system message or concatenate for chat prompts
                    if langchain_result:
                        system_msg = None
                        for msg in langchain_result:
                            # Handle both dict and tuple formats
                            if isinstance(msg, dict) and msg.get('role') == 'system':
                                system_msg = msg
                                break
                            elif isinstance(msg, (tuple, list)) and len(msg) >= 2 and msg[0] == 'system':
                                system_msg = {'role': 'system', 'content': msg[1]}
                                break
                        
                        if system_msg:
                            prompt_text = system_msg.get('content', '')
                        else:
                            # Fallback: concatenate all messages
                            texts = []
                            for msg in langchain_result:
                                if isinstance(msg, dict):
                                    texts.append(msg.get('content', ''))
                                elif isinstance(msg, (tuple, list)) and len(msg) >= 2:
                                    texts.append(str(msg[1]))
                                else:
                                    texts.append(str(msg))
                            prompt_text = ' '.join(texts)
                    else:
                        prompt_text = ""
                else:
                    prompt_text = str(langchain_result)
                
                return {
                    "prompt": prompt_text,
                    "config": prompt_obj.config or {}
                }
            except Exception as e:
                logger.warning(f"Failed to fetch prompt config for '{name}': {e}")
        
        # Fallback with default config
        return {
            "prompt": self._get_local_prompt(name),
            "config": {"model": "gpt-4o", "temperature": 0.7}
        }
    
    def format_prompt(self, name: str, variables: Dict[str, Any], 
                     label: str = "production") -> str:
        """
        Get and format a prompt with variables
        
        Args:
            name: Prompt name
            variables: Dictionary of variables to substitute
            label: Version label
            
        Returns:
            Formatted prompt string
        """
        prompt_template = self.get_prompt(name, label)
        
        # Ensure we have a string to format
        if not isinstance(prompt_template, str):
            logger.error(f"Prompt '{name}' returned non-string type: {type(prompt_template)}")
            prompt_template = str(prompt_template)
        
        # Format the prompt with variables
        try:
            formatted = prompt_template.format(**variables)
            return formatted
        except (KeyError, AttributeError) as e:
            logger.error(f"Error formatting prompt '{name}': {e}")
            # Fallback: partial substitution
            for key, value in variables.items():
                try:
                    prompt_template = prompt_template.replace(f"{{{key}}}", str(value))
                except Exception:
                    pass
            return prompt_template
    
    def _get_local_prompt(self, name: str) -> str:
        """
        Get prompt from local file as fallback
        
        Args:
            name: Prompt name
            
        Returns:
            Prompt text from local file
        """
        # Map prompt names to local files
        name_to_file = {
            "gtd-coach-system": "system.txt",  # Legacy name
            "gtd-coach-system-v2": "system.txt",  # New name with critical instructions
            "gtd-coach-firm": "firm.txt",
            "gtd-coach-simple": "simple.txt",
            "gtd-coach-fallback": "fallback.txt",
            "gtd-weekly-review-system": "system.txt",  # Default to system
            "gtd-phase-completion": None,  # Will use hardcoded
            "gtd-evaluation-task-extraction": None,
            "gtd-evaluation-memory-relevance": None,
            "gtd-evaluation-coaching-quality": None,
            "gtd-daily-capture": None,
            "gtd-adhd-intervention": None,
            "gtd-llm-self-evaluation": None
        }
        
        file_name = name_to_file.get(name)
        
        if file_name:
            file_path = self.local_prompts_dir / file_name
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                logger.debug(f"Loaded prompt '{name}' from local file")
                return content
        
        # Hardcoded fallbacks for embedded prompts
        fallback_prompts = {
            "gtd-phase-completion": """Phase Complete: {phase}
{separator}
{summary}

Time remaining: {time_remaining} minutes

Ready to continue to next phase?""",
            
            "gtd-evaluation-task-extraction": """You are evaluating task extraction accuracy.
User said: {user_input}
Tasks extracted: {extracted_tasks}
Score (0.0-1.0) and provide JSON response.""",
            
            "gtd-weekly-review-system": """You are a GTD coach helping with a weekly review.
Current phase: {current_phase}
Guide the user through the process.""",
            
            "gtd-daily-capture": """Daily GTD capture session.
Time limit: {time_limit} minutes
What's on your mind?""",
            
            "gtd-adhd-intervention": """ADHD pattern detected: {pattern_type}
Suggested intervention: {intervention_text}
What would you like to do?"""
        }
        
        if name in fallback_prompts:
            logger.debug(f"Using hardcoded fallback for prompt '{name}'")
            return fallback_prompts[name]
        
        # Ultimate fallback
        logger.warning(f"No prompt found for '{name}', using generic fallback")
        return "Please provide your input:"


# Singleton instance
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get or create the singleton PromptManager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager