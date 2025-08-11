#!/usr/bin/env python3
"""
N-of-1 Experiment Framework for GTD Coach
Manages sequential single-subject experiments with ABAB design
"""

import os
import logging
import yaml
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class NOf1Experimenter:
    """Manages sequential single-subject experiments for GTD Coach"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the experimenter with configuration
        
        Args:
            config_path: Path to experiment schedule YAML file
        """
        if not config_path:
            # Try multiple possible locations
            possible_paths = [
                Path("/app/config/experiments/n_of_1_schedule.yaml"),  # Docker location
                Path.home() / "gtd-coach" / "config" / "experiments" / "n_of_1_schedule.yaml",  # Home location
                Path("config/experiments/n_of_1_schedule.yaml"),  # Relative location
                Path(__file__).parent.parent.parent / "config" / "experiments" / "n_of_1_schedule.yaml"  # Package relative
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
            else:
                # Use default if none found
                config_path = Path.home() / "gtd-coach" / "config" / "experiments" / "n_of_1_schedule.yaml"
        
        self.config_path = config_path
        self.experiments = []
        self.current_week = None
        self.current_experiment = None
        self.session_count = 0
        
        # Load experiment configuration
        self.load_configuration()
        
        # Determine current week and experiment
        self.update_current_experiment()
    
    def load_configuration(self) -> None:
        """Load experiment schedule from YAML configuration"""
        if not self.config_path.exists():
            logger.warning(f"Experiment config not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.experiments = config.get('experiments', [])
            self.analysis_config = config.get('analysis', {})
            self.override_config = config.get('override', {})
            self.success_criteria = config.get('success_criteria', {})
            
            logger.info(f"Loaded {len(self.experiments)} experiments from configuration")
            
        except Exception as e:
            logger.error(f"Failed to load experiment configuration: {e}")
    
    def update_current_experiment(self) -> None:
        """Determine current week and active experiment"""
        # Get current ISO week
        now = datetime.now()
        self.current_week = now.strftime("%G-W%V")
        week_number = int(now.strftime("%V"))
        
        # Find experiment for current week (cycling through if needed)
        if self.experiments:
            experiment_index = (week_number - 1) % len(self.experiments)
            self.current_experiment = self.experiments[experiment_index]
            
            logger.info(f"Current experiment (week {self.current_week}): {self.current_experiment.get('name')}")
    
    def get_current_experiment(self) -> Optional[Dict[str, Any]]:
        """
        Get the current week's experiment configuration
        
        Returns:
            Current experiment dict or None if no experiments configured
        """
        if not self.current_experiment:
            self.update_current_experiment()
        
        return self.current_experiment
    
    def get_condition_for_session(self, session_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get experimental condition for current session using ABAB rotation
        
        Args:
            session_number: Session number within week (auto-increments if not provided)
            
        Returns:
            Dictionary with condition configuration
        """
        if not self.current_experiment:
            return {
                "variable": "control",
                "value": "baseline",
                "config": {}
            }
        
        # Use provided session number or increment counter
        if session_number is None:
            self.session_count += 1
            session_number = self.session_count
        
        # Get conditions for current experiment
        conditions = self.current_experiment.get('conditions', [])
        if not conditions:
            return {
                "variable": self.current_experiment.get('variable', 'unknown'),
                "value": "default",
                "config": {}
            }
        
        # ABAB pattern: cycle through conditions
        condition_index = (session_number - 1) % len(conditions)
        condition = conditions[condition_index]
        
        return {
            "variable": self.current_experiment.get('variable'),
            "value": condition.get('value'),
            "description": condition.get('description'),
            "config": condition.get('config', {}),
            "session_in_pattern": condition_index + 1,  # Position in ABAB
            "pattern_complete": condition_index == len(conditions) - 1
        }
    
    def should_override(self) -> bool:
        """
        Check if user has requested override via environment variable
        
        Returns:
            True if override is requested
        """
        if not self.override_config.get('enabled', True):
            return False
        
        # Check for any override environment variables
        override_vars = self.override_config.get('environment_variables', [])
        for var in override_vars:
            if os.environ.get(var):
                return True
        
        return False
    
    def get_override_value(self) -> Optional[Dict[str, Any]]:
        """
        Get override configuration from environment variables
        
        Returns:
            Override configuration or None if no override
        """
        if not self.should_override():
            return None
        
        # Map environment variables to experiment variables
        var_mapping = {
            "EXPERIMENT_OVERRIDE_MEMORY": "memory_retrieval_strategy",
            "EXPERIMENT_OVERRIDE_TEMPERATURE": "temperature_profile",
            "EXPERIMENT_OVERRIDE_STYLE": "coaching_style",
            "EXPERIMENT_OVERRIDE_LENGTH": "prompt_length",
            "EXPERIMENT_OVERRIDE_STRUCTURE": "prompt_structure",
            "EXPERIMENT_OVERRIDE_ADHD": "adhd_language_pattern",
            "EXPERIMENT_OVERRIDE_INTERVENTIONS": "jitai_enabled",
            "EXPERIMENT_OVERRIDE_ADAPTIVE": "adaptive_behavior"
        }
        
        for env_var, exp_var in var_mapping.items():
            override_value = os.environ.get(env_var)
            if override_value:
                logger.info(f"Override detected: {exp_var} = {override_value}")
                return {
                    "variable": exp_var,
                    "value": override_value,
                    "config": {},
                    "is_override": True
                }
        
        return None
    
    def get_experiment_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for current experiment to include in traces
        
        Returns:
            Dictionary of experiment metadata
        """
        condition = self.get_condition_for_session()
        
        metadata = {
            "experiment_week": self.current_week,
            "experiment_name": self.current_experiment.get('name') if self.current_experiment else None,
            "experiment_variable": condition.get('variable'),
            "experiment_value": condition.get('value'),
            "experiment_description": condition.get('description'),
            "session_in_pattern": condition.get('session_in_pattern'),
            "pattern_complete": condition.get('pattern_complete', False)
        }
        
        # Add override flag if applicable
        if self.should_override():
            metadata["experiment_override"] = True
            override = self.get_override_value()
            if override:
                metadata["override_variable"] = override.get('variable')
                metadata["override_value"] = override.get('value')
        
        return metadata
    
    def get_metrics_focus(self) -> List[str]:
        """
        Get the metrics to focus on for current experiment
        
        Returns:
            List of metric names to prioritize
        """
        if not self.current_experiment:
            return ["memory_relevance_score", "time_to_first_capture", "task_followthrough_rate"]
        
        return self.current_experiment.get('metrics_focus', [])
    
    def apply_experiment_config(self, coach_instance: Any) -> None:
        """
        Apply current experimental condition to coach instance
        
        Args:
            coach_instance: GTDCoach instance to configure
        """
        # Check for override first
        override = self.get_override_value()
        if override:
            condition = override
            logger.info(f"Applying override: {condition}")
        else:
            condition = self.get_condition_for_session()
            logger.info(f"Applying condition: {condition.get('value')} for {condition.get('variable')}")
        
        # Store experiment info on coach instance
        coach_instance.current_experiment_variable = condition.get('variable')
        coach_instance.current_experiment_value = condition.get('value')
        
        # Apply configuration based on variable type
        config = condition.get('config', {})
        variable = condition.get('variable')
        
        if variable == "memory_retrieval_strategy":
            self._apply_memory_strategy(coach_instance, config)
        elif variable == "temperature_profile":
            self._apply_temperature_profile(coach_instance, config)
        elif variable == "coaching_style":
            self._apply_coaching_style(coach_instance, config)
        elif variable == "prompt_length":
            self._apply_prompt_length(coach_instance, config)
        elif variable == "prompt_structure":
            self._apply_prompt_structure(coach_instance, config)
        elif variable == "adhd_language_pattern":
            self._apply_adhd_pattern(coach_instance, config)
        elif variable == "jitai_enabled":
            self._apply_intervention_config(coach_instance, config)
        elif variable == "adaptive_behavior":
            self._apply_adaptive_config(coach_instance, config)
    
    def _apply_memory_strategy(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply memory retrieval strategy configuration"""
        if hasattr(coach, 'memory'):
            coach.memory.retrieval_strategy = config.get('strategy', 'recency_weighted')
            coach.memory.retrieval_limit = config.get('limit', 5)
            
            if 'weight_factor' in config:
                coach.memory.recency_weight = config['weight_factor']
            if 'min_occurrences' in config:
                coach.memory.frequency_threshold = config['min_occurrences']
    
    def _apply_temperature_profile(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply temperature settings per phase"""
        if hasattr(coach, 'phase_settings'):
            for phase, temp in config.items():
                if phase in coach.phase_settings:
                    if temp == "adaptive":
                        # Enable adaptive temperature
                        coach.phase_settings[phase]['adaptive_temperature'] = True
                    else:
                        coach.phase_settings[phase]['temperature'] = temp
                        coach.phase_settings[phase]['adaptive_temperature'] = False
    
    def _apply_coaching_style(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply coaching style configuration"""
        style = config.get('prompt_style', 'directive')
        
        # Override prompt tone selection
        if style == 'directive':
            coach.prompt_tone = 'firm'
        elif style == 'socratic':
            coach.prompt_tone = 'gentle'
        
        # Store additional style config
        coach.time_reminder_frequency = config.get('time_reminders', 'moderate')
        coach.structure_emphasis = config.get('structure_emphasis', 'medium')
    
    def _apply_prompt_length(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply prompt length configuration"""
        max_tokens = config.get('max_tokens', 300)
        
        # Apply to all phases
        if hasattr(coach, 'phase_settings'):
            for phase in coach.phase_settings:
                coach.phase_settings[phase]['max_tokens'] = max_tokens
        
        coach.prompt_detail_level = config.get('detail_level', 'balanced')
    
    def _apply_prompt_structure(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply prompt structure configuration"""
        coach.prompt_format = config.get('format', 'narrative')
        coach.use_visual_breaks = config.get('visual_breaks', False)
        coach.hierarchy_style = config.get('hierarchy', 'implicit')
    
    def _apply_adhd_pattern(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply ADHD language pattern configuration"""
        coach.time_emphasis = config.get('time_emphasis', 'moderate')
        coach.urgency_level = config.get('urgency_level', 'balanced')
        coach.celebration_style = config.get('celebration_style', 'both')
    
    def _apply_intervention_config(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply just-in-time intervention configuration"""
        # Enable or disable interventions based on value
        # For override, check if value is 'on' or config has interventions_enabled
        if hasattr(coach, 'current_experiment_value'):
            if coach.current_experiment_value == 'on':
                coach.interventions_enabled = True
            elif coach.current_experiment_value == 'off':
                coach.interventions_enabled = False
            else:
                coach.interventions_enabled = config.get('interventions_enabled', False)
        else:
            coach.interventions_enabled = config.get('interventions_enabled', False)
        
        # Set intervention type (for future expansion beyond grounding)
        coach.intervention_type = config.get('intervention_type', 'grounding')
        
        # Set cooldown between interventions (in seconds)
        cooldown_minutes = config.get('cooldown_minutes', 10)
        coach.intervention_cooldown = cooldown_minutes * 60
        
        logger.info(f"Interventions {'enabled' if coach.interventions_enabled else 'disabled'} "
                   f"(type: {coach.intervention_type}, cooldown: {cooldown_minutes} min)")
    
    def _apply_adaptive_config(self, coach: Any, config: Dict[str, Any]) -> None:
        """Apply adaptive behavior configuration"""
        # Enable or disable adaptive behavior
        adaptive_enabled = config.get('adaptive_enabled', False)
        
        # Store configuration on coach
        coach.adaptive_enabled = adaptive_enabled
        coach.adapt_prompts = config.get('adapt_prompts', True) if adaptive_enabled else False
        coach.adapt_settings = config.get('adapt_settings', True) if adaptive_enabled else False
        
        # Configure the adaptive managers if available
        if hasattr(coach, 'state_monitor') and hasattr(coach, 'response_adapter'):
            if not adaptive_enabled:
                # Disable adaptations by clearing the monitor
                coach.state_monitor = None
                coach.response_adapter = None
                logger.info("Adaptive behavior disabled for this session")
            else:
                # Ensure they're properly initialized
                if coach.state_monitor is None:
                    from gtd_coach.adaptive import UserStateMonitor, AdaptiveResponseManager
                    coach.state_monitor = UserStateMonitor()
                    coach.response_adapter = AdaptiveResponseManager()
                logger.info("Adaptive behavior enabled with prompt and setting adaptation")
    
    def log_session_start(self) -> None:
        """Log the start of an experimental session"""
        condition = self.get_condition_for_session()
        experiment_name = self.current_experiment.get('name') if self.current_experiment else 'None'
        
        logger.info(f"""
        ===== EXPERIMENT SESSION START =====
        Week: {self.current_week}
        Experiment: {experiment_name}
        Variable: {condition.get('variable')}
        Condition: {condition.get('value')}
        Session in Pattern: {condition.get('session_in_pattern')}/4
        Override Active: {self.should_override()}
        ====================================
        """)
    
    def get_success_criteria(self, metric_name: str) -> Dict[str, float]:
        """
        Get success criteria for a specific metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary with target and improvement threshold
        """
        return self.success_criteria.get(metric_name, {
            "target": None,
            "improvement_threshold": 0.1
        })