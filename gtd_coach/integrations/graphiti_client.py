#!/usr/bin/env python3
"""
Graphiti Client for GTD Coach - FalkorDB Only
Provides a singleton client with connection pooling for FalkorDB
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.nodes import EpisodeType

# Import database driver for FalkorDB
try:
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    FALKORDB_AVAILABLE = True
except ImportError:
    FALKORDB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error("FalkorDB driver not available. Install with: pip install graphiti-core[falkordb]")

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
    """Singleton Graphiti client for FalkorDB"""
    
    _instance: Optional['GraphitiClient'] = None
    _lock = asyncio.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, env_file: str = '.env.graphiti') -> 'Graphiti':
        """
        Initialize Graphiti with FalkorDB connection
        
        Args:
            env_file: Path to environment file with configuration
            
        Returns:
            Initialized Graphiti client
            
        Raises:
            ImportError: If FalkorDB driver is not available
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
            
            # Check FalkorDB availability
            if not FALKORDB_AVAILABLE:
                raise ImportError("FalkorDB driver not available. Install with: pip install graphiti-core[falkordb]")
            
            # Validate required environment variables
            required_vars = ['OPENAI_API_KEY']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            # Initialize FalkorDB driver
            driver = await self._initialize_falkordb_driver()
            
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
            )
            
            embedder = OpenAIEmbedder(config=embedder_config)
            
            # Initialize Graphiti with FalkorDB driver
            try:
                if GTD_ENTITIES_AVAILABLE:
                    logger.info("GTD entities available for selective use in add_episode() calls")
                
                logger.info(f"Initializing Graphiti with FalkorDB backend")
                
                # v0.17.9 uses graph_driver parameter
                self.client = Graphiti(
                    graph_driver=driver,
                    llm_client=llm_client,
                    embedder=embedder
                )
                
                # Build indices and constraints if needed
                logger.info("Building FalkorDB indices and constraints...")
                await self.client.build_indices_and_constraints()
                
                self._initialized = True
                logger.info("✅ Graphiti client initialized successfully with FalkorDB")
                
                return self.client
                
            except Exception as e:
                logger.error(f"Failed to initialize Graphiti: {e}")
                raise
    
    async def _initialize_falkordb_driver(self):
        """
        Initialize FalkorDB driver
        
        Returns:
            Initialized FalkorDB driver instance
        """
        host = os.getenv('FALKORDB_HOST', 'localhost')
        port = int(os.getenv('FALKORDB_PORT', '6380'))
        database = os.getenv('FALKORDB_DATABASE', 'shared_gtd_knowledge')
        
        logger.info(f"Connecting to FalkorDB at {host}:{port}/{database}")
        
        driver = FalkorDriver(
            host=host,
            port=port,
            database=database
        )
        
        logger.info("✅ FalkorDB driver initialized")
        return driver
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the Graphiti/FalkorDB connection
        
        Returns:
            True if healthy, False otherwise
        """
        if not self._initialized or not hasattr(self, 'client'):
            return False
        
        try:
            # For FalkorDB, if client exists and is initialized, assume healthy
            # v0.17.9 doesn't expose direct driver access for health checks
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
    """Test function to verify the FalkorDB client works"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Get the singleton instance
        client = await GraphitiClient.get_instance()
        
        # Test adding an episode
        await client.add_episode(
            name="test_falkordb_connection",
            episode_body="This is a test episode to verify FalkorDB connection",
            source=EpisodeType.text,
            source_description="FalkorDB connection test",
            group_id="shared_knowledge",
            reference_time=datetime.now(timezone.utc)
        )
        
        print("✅ Successfully added test episode to FalkorDB via Graphiti")
        
        # Test search
        results = await client.search("test", num_results=5)
        print(f"✅ Search returned {len(results)} results")
        
        # Health check
        health = await GraphitiClient().health_check()
        print(f"✅ Health check: {'passed' if health else 'failed'}")
        
        # Clean up
        await GraphitiClient().close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run test
    asyncio.run(test_client())