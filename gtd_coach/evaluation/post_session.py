#!/usr/bin/env python3
"""
Post-Session Batch Evaluator for GTD Coach

Evaluates coach interactions after session completion without impacting user experience.
Uses fire-and-forget pattern for non-blocking evaluation.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class PostSessionEvaluator:
    """Evaluates GTD Coach sessions using LLM-as-a-Judge pattern"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize evaluator with configuration
        
        Args:
            config_path: Path to evaluation config file
        """
        self.config = self._load_config(config_path)
        self.evaluation_results = []
        self.session_id = None
        
        # Initialize clients based on config
        self._init_clients()
        
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load evaluation configuration"""
        if not config_path:
            config_path = Path.home() / "gtd-coach" / "config" / "evaluation" / "judge_config.yaml"
        
        # Default configuration
        default_config = {
            "enabled": True,
            "mode": "post_session",
            "models": {
                "screening": "local-llama-3.1-8b",
                "task_extraction": "gpt-4o-mini",
                "memory_relevance": "gpt-4o-mini",
                "coaching_quality": "gpt-4o"
            },
            "thresholds": {
                "task_extraction": 0.8,
                "memory_relevance": 0.6,
                "coaching_quality": 0.7
            },
            "batching": {
                "size": 5,
                "timeout": 10.0
            },
            "fallback": {
                "use_local": True,
                "timeout": 5.0
            }
        }
        
        # Try to load from file
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config and 'evaluation' in loaded_config:
                        default_config.update(loaded_config['evaluation'])
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def _init_clients(self):
        """Initialize LLM clients based on configuration"""
        # Local LLM client (LM Studio)
        self.local_client = OpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio"
        )
        
        # Cloud LLM client (OpenAI)
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            self.cloud_client = OpenAI(api_key=openai_key)
        else:
            logger.warning("No OpenAI API key found, using local model only")
            self.cloud_client = None
            
    def evaluate_session(self, session_data: Dict[str, Any]) -> None:
        """
        Evaluate a completed session (fire-and-forget)
        
        Args:
            session_data: Complete session data including interactions
        """
        if not self.config.get('enabled', True):
            logger.info("Evaluation disabled, skipping")
            return
            
        self.session_id = session_data.get('session_id')
        logger.info(f"Starting post-session evaluation for {self.session_id}")
        
        # Queue evaluation tasks asynchronously (fire-and-forget)
        try:
            # Create new event loop for background processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Schedule evaluation without waiting
            loop.run_in_executor(None, self._process_evaluations_sync, session_data)
            
            logger.info(f"Evaluation queued for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to queue evaluation: {e}")
    
    def _process_evaluations_sync(self, session_data: Dict[str, Any]):
        """Synchronous wrapper for evaluation processing"""
        try:
            # Run async evaluation in new loop
            asyncio.run(self._process_evaluations(session_data))
        except Exception as e:
            logger.error(f"Evaluation processing failed: {e}")
    
    async def _process_evaluations(self, session_data: Dict[str, Any]):
        """
        Process evaluations asynchronously in batches
        
        Args:
            session_data: Complete session data
        """
        interactions = session_data.get('interactions', [])
        if not interactions:
            logger.warning("No interactions to evaluate")
            return
        
        logger.info(f"Starting evaluation of {len(interactions)} interactions")
        
        # Filter interactions to priority phases to reduce costs
        priority_phases = self.config.get('priority_phases', [])
        if priority_phases:
            filtered_interactions = [i for i in interactions 
                                    if i.get('phase') in priority_phases]
            logger.info(f"Filtered to {len(filtered_interactions)} priority interactions")
            interactions = filtered_interactions if filtered_interactions else interactions[:2]
        
        # Batch interactions
        batch_size = self.config['batching']['size']
        batches = [interactions[i:i + batch_size] 
                  for i in range(0, len(interactions), batch_size)]
        
        # Process each batch
        for batch_idx, batch in enumerate(batches):
            logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} interactions")
            
            # Create evaluation tasks for this batch
            tasks = []
            for interaction in batch:
                tasks.append(self._evaluate_interaction(interaction))
            
            # Wait for batch completion with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.config['batching']['timeout']
                )
                
                # Store results
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Evaluation failed for interaction {idx}: {result}")
                        # Add placeholder result
                        self.evaluation_results.append({
                            'error': str(result),
                            'fallback': True,
                            'phase': batch[idx].get('phase')
                        })
                    else:
                        logger.info(f"Successfully evaluated interaction {idx}")
                        self.evaluation_results.append(result)
                        
            except asyncio.TimeoutError:
                logger.warning(f"Batch {batch_idx + 1} timed out after {self.config['batching']['timeout']}s")
                # Add timeout placeholder
                for interaction in batch:
                    self.evaluation_results.append({
                        'error': 'Batch timeout',
                        'fallback': True,
                        'phase': interaction.get('phase')
                    })
        
        logger.info(f"Completed evaluation with {len(self.evaluation_results)} results")
        
        # Save evaluation results
        await self._save_results(session_data)
        
    async def _evaluate_interaction(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single interaction
        
        Args:
            interaction: Single interaction data
            
        Returns:
            Evaluation scores and reasoning
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'phase': interaction.get('phase'),
            'user_input': interaction.get('user_input'),
            'coach_response': interaction.get('coach_response')
        }
        
        # Evaluate each dimension
        try:
            # Task extraction accuracy
            if interaction.get('extracted_tasks'):
                task_score = await self._evaluate_task_extraction(interaction)
                results['task_extraction'] = task_score
            
            # Memory relevance
            if interaction.get('retrieved_memories'):
                memory_score = await self._evaluate_memory_relevance(interaction)
                results['memory_relevance'] = memory_score
            
            # Coaching quality (sample only to control costs)
            if interaction.get('phase') in ['MIND_SWEEP', 'PRIORITIZATION']:
                quality_score = await self._evaluate_coaching_quality(interaction)
                results['coaching_quality'] = quality_score
                
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            results['error'] = str(e)
        
        return results
    
    async def _evaluate_task_extraction(self, interaction: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate task extraction accuracy"""
        # Use prompt manager to get evaluation prompt
        from gtd_coach.prompts.manager import get_prompt_manager
        prompt_manager = get_prompt_manager()
        
        prompt = prompt_manager.format_prompt(
            "gtd-evaluation-task-extraction",
            {
                "user_input": interaction.get('user_input', ''),
                "extracted_tasks": json.dumps(interaction.get('extracted_tasks', []))
            }
        )
        
        try:
            # Try cloud model first
            if self.cloud_client:
                response = self.cloud_client.chat.completions.create(
                    model=self.config['models']['task_extraction'],
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=200
                )
            else:
                # Fallback to local
                response = self.local_client.chat.completions.create(
                    model="meta-llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=200
                )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Task extraction evaluation failed: {e}")
            return {"score": 0.5, "error": str(e)}
    
    async def _evaluate_memory_relevance(self, interaction: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate memory relevance"""
        # Use prompt manager to get evaluation prompt
        from gtd_coach.prompts.manager import get_prompt_manager
        prompt_manager = get_prompt_manager()
        
        prompt = prompt_manager.format_prompt(
            "gtd-evaluation-memory-relevance",
            {
                "phase": interaction.get('phase', ''),
                "user_input": interaction.get('user_input', ''),
                "retrieved_memories": json.dumps(interaction.get('retrieved_memories', [])),
                "coach_response": interaction.get('coach_response', '')
            }
        )
        
        try:
            # Try cloud model first
            if self.cloud_client:
                response = self.cloud_client.chat.completions.create(
                    model=self.config['models']['memory_relevance'],
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=200
                )
            else:
                # Fallback to local
                response = self.local_client.chat.completions.create(
                    model="meta-llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=200
                )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Memory relevance evaluation failed: {e}")
            return {"score": 0.5, "error": str(e)}
    
    async def _evaluate_coaching_quality(self, interaction: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate coaching quality for ADHD appropriateness"""
        # Use prompt manager to get evaluation prompt
        from gtd_coach.prompts.manager import get_prompt_manager
        prompt_manager = get_prompt_manager()
        
        # Get fully formatted prompt from Langfuse
        prompt = prompt_manager.format_prompt(
            "gtd-evaluation-coaching-quality",
            {
                "phase": interaction.get('phase', ''),
                "time_remaining": interaction.get('time_remaining', 'unknown'),
                "user_input": interaction.get('user_input', ''),
                "coach_response": interaction.get('coach_response', '')
            }
        )
        
        try:
            # Use more sophisticated model for quality evaluation
            if self.cloud_client:
                response = self.cloud_client.chat.completions.create(
                    model=self.config['models']['coaching_quality'],
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=300
                )
            else:
                # Fallback to local
                response = self.local_client.chat.completions.create(
                    model="meta-llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=300
                )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Coaching quality evaluation failed: {e}")
            return {"score": 0.5, "error": str(e)}
    
    async def _save_results(self, session_data: Dict[str, Any]):
        """Save evaluation results to file and Langfuse"""
        # Save to local file
        results_dir = Path.home() / "gtd-coach" / "data" / "evaluations"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = results_dir / f"eval_{self.session_id}.json"
        
        evaluation_summary = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'session_data': {
                'phase_count': len(set(i.get('phase') for i in session_data.get('interactions', []))),
                'interaction_count': len(session_data.get('interactions', [])),
                'duration': session_data.get('duration')
            },
            'evaluations': self.evaluation_results,
            'summary': self._calculate_summary()
        }
        
        with open(results_file, 'w') as f:
            json.dump(evaluation_summary, f, indent=2)
        
        logger.info(f"Evaluation results saved to {results_file}")
        
        # Send to Langfuse if configured
        await self._send_to_langfuse(evaluation_summary)
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from evaluation results with rule-based metrics"""
        if not self.evaluation_results:
            return {}
        
        summary = {
            'total_evaluations': len(self.evaluation_results),
            'average_scores': {},
            'below_threshold': [],
            'rule_based_scores': {}
        }
        
        # Calculate averages for each metric
        for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
            scores = [r.get(metric, {}).get('score', 0) 
                     for r in self.evaluation_results 
                     if metric in r]
            
            if scores:
                avg_score = sum(scores) / len(scores)
                summary['average_scores'][metric] = round(avg_score, 3)
                
                # Check against threshold
                threshold = self.config['thresholds'].get(metric, 0.5)
                if avg_score < threshold:
                    summary['below_threshold'].append({
                        'metric': metric,
                        'score': avg_score,
                        'threshold': threshold
                    })
        
        # Add rule-based evaluations (no LLM needed)
        summary['rule_based_scores'] = self._calculate_rule_based_scores()
        
        return summary
    
    def _calculate_rule_based_scores(self) -> Dict[str, float]:
        """
        Calculate rule-based scores without using LLMs
        Simple, fast metrics for session effectiveness
        """
        scores = {}
        
        # Calculate task capture effectiveness
        # Count how many interactions resulted in task extraction
        interactions_with_tasks = sum(
            1 for r in self.evaluation_results 
            if 'task_extraction' in r and r.get('phase') == 'MIND_SWEEP'
        )
        total_mind_sweep = sum(
            1 for r in self.evaluation_results 
            if r.get('phase') == 'MIND_SWEEP'
        )
        
        if total_mind_sweep > 0:
            scores['task_capture_rate'] = interactions_with_tasks / total_mind_sweep
        else:
            scores['task_capture_rate'] = 0.0
        
        # Calculate interrupt handling quality
        # Good interrupts happen at phase boundaries, bad ones mid-phase
        good_interrupts = sum(
            1 for r in self.evaluation_results
            if r.get('phase') in ['STARTUP', 'WRAP_UP'] and r.get('user_input')
        )
        total_interrupts = sum(
            1 for r in self.evaluation_results
            if r.get('user_input')
        )
        
        if total_interrupts > 0:
            scores['interrupt_quality'] = good_interrupts / total_interrupts
        else:
            scores['interrupt_quality'] = 1.0  # No interrupts is good
        
        # Calculate phase completion rate
        expected_phases = ['STARTUP', 'MIND_SWEEP', 'PROJECT_REVIEW', 'PRIORITIZATION', 'WRAP_UP']
        completed_phases = set(r.get('phase') for r in self.evaluation_results if r.get('phase'))
        scores['phase_completion_rate'] = len(completed_phases) / len(expected_phases)
        
        # Calculate session completion
        has_wrap_up = any(r.get('phase') == 'WRAP_UP' for r in self.evaluation_results)
        scores['session_completed'] = 1.0 if has_wrap_up else 0.0
        
        # Calculate memory utilization (if available)
        interactions_with_memory = sum(
            1 for r in self.evaluation_results
            if 'memory_relevance' in r
        )
        total_interactions = len(self.evaluation_results)
        
        if total_interactions > 0:
            scores['memory_utilization'] = interactions_with_memory / total_interactions
        else:
            scores['memory_utilization'] = 0.0
        
        # Calculate overall session effectiveness
        # Weighted average of key metrics
        effectiveness = (
            scores['session_completed'] * 0.3 +
            scores['phase_completion_rate'] * 0.3 +
            scores['task_capture_rate'] * 0.2 +
            scores['interrupt_quality'] * 0.1 +
            scores['memory_utilization'] * 0.1
        )
        scores['session_effectiveness'] = round(effectiveness, 3)
        
        return scores
    
    async def _send_to_langfuse(self, evaluation_summary: Dict[str, Any]):
        """Send evaluation scores to Langfuse"""
        try:
            # Import Langfuse if available
            from langfuse import Langfuse
            
            # Check for API keys
            if not os.environ.get('LANGFUSE_PUBLIC_KEY'):
                logger.info("Langfuse not configured, skipping score upload")
                return
            
            langfuse = Langfuse()
            
            # Send aggregate scores
            for metric, score in evaluation_summary['summary'].get('average_scores', {}).items():
                langfuse.create_score(
                    trace_id=self.session_id,
                    name=f"eval_{metric}",
                    value=score,
                    data_type="NUMERIC",
                    comment=f"Post-session evaluation for {metric}"
                )
            
            # Send rule-based scores (fast, no LLM needed)
            for metric, score in evaluation_summary['summary'].get('rule_based_scores', {}).items():
                langfuse.create_score(
                    trace_id=self.session_id,
                    name=f"rule_{metric}",
                    value=score,
                    data_type="NUMERIC",
                    comment=f"Rule-based evaluation for {metric}"
                )
            
            logger.info(f"Sent {len(evaluation_summary['summary'].get('average_scores', {}))} LLM scores and "
                      f"{len(evaluation_summary['summary'].get('rule_based_scores', {}))} rule-based scores to Langfuse")
            
        except ImportError:
            logger.warning("Langfuse not installed, skipping score upload")
        except Exception as e:
            logger.error(f"Failed to send scores to Langfuse: {e}")


def evaluate_session_async(session_data: Dict[str, Any]):
    """
    Helper function to evaluate a session asynchronously
    
    Args:
        session_data: Complete session data
    """
    evaluator = PostSessionEvaluator()
    evaluator.evaluate_session(session_data)