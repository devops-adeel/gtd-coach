"""
SQLite-based checkpointing for LangGraph agent persistence.
Enables resumable sessions that survive process restarts.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph not installed - agent checkpointing unavailable")
    print("Install with: pip install langgraph")

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """
    Manages SQLite-based checkpointing for LangGraph agents.
    Provides persistence across process restarts and session recovery.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize checkpointer manager.
        
        Args:
            db_path: Path to SQLite database file (default: data/agent_state.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "agent_state.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection_string = f"sqlite:///{self.db_path}"
        self._checkpointer = None
        self._metadata = {}
        
        # Initialize metadata tracking
        self.metadata_table_created = False
        self._ensure_metadata_table()
    
    def get_checkpointer(self) -> Optional['SqliteSaver']:
        """
        Get or create the SQLite checkpointer.
        
        Returns:
            SqliteSaver instance or None if LangGraph not available
        """
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available - returning None checkpointer")
            return None
        
        if self._checkpointer is None:
            try:
                # Create SQLite checkpointer
                self._checkpointer = SqliteSaver.from_conn_string(
                    self.connection_string
                )
                logger.info(f"SQLite checkpointer initialized at {self.db_path}")
                
                # Setup tables if needed
                if hasattr(self._checkpointer, 'setup'):
                    self._checkpointer.setup()
                    
            except Exception as e:
                logger.error(f"Failed to create SQLite checkpointer: {e}")
                return None
        
        return self._checkpointer
    
    def _ensure_metadata_table(self):
        """Create metadata table for tracking sessions"""
        if self.metadata_table_created:
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_metadata (
                    session_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    workflow_type TEXT,
                    user_id TEXT,
                    phase TEXT,
                    completed BOOLEAN DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_id 
                ON session_metadata(thread_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON session_metadata(updated_at DESC)
            """)
            
            conn.commit()
            conn.close()
            
            self.metadata_table_created = True
            logger.info("Session metadata table initialized")
            
        except Exception as e:
            logger.error(f"Failed to create metadata table: {e}")
    
    def save_session_metadata(
        self,
        session_id: str,
        thread_id: str,
        workflow_type: str = "daily_capture",
        user_id: Optional[str] = None,
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save metadata about a session.
        
        Args:
            session_id: Unique session identifier
            thread_id: LangGraph thread identifier
            workflow_type: Type of workflow (daily_capture, weekly_review, etc.)
            user_id: Optional user identifier
            phase: Current phase of the workflow
            metadata: Additional metadata to store
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            metadata_json = json.dumps(metadata) if metadata else "{}"
            
            # Upsert session metadata
            cursor.execute("""
                INSERT OR REPLACE INTO session_metadata 
                (session_id, thread_id, created_at, updated_at, 
                 workflow_type, user_id, phase, metadata)
                VALUES (?, ?, 
                        COALESCE((SELECT created_at FROM session_metadata WHERE session_id = ?), ?),
                        ?, ?, ?, ?, ?)
            """, (
                session_id, thread_id, session_id, now,
                now, workflow_type, user_id, phase, metadata_json
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Saved metadata for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save session metadata: {e}")
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session metadata dictionary or None
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT thread_id, created_at, updated_at, workflow_type,
                       user_id, phase, completed, error_count, metadata
                FROM session_metadata
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "session_id": session_id,
                    "thread_id": row[0],
                    "created_at": row[1],
                    "updated_at": row[2],
                    "workflow_type": row[3],
                    "user_id": row[4],
                    "phase": row[5],
                    "completed": bool(row[6]),
                    "error_count": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session metadata: {e}")
            return None
    
    def get_recent_sessions(
        self,
        limit: int = 10,
        workflow_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> list:
        """
        Get recent sessions with optional filtering.
        
        Args:
            limit: Maximum number of sessions to return
            workflow_type: Filter by workflow type
            user_id: Filter by user ID
            
        Returns:
            List of session metadata dictionaries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = """
                SELECT session_id, thread_id, created_at, updated_at, 
                       workflow_type, user_id, phase, completed, error_count
                FROM session_metadata
                WHERE 1=1
            """
            params = []
            
            if workflow_type:
                query += " AND workflow_type = ?"
                params.append(workflow_type)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": row[0],
                    "thread_id": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "workflow_type": row[4],
                    "user_id": row[5],
                    "phase": row[6],
                    "completed": bool(row[7]),
                    "error_count": row[8]
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
            return []
    
    def get_resumable_session(
        self,
        workflow_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the most recent incomplete session that can be resumed.
        
        Args:
            workflow_type: Filter by workflow type
            user_id: Filter by user ID
            
        Returns:
            Session metadata for resumable session or None
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = """
                SELECT session_id, thread_id, created_at, updated_at,
                       workflow_type, user_id, phase, error_count, metadata
                FROM session_metadata
                WHERE completed = 0
            """
            params = []
            
            if workflow_type:
                query += " AND workflow_type = ?"
                params.append(workflow_type)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            # Only resume sessions from the last 24 hours
            query += """ 
                AND datetime(updated_at) > datetime('now', '-1 day')
                ORDER BY updated_at DESC
                LIMIT 1
            """
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "session_id": row[0],
                    "thread_id": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "workflow_type": row[4],
                    "user_id": row[5],
                    "phase": row[6],
                    "error_count": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get resumable session: {e}")
            return None
    
    def mark_session_complete(self, session_id: str):
        """
        Mark a session as completed.
        
        Args:
            session_id: Session identifier
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE session_metadata
                SET completed = 1, updated_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Marked session {session_id} as completed")
            
        except Exception as e:
            logger.error(f"Failed to mark session complete: {e}")
    
    def increment_error_count(self, session_id: str):
        """
        Increment error count for a session.
        
        Args:
            session_id: Session identifier
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE session_metadata
                SET error_count = error_count + 1, updated_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to increment error count: {e}")
    
    def cleanup_old_sessions(self, days: int = 30):
        """
        Remove old sessions and checkpoints.
        
        Args:
            days: Remove sessions older than this many days
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Delete old metadata
            cursor.execute("""
                DELETE FROM session_metadata
                WHERE datetime(updated_at) < datetime('now', ? || ' days')
            """, (-days,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old sessions")
            
            # TODO: Also clean up old checkpoints from LangGraph tables
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored sessions.
        
        Returns:
            Dictionary with session statistics
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM session_metadata")
            total = cursor.fetchone()[0]
            
            # Completed sessions
            cursor.execute("SELECT COUNT(*) FROM session_metadata WHERE completed = 1")
            completed = cursor.fetchone()[0]
            
            # Sessions by workflow type
            cursor.execute("""
                SELECT workflow_type, COUNT(*) 
                FROM session_metadata 
                GROUP BY workflow_type
            """)
            by_type = dict(cursor.fetchall())
            
            # Average error count
            cursor.execute("SELECT AVG(error_count) FROM session_metadata")
            avg_errors = cursor.fetchone()[0] or 0
            
            # Database size
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
            
            conn.close()
            
            return {
                "total_sessions": total,
                "completed_sessions": completed,
                "incomplete_sessions": total - completed,
                "completion_rate": (completed / total * 100) if total > 0 else 0,
                "sessions_by_type": by_type,
                "average_errors": round(avg_errors, 2),
                "database_size_mb": round(db_size_mb, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# Create singleton instance
_checkpointer_manager = None

def get_checkpointer_manager() -> CheckpointerManager:
    """Get singleton CheckpointerManager instance"""
    global _checkpointer_manager
    if _checkpointer_manager is None:
        _checkpointer_manager = CheckpointerManager()
    return _checkpointer_manager

def get_checkpointer() -> Optional['SqliteSaver']:
    """Convenience function to get checkpointer directly"""
    return get_checkpointer_manager().get_checkpointer()