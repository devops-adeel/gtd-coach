#!/usr/bin/env python3
"""
Evaluation Criteria and Prompts for LLM-as-a-Judge

Defines the evaluation criteria and prompts for each dimension:
- Task extraction accuracy
- Memory relevance
- Coaching quality
"""

from typing import Dict, Any


class EvaluationCriteria:
    """Manages evaluation criteria and prompts for different dimensions"""
    
    @staticmethod
    def get_task_extraction_prompt(interaction: Dict[str, Any]) -> str:
        """
        Generate prompt for evaluating task extraction accuracy
        
        Args:
            interaction: Interaction data containing user input and extracted tasks
            
        Returns:
            Evaluation prompt string
        """
        return f"""You are an expert evaluator for a GTD (Getting Things Done) coaching system designed for ADHD users.
Your task is to evaluate how accurately the system extracted actionable tasks from the user's input.

CONTEXT:
- Phase: {interaction.get('phase', 'Unknown')}
- This is an ADHD-friendly system, so users may express tasks in scattered or incomplete ways

USER INPUT:
"{interaction.get('user_input', '')}"

EXTRACTED TASKS BY SYSTEM:
{interaction.get('extracted_tasks', [])}

EVALUATION CRITERIA:
1. Completeness: Were ALL actionable items mentioned by the user captured?
2. Accuracy: Are the extracted items actually tasks (not just observations or feelings)?
3. Clarity: Are the extracted tasks clear and actionable?

IMPORTANT CONSIDERATIONS:
- Users with ADHD may mention tasks indirectly or embedded in other thoughts
- Look for implied tasks (e.g., "I'm worried about the presentation" implies "Prepare presentation")
- Some items may be better captured as "clarify" tasks if unclear

SCORING:
- 1.0: Perfect - all tasks captured accurately
- 0.8-0.9: Good - minor task missed or slight inaccuracy
- 0.6-0.7: Adequate - some tasks missed but main ones captured
- 0.4-0.5: Poor - significant tasks missed
- 0.0-0.3: Failed - most tasks missed or wrong

Provide your evaluation in JSON format:
{{
    "score": 0.0-1.0,
    "missed_tasks": ["list any tasks mentioned but not extracted"],
    "incorrect_extractions": ["list any non-tasks that were incorrectly extracted"],
    "suggestions": ["list better ways to phrase extracted tasks if needed"],
    "reasoning": "Brief explanation of your score"
}}"""

    @staticmethod
    def get_memory_relevance_prompt(interaction: Dict[str, Any]) -> str:
        """
        Generate prompt for evaluating memory relevance
        
        Args:
            interaction: Interaction data with memories and context
            
        Returns:
            Evaluation prompt string
        """
        return f"""You are evaluating the relevance and usage of retrieved memories in an ADHD coaching session.
The system uses a memory graph (Graphiti) to retrieve past patterns and information.

CONTEXT:
- Phase: {interaction.get('phase', 'Unknown')}
- Session Week: {interaction.get('session_week', 'Unknown')}
- Time in Phase: {interaction.get('time_elapsed', 'Unknown')}

CURRENT USER INPUT:
"{interaction.get('user_input', '')}"

RETRIEVED MEMORIES:
{interaction.get('retrieved_memories', [])}

COACH RESPONSE:
"{interaction.get('coach_response', '')}"

EVALUATION CRITERIA:
1. Relevance: Were the retrieved memories relevant to the current context?
2. Utilization: Did the coach actually USE the memories in the response?
3. Value: Did the memories improve the quality of the coaching?
4. Timeliness: Were the memories from an appropriate time frame?

IMPORTANT CONSIDERATIONS:
- For ADHD users, pattern recognition from past sessions is crucial
- Memories about recurring struggles are especially valuable
- Not all memories need to be explicitly mentioned to be useful
- Context-setting memories may influence tone without direct reference

SCORING:
- 1.0: Perfect - highly relevant memories effectively used
- 0.8-0.9: Good - relevant memories with some usage
- 0.6-0.7: Adequate - somewhat relevant but underutilized
- 0.4-0.5: Poor - memories retrieved but not relevant/used
- 0.0-0.3: Failed - irrelevant or no memories when needed

Provide your evaluation in JSON format:
{{
    "score": 0.0-1.0,
    "memories_used": true/false,
    "relevance_rating": "high/medium/low",
    "usage_examples": ["specific examples of memory usage in response"],
    "missed_opportunities": ["ways memories could have been better used"],
    "reasoning": "Brief explanation of your score"
}}"""

    @staticmethod
    def get_coaching_quality_prompt(interaction: Dict[str, Any]) -> str:
        """
        Generate prompt for evaluating ADHD coaching quality
        
        Args:
            interaction: Complete interaction data
            
        Returns:
            Evaluation prompt string
        """
        return f"""You are an expert in ADHD coaching evaluating the quality of a GTD coach's response.
This system is specifically designed for adults with ADHD who struggle with executive function.

CONTEXT:
- Phase: {interaction.get('phase', 'Unknown')}
- Time Remaining in Phase: {interaction.get('time_remaining', 'Unknown')}
- Session Progress: {interaction.get('session_progress', 'Unknown')}%
- Experiment Variable: {interaction.get('experiment_variable', 'baseline')}

USER INPUT:
"{interaction.get('user_input', '')}"

COACH RESPONSE:
"{interaction.get('coach_response', '')}"

ADHD COACHING QUALITY CRITERIA:
1. Structure & Boundaries: Clear, predictable structure with time awareness
2. Executive Function Support: Helps with planning, prioritization, task initiation
3. Non-Judgmental Tone: Supportive, understanding of ADHD challenges
4. Cognitive Load Management: Information presented in digestible chunks
5. Time Awareness: Appropriate urgency without creating anxiety
6. External Accountability: Acts as external executive function
7. Celebration & Progress: Acknowledges effort and progress

SPECIFIC CHECKS:
- Does the response maintain phase boundaries?
- Is time awareness present but not anxiety-inducing?
- Are instructions clear and actionable?
- Is the cognitive load appropriate for ADHD working memory?
- Does it help with task initiation or decision paralysis?
- Is the tone encouraging rather than critical?

RED FLAGS (automatic score reduction):
- Overwhelming lists without prioritization
- Vague or abstract suggestions
- Judgmental language about productivity
- Ignoring time boundaries
- Complex multi-step instructions without breaks

SCORING:
- 1.0: Exceptional - perfectly ADHD-adapted coaching
- 0.8-0.9: Good - strong ADHD support with minor issues
- 0.6-0.7: Adequate - helpful but could be more ADHD-specific
- 0.4-0.5: Poor - generic coaching, not ADHD-adapted
- 0.0-0.3: Harmful - may increase ADHD struggles

Provide your evaluation in JSON format:
{{
    "score": 0.0-1.0,
    "structure": true/false,
    "time_aware": true/false,
    "supportive": true/false,
    "executive_support": true/false,
    "cognitive_load": "appropriate/too_high/too_low",
    "red_flags": ["list any concerning elements"],
    "strengths": ["list coaching strengths shown"],
    "improvements": ["specific suggestions for better ADHD support"],
    "reasoning": "Brief explanation focusing on ADHD-specific aspects"
}}"""

    @staticmethod
    def get_intervention_threshold(metric: str, user_history: Dict[str, Any] = None) -> float:
        """
        Get dynamic intervention threshold based on metric and user history
        
        Args:
            metric: The evaluation metric name
            user_history: Optional user history for personalized thresholds
            
        Returns:
            Threshold value (0.0 to 1.0)
        """
        base_thresholds = {
            'task_extraction': 0.7,  # Intervene if < 70% accuracy
            'memory_relevance': 0.5,  # Intervene if < 50% relevance
            'coaching_quality': 0.6   # Intervene if < 60% quality
        }
        
        if not user_history:
            return base_thresholds.get(metric, 0.5)
        
        # Adjust based on user's personal baseline
        user_avg = user_history.get(f'{metric}_average', None)
        if user_avg:
            # Set threshold at 80% of user's average
            personalized = user_avg * 0.8
            # But don't go below minimum safety threshold
            return max(personalized, base_thresholds.get(metric, 0.5) * 0.7)
        
        return base_thresholds.get(metric, 0.5)

    @staticmethod
    def get_intervention_prompt(metric: str, score: float, details: Dict[str, Any]) -> str:
        """
        Generate intervention prompt based on evaluation results
        
        Args:
            metric: The metric that triggered intervention
            score: The evaluation score
            details: Evaluation details including missed items
            
        Returns:
            Intervention prompt for the coach
        """
        if metric == 'task_extraction' and details.get('missed_tasks'):
            missed = ', '.join(details['missed_tasks'][:3])  # Limit to 3
            return f"""
Before we continue, I want to make sure I captured everything you mentioned.
I heard you mention: {missed}
Should I add these to our list?"""

        elif metric == 'memory_relevance' and score < 0.3:
            return """
I'm having trouble recalling relevant patterns from our previous sessions.
What's been your biggest challenge this week that we should focus on?"""

        elif metric == 'coaching_quality' and details.get('red_flags'):
            # Don't show red flags to user, but adjust coaching style
            return None  # Signal to adjust internal coaching parameters
        
        return None  # No intervention needed

    @staticmethod
    def format_evaluation_summary(evaluations: list) -> Dict[str, Any]:
        """
        Format evaluation results into a summary
        
        Args:
            evaluations: List of evaluation results
            
        Returns:
            Formatted summary with insights
        """
        summary = {
            'total_interactions': len(evaluations),
            'metrics': {},
            'patterns': [],
            'recommendations': []
        }
        
        # Calculate metrics
        for metric in ['task_extraction', 'memory_relevance', 'coaching_quality']:
            scores = [e.get(metric, {}).get('score', 0) for e in evaluations if metric in e]
            if scores:
                summary['metrics'][metric] = {
                    'average': round(sum(scores) / len(scores), 3),
                    'min': round(min(scores), 3),
                    'max': round(max(scores), 3),
                    'count': len(scores)
                }
        
        # Identify patterns
        if summary['metrics'].get('task_extraction', {}).get('average', 1) < 0.7:
            summary['patterns'].append('Consistent task extraction issues')
            summary['recommendations'].append('Consider more structured prompting for task capture')
        
        if summary['metrics'].get('memory_relevance', {}).get('average', 1) < 0.5:
            summary['patterns'].append('Memory retrieval not effectively used')
            summary['recommendations'].append('Tune memory retrieval strategy or thresholds')
        
        if summary['metrics'].get('coaching_quality', {}).get('average', 1) < 0.6:
            summary['patterns'].append('Coaching quality below ADHD standards')
            summary['recommendations'].append('Review ADHD-specific coaching guidelines')
        
        return summary