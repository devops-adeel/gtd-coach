"""
Langfuse-wrapped LLM client for GTD Coach agent system.
All agent LLM calls go through this client for observability.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from langfuse.openai import OpenAI
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    from openai import OpenAI
    LANGFUSE_AVAILABLE = False
    print("⚠️ Langfuse not available - using standard OpenAI client")
    print("Install with: pip install 'langfuse[openai]'")

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Managed LLM client with Langfuse observability.
    Points to local LM Studio for agent operations.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_langfuse: bool = True
    ):
        """
        Initialize LLM client.
        
        Args:
            base_url: LM Studio endpoint (default: http://localhost:1234/v1)
            api_key: API key (default: "lm-studio" for local)
            model: Model name (default: meta-llama-3.1-8b-instruct)
            enable_langfuse: Whether to enable Langfuse tracking
        """
        self.base_url = base_url or os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.api_key = api_key or "lm-studio"
        self.model = model or os.getenv("LLM_MODEL", "meta-llama-3.1-8b-instruct")
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        
        # Initialize client
        self._client = None
        self._langfuse = None
        
        # Performance tracking
        self.call_count = 0
        self.total_latency_ms = 0
        self.error_count = 0
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client with or without Langfuse"""
        try:
            if self.enable_langfuse:
                # Check if Langfuse is configured
                from gtd_coach.integrations.langfuse import validate_configuration
                
                if validate_configuration():
                    # Use Langfuse-wrapped client
                    self._client = OpenAI(
                        base_url=self.base_url,
                        api_key=self.api_key
                    )
                    
                    # Also initialize Langfuse client for additional tracking
                    self._langfuse = Langfuse()
                    
                    logger.info("Langfuse-wrapped LLM client initialized")
                else:
                    logger.warning("Langfuse not configured - using standard client")
                    self.enable_langfuse = False
            
            if not self.enable_langfuse:
                # Use standard OpenAI client
                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key
                )
                logger.info("Standard LLM client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            # Fallback to standard client
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        session_id: Optional[str] = None,
        phase: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Make a chat completion request with observability.
        
        Args:
            messages: List of message dictionaries
            model: Model to use (default: self.model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            session_id: Session identifier for tracking
            phase: Current GTD phase for context
            user_id: User identifier
            metadata: Additional metadata to track
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            OpenAI ChatCompletion response
        """
        model = model or self.model
        start_time = datetime.now()
        
        # Prepare metadata for Langfuse
        langfuse_metadata = {
            "session_id": session_id,
            "phase": phase,
            "user_id": user_id,
            "temperature": temperature,
            "stream": stream
        }
        
        if metadata:
            langfuse_metadata.update(metadata)
        
        # Add Langfuse tracking if available
        if self.enable_langfuse and session_id:
            kwargs["metadata"] = {
                "langfuse_session_id": session_id,
                "langfuse_user_id": user_id,
                "langfuse_tags": [f"phase:{phase}"] if phase else [],
                **langfuse_metadata
            }
        
        try:
            # Make the LLM call
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            
            # Track performance
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.call_count += 1
            self.total_latency_ms += latency_ms
            
            # Log performance if not streaming
            if not stream:
                logger.debug(
                    f"LLM call completed - Phase: {phase}, "
                    f"Latency: {latency_ms:.0f}ms, "
                    f"Tokens: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}"
                )
            
            # Score in Langfuse if available
            if self.enable_langfuse and phase:
                self._score_response(
                    phase=phase,
                    success=True,
                    latency_ms=latency_ms,
                    session_id=session_id
                )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"LLM call failed: {e}")
            
            # Score failure in Langfuse
            if self.enable_langfuse and phase:
                self._score_response(
                    phase=phase,
                    success=False,
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    session_id=session_id
                )
            
            raise
    
    def _score_response(
        self,
        phase: str,
        success: bool,
        latency_ms: float,
        session_id: Optional[str] = None
    ):
        """Score the response in Langfuse for quality tracking"""
        if not self._langfuse:
            return
        
        try:
            from gtd_coach.integrations.langfuse import score_response
            
            score_response(
                phase=phase,
                success=success,
                response_time=latency_ms / 1000,  # Convert to seconds
                session_id=session_id
            )
            
        except Exception as e:
            logger.debug(f"Failed to score response: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client performance statistics"""
        avg_latency = (
            self.total_latency_ms / self.call_count 
            if self.call_count > 0 else 0
        )
        
        return {
            "total_calls": self.call_count,
            "total_errors": self.error_count,
            "error_rate": (
                self.error_count / self.call_count 
                if self.call_count > 0 else 0
            ),
            "average_latency_ms": round(avg_latency, 1),
            "langfuse_enabled": self.enable_langfuse,
            "model": self.model,
            "base_url": self.base_url
        }
    
    def test_connection(self) -> bool:
        """Test connection to LM Studio"""
        try:
            # Try to get model list
            models = self._client.models.list()
            logger.info(f"LM Studio connection successful - {len(list(models.data))} models available")
            return True
        except Exception as e:
            logger.error(f"LM Studio connection failed: {e}")
            return False
    
    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ):
        """
        Stream a chat completion response.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters for chat_completion
            
        Yields:
            Streaming response chunks
        """
        kwargs["stream"] = True
        response = self.chat_completion(messages, **kwargs)
        
        for chunk in response:
            yield chunk


class EvaluationClient:
    """
    Separate client for LLM-as-judge evaluations.
    Can use a different model or provider than the main agent.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize evaluation client.
        
        Args:
            base_url: API endpoint (can be different from agent)
            api_key: API key for evaluation model
            model: Model for evaluations (can be more powerful)
        """
        # Default to same as agent but allow override
        self.base_url = base_url or os.getenv("EVAL_LLM_URL", "http://localhost:1234/v1")
        self.api_key = api_key or os.getenv("EVAL_API_KEY", "lm-studio")
        self.model = model or os.getenv("EVAL_MODEL", "meta-llama-3.1-8b-instruct")
        
        # Always use standard client for evaluations (no Langfuse wrapping)
        from openai import OpenAI as StandardOpenAI
        self._client = StandardOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
        
        logger.info(f"Evaluation client initialized with model: {self.model}")
    
    def evaluate(
        self,
        prompt: str,
        response: str,
        criteria: Optional[Dict[str, str]] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Evaluate a response using LLM-as-judge.
        
        Args:
            prompt: Original prompt
            response: Response to evaluate
            criteria: Evaluation criteria
            temperature: Lower temperature for more consistent evaluation
            
        Returns:
            Evaluation results
        """
        eval_prompt = self._build_evaluation_prompt(prompt, response, criteria)
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator."},
                    {"role": "user", "content": eval_prompt}
                ],
                temperature=temperature,
                max_tokens=500
            )
            
            # Parse evaluation response
            evaluation = response.choices[0].message.content
            
            # Try to extract score if present
            score = None
            if "/10" in evaluation:
                import re
                match = re.search(r"(\d+)/10", evaluation)
                if match:
                    score = int(match.group(1))
            
            return {
                "evaluation": evaluation,
                "score": score,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {
                "evaluation": "Error during evaluation",
                "score": None,
                "error": str(e)
            }
    
    def _build_evaluation_prompt(
        self,
        prompt: str,
        response: str,
        criteria: Optional[Dict[str, str]] = None
    ) -> str:
        """Build evaluation prompt"""
        eval_prompt = f"""Evaluate the following response:

PROMPT: {prompt}

RESPONSE: {response}

CRITERIA:
"""
        
        if criteria:
            for key, value in criteria.items():
                eval_prompt += f"- {key}: {value}\n"
        else:
            eval_prompt += """- Relevance: Does the response address the prompt?
- Completeness: Is the response complete and thorough?
- Accuracy: Is the information accurate?
- Clarity: Is the response clear and well-structured?
"""
        
        eval_prompt += "\nProvide a brief evaluation and score out of 10."
        
        return eval_prompt


# Singleton instances
_llm_client = None
_eval_client = None

def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

def get_evaluation_client() -> EvaluationClient:
    """Get singleton evaluation client instance"""
    global _eval_client
    if _eval_client is None:
        _eval_client = EvaluationClient()
    return _eval_client