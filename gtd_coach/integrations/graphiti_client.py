#!/usr/bin/env python3
"""
Graphiti Client for GTD Coach
Provides a singleton client with connection pooling and health checks
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.nodes import EpisodeType

# Import custom GTD entities and edge mappings
try:
    from gtd_coach.integrations.gtd_entities import get_gtd_entities, get_gtd_edge_map
    GTD_ENTITIES_AVAILABLE = True
except ImportError:
    GTD_ENTITIES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("GTD entities not available, using default Graphiti entities")

logger = logging.getLogger(__name__)


class GraphitiClient:
    """Singleton Graphiti client with connection management"""
    
    _instance: Optional['GraphitiClient'] = None
    _lock = asyncio.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, env_file: str = '.env.graphiti') -> 'Graphiti':
        """
        Lazy initialization with connection verification
        
        Args:
            env_file: Path to environment file with configuration
            
        Returns:
            Initialized Graphiti client
            
        Raises:
            ConnectionError: If Neo4j connection fails
            ValueError: If required environment variables are missing
        """
        async with self._lock:
            if self._initialized and hasattr(self, 'client'):
                return self.client
            
            # Load environment variables
            env_path = Path.home() / "gtd-coach" / env_file
            if not env_path.exists():
                # Try local path if not in home directory
                env_path = Path(env_file)
            
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded configuration from {env_path}")
            else:
                logger.warning(f"Config file not found: {env_path}, using existing environment")
            
            # Validate required environment variables
            required_vars = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD', 'OPENAI_API_KEY']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            # Test Neo4j connection first
            await self._verify_neo4j_connection()
            
            # Initialize LLM configuration
            llm_config = LLMConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4096
            )
            
            llm_client = OpenAIClient(config=llm_config)
            
            # Initialize embedder configuration
            embedder_config = OpenAIEmbedderConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                embedding_model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
                # Let Graphiti use the default embedding_dim for the model
            )
            
            embedder = OpenAIEmbedder(config=embedder_config)
            
            # Initialize cross-encoder (reranker)
            # The reranker creates its own client internally
            cross_encoder = OpenAIRerankerClient(
                config=llm_config
            )
            
            # Initialize Graphiti with all components
            try:
                # NOTE: Custom entities are passed per-episode via add_episode() parameters,
                # not through the Graphiti constructor. See gtd_entity_config.py for
                # how entity types are applied selectively to different episode types.
                if GTD_ENTITIES_AVAILABLE:
                    logger.info("GTD entities available for selective use in add_episode() calls")
                
                self.client = Graphiti(
                    uri=os.getenv('NEO4J_URI'),
                    user=os.getenv('NEO4J_USER'),
                    password=os.getenv('NEO4J_PASSWORD'),
                    # Note: database parameter is not directly supported, uses default
                    llm_client=llm_client,
                    embedder=embedder,
                    cross_encoder=cross_encoder
                )
                
                # Build indices and constraints if needed
                logger.info("Building Neo4j indices and constraints...")
                await self.client.build_indices_and_constraints()
                
                self._initialized = True
                logger.info("✅ Graphiti client initialized successfully")
                
                return self.client
                
            except Exception as e:
                logger.error(f"Failed to initialize Graphiti: {e}")
                raise
    
    async def _verify_neo4j_connection(self):
        """
        Verify Neo4j is accessible before initializing Graphiti
        
        Raises:
            ConnectionError: If connection to Neo4j fails
        """
        uri = os.getenv('NEO4J_URI')
        user = os.getenv('NEO4J_USER')
        password = os.getenv('NEO4J_PASSWORD')
        database = os.getenv('NEO4J_DATABASE', 'neo4j')
        
        logger.info(f"Testing Neo4j connection to {uri}...")
        
        try:
            driver = AsyncGraphDatabase.driver(
                uri,
                auth=(user, password),
                database=database
            )
            
            async with driver.session(database=database) as session:
                result = await session.run("RETURN 1 as test")
                test_value = await result.single()
                if test_value and test_value['test'] == 1:
                    logger.info("✅ Neo4j connection verified")
                else:
                    raise ConnectionError("Neo4j test query failed")
            
            await driver.close()
            
        except Exception as e:
            error_msg = f"Cannot connect to Neo4j at {uri}: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the Graphiti connection
        
        Returns:
            True if healthy, False otherwise
        """
        if not self._initialized or not hasattr(self, 'client'):
            return False
        
        try:
            # Try a simple operation
            async with self.client.driver.session() as session:
                result = await session.run("RETURN 1 as health")
                await result.single()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def close(self):
        """Close the Graphiti client and clean up resources"""
        if hasattr(self, 'client') and self.client:
            try:
                await self.client.close()
                logger.info("Graphiti client closed")
            except Exception as e:
                logger.error(f"Error closing Graphiti client: {e}")
            finally:
                self._initialized = False
    
    @classmethod
    async def get_instance(cls) -> 'Graphiti':
        """
        Get or create the singleton Graphiti client instance
        
        Returns:
            Initialized Graphiti client
        """
        instance = cls()
        return await instance.initialize()


async def test_client():
    """Test function to verify the client works"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Get the singleton instance
        client = await GraphitiClient.get_instance()
        
        # Test adding an episode
        await client.add_episode(
            name="test_connection",
            episode_body="This is a test episode to verify Graphiti connection",
            source=EpisodeType.text,
            source_description="Connection test",
            group_id="test_group",
            reference_time=datetime.now(timezone.utc)
        )
        
        print("✅ Successfully added test episode to Graphiti")
        
        # Test search
        results = await client.search("test", num_results=5)
        print(f"✅ Search returned {len(results)} results")
        
        # Health check
        health = await GraphitiClient().health_check()
        print(f"✅ Health check: {'Healthy' if health else 'Unhealthy'}")
        
        # Close the client
        await GraphitiClient().close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Run test when executed directly
    import sys
    success = asyncio.run(test_client())
    sys.exit(0 if success else 1)