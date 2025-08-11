#!/usr/bin/env python3
"""
Adaptive Response Manager for GTD Coach
Adapts coach responses based on detected user state
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AdaptiveResponseManager:
    """Adapts coach responses based on user state"""
    
    # Adaptation configurations for different states
    ADAPTATIONS = {
        'low_energy': {
            'prompt_modifier': "Be very concise and encouraging. ",
            'max_tokens': 100,
            'temperature': 0.7,
            'encouragement': 'high',
            'pace_modifier': "Take your time. No rush. "
        },
        'high_confusion': {
            'prompt_modifier': "Use simple, clear language. Break things into small steps. ",
            'max_tokens': 150,
            'temperature': 0.6,
            'example_mode': True,
            'structure_modifier': "Number each point clearly. "
        },
        'low_engagement': {
            'prompt_modifier': "Be energetic and celebratory! ",
            'max_tokens': 120,
            'temperature': 0.9,
            'celebration_mode': True,
            'variety_modifier': "Mix things up a bit. "
        },
        'high_stress': {
            'prompt_modifier': "Stay calm and supportive. ",
            'max_tokens': 100,
            'temperature': 0.6,
            'tone': 'calming',
            'grounding_reminder': True
        },
        'needs_break': {
            'prompt_modifier': "Gently suggest a quick break if needed. ",
            'max_tokens': 80,
            'break_suggestion': True
        }
    }
    
    # Phase-specific adaptation overrides
    PHASE_ADAPTATIONS = {
        'MIND_SWEEP': {
            'low_energy': {
                'prompt_modifier': "Just capture what comes to mind, no need to be complete. "
            },
            'high_confusion': {
                'prompt_modifier': "Let's just get things out of your head. Don't worry about organizing. "
            }
        },
        'PROJECT_REVIEW': {
            'low_energy': {
                'prompt_modifier': "Quick decisions only - we can revisit later. "
            },
            'low_engagement': {
                'prompt_modifier': "You're doing great! Each decision moves you forward! "
            }
        },
        'PRIORITIZATION': {
            'high_stress': {
                'prompt_modifier': "Remember: not everything needs to be an A priority. Be kind to yourself. "
            }
        }
    }
    
    def __init__(self):
        """Initialize the adaptive response manager"""
        self.current_adaptations = {}
        self.adaptation_history = []
        self.adaptation_counts = {}
    
    def get_adaptations(self, user_state: Dict[str, Any], phase: Optional[str] = None) -> Dict[str, Any]:
        """
        Get adaptations based on user state and current phase
        
        Args:
            user_state: Current user state from UserStateMonitor
            phase: Current phase name (optional)
            
        Returns:
            Dictionary of adaptations to apply
        """
        adaptations = {
            'prompt_modifiers': [],
            'settings': {},
            'flags': set()
        }
        
        # Check each state condition and apply adaptations
        if user_state.get('energy_level') == 'low':
            self._apply_adaptation('low_energy', adaptations, phase)
        
        if user_state.get('confusion_level', 0) > 0.5:
            self._apply_adaptation('high_confusion', adaptations, phase)
        
        if user_state.get('engagement_level', 1.0) < 0.6:
            self._apply_adaptation('low_engagement', adaptations, phase)
        
        if user_state.get('stress_indicators', 0) >= 2:
            self._apply_adaptation('high_stress', adaptations, phase)
        
        if user_state.get('needs_break'):
            self._apply_adaptation('needs_break', adaptations, phase)
        
        # Combine prompt modifiers
        if adaptations['prompt_modifiers']:
            adaptations['combined_prompt_modifier'] = ' '.join(adaptations['prompt_modifiers'])
        
        # Log adaptations
        if adaptations['prompt_modifiers'] or adaptations['settings']:
            logger.info(f"Applying adaptations for phase {phase}: {adaptations['flags']}")
            self._record_adaptation(user_state, adaptations, phase)
        
        self.current_adaptations = adaptations
        return adaptations
    
    def _apply_adaptation(self, state_type: str, adaptations: Dict, phase: Optional[str]):
        """
        Apply specific adaptation based on state type
        
        Args:
            state_type: Type of state (e.g., 'low_energy')
            adaptations: Adaptations dictionary to update
            phase: Current phase name
        """
        # Get base adaptation
        base_adapt = self.ADAPTATIONS.get(state_type, {})
        
        # Check for phase-specific overrides
        if phase and phase in self.PHASE_ADAPTATIONS:
            phase_adapt = self.PHASE_ADAPTATIONS[phase].get(state_type, {})
            base_adapt = {**base_adapt, **phase_adapt}
        
        # Apply adaptations
        if 'prompt_modifier' in base_adapt:
            adaptations['prompt_modifiers'].append(base_adapt['prompt_modifier'])
        
        if 'max_tokens' in base_adapt:
            adaptations['settings']['max_tokens'] = base_adapt['max_tokens']
        
        if 'temperature' in base_adapt:
            adaptations['settings']['temperature'] = base_adapt['temperature']
        
        # Set flags for special modes
        for key in ['example_mode', 'celebration_mode', 'grounding_reminder', 'break_suggestion']:
            if base_adapt.get(key):
                adaptations['flags'].add(key)
        
        # Track this adaptation
        self.adaptation_counts[state_type] = self.adaptation_counts.get(state_type, 0) + 1
    
    def adapt_prompt(self, base_prompt: str, adaptations: Dict[str, Any]) -> str:
        """
        Apply adaptations to a prompt
        
        Args:
            base_prompt: Original prompt text
            adaptations: Adaptations to apply
            
        Returns:
            Adapted prompt
        """
        # Add prompt modifiers at the beginning
        if adaptations.get('combined_prompt_modifier'):
            adapted_prompt = adaptations['combined_prompt_modifier'] + base_prompt
        else:
            adapted_prompt = base_prompt
        
        # Add celebration if needed (before the text)
        if 'celebration_mode' in adaptations.get('flags', set()):
            adapted_prompt = "🎉 " + adapted_prompt
        
        # Add examples if needed
        if 'example_mode' in adaptations.get('flags', set()):
            adapted_prompt += "\n\nFor example: Start with just one thing that's on your mind right now."
        
        # Add break reminder if needed
        if 'break_suggestion' in adaptations.get('flags', set()):
            adapted_prompt += "\n\n(Feel free to take a quick stretch if you need it!)"
        
        return adapted_prompt
    
    def adapt_settings(self, base_settings: Dict[str, Any], adaptations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply adaptations to LLM settings
        
        Args:
            base_settings: Original settings
            adaptations: Adaptations to apply
            
        Returns:
            Adapted settings
        """
        adapted_settings = base_settings.copy()
        
        # Apply setting overrides
        if 'settings' in adaptations:
            adapted_settings.update(adaptations['settings'])
        
        return adapted_settings
    
    def _record_adaptation(self, user_state: Dict, adaptations: Dict, phase: Optional[str]):
        """Record adaptation for analysis"""
        self.adaptation_history.append({
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'user_state': user_state,
            'adaptations_applied': {
                'modifiers': adaptations.get('prompt_modifiers', []),
                'settings': adaptations.get('settings', {}),
                'flags': list(adaptations.get('flags', set()))
            }
        })
        
        # Keep only last 50 adaptations
        if len(self.adaptation_history) > 50:
            self.adaptation_history.pop(0)
    
    def get_adaptation_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about adaptations
        
        Returns:
            Dictionary of adaptation metrics
        """
        return {
            'total_adaptations': len(self.adaptation_history),
            'adaptation_counts': self.adaptation_counts,
            'current_adaptations': self.current_adaptations,
            'most_common': max(self.adaptation_counts.items(), key=lambda x: x[1])[0] 
                          if self.adaptation_counts else None
        }
    
    def should_suggest_break(self, phase_duration: float, user_state: Dict[str, Any]) -> bool:
        """
        Determine if a break should be suggested
        
        Args:
            phase_duration: How long the current phase has been running (seconds)
            user_state: Current user state
            
        Returns:
            True if break should be suggested
        """
        # Suggest break if phase is taking too long and user shows fatigue
        if phase_duration > 600 and user_state.get('energy_level') == 'low':  # 10+ minutes
            return True
        
        # Suggest break if high stress and confusion
        if user_state.get('stress_indicators', 0) >= 2 and user_state.get('confusion_level', 0) > 0.5:
            return True
        
        return False
    
    def get_encouragement_message(self, phase: str, progress: float) -> str:
        """
        Get an encouraging message based on phase and progress
        
        Args:
            phase: Current phase name
            progress: Progress through phase (0-1)
            
        Returns:
            Encouragement message
        """
        messages = {
            'MIND_SWEEP': {
                0.5: "Great job getting things out of your head!",
                0.8: "Almost done with mind sweep - you're doing fantastic!",
                1.0: "Excellent mind sweep! Your brain must feel lighter!"
            },
            'PROJECT_REVIEW': {
                0.3: "Good progress on your projects!",
                0.6: "You're making great decisions!",
                0.8: "Almost through - each decision counts!",
                0.9: "Almost through - each decision counts!"
            },
            'PRIORITIZATION': {
                0.5: "Nice work prioritizing!",
                1.0: "Priorities set - you're ready for the week!"
            },
            'WRAP_UP': {
                1.0: "Amazing job completing your review! 🎉"
            }
        }
        
        phase_messages = messages.get(phase, {})
        
        # Find appropriate message based on progress
        for threshold in sorted(phase_messages.keys()):
            if progress >= threshold:
                return phase_messages[threshold]
        
        return "You're doing great!"