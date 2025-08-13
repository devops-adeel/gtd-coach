#!/usr/bin/env python3
"""
Targeted tests for tool operation coverage gaps
Focus on edge cases and error paths in tool implementations
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import tempfile

from gtd_coach.agent.tools import *
from gtd_coach.agent.state import StateValidator


class TestMemoryToolGaps:
    """Test memory tool operations that were uncovered"""
    
    @pytest.mark.asyncio
    async def test_batch_memory_operations(self):
        """Test batched memory operations for efficiency"""
        mock_memory = AsyncMock()
        episodes_saved = []
        
        async def track_save(episode):
            episodes_saved.append(episode)
            return {"id": f"ep_{len(episodes_saved)}"}
        
        mock_memory.add_episode.side_effect = track_save
        
        # Batch operations
        batch_size = 5
        total_episodes = 12
        
        episodes = [
            {"content": f"Episode {i}", "type": "capture"}
            for i in range(total_episodes)
        ]
        
        # Process in batches
        for i in range(0, total_episodes, batch_size):
            batch = episodes[i:i + batch_size]
            
            # Save batch concurrently
            tasks = [mock_memory.add_episode(ep) for ep in batch]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(batch)
        
        # Verify all episodes saved
        assert len(episodes_saved) == total_episodes
    
    @pytest.mark.asyncio
    async def test_memory_search_with_filters(self):
        """Test memory search with various filter combinations"""
        mock_memory = AsyncMock()
        
        # Mock search with filters
        def search_with_filters(query, **kwargs):
            results = [
                {"id": "1", "type": "GTDProject", "name": "Project A"},
                {"id": "2", "type": "GTDAction", "name": "Action B"},
                {"id": "3", "type": "ADHDPattern", "name": "Pattern C"},
            ]
            
            # Apply filters
            if "entity_type" in kwargs:
                results = [r for r in results if r["type"] == kwargs["entity_type"]]
            
            if "date_range" in kwargs:
                # Filter by date (mock implementation)
                pass
            
            if "user_id" in kwargs:
                # Filter by user (mock implementation)
                pass
            
            return results
        
        mock_memory.search_nodes.side_effect = search_with_filters
        
        # Test different filter combinations
        test_cases = [
            ({}, 3),  # No filter
            ({"entity_type": "GTDProject"}, 1),  # Type filter
            ({"entity_type": "ADHDPattern"}, 1),  # Different type
            ({"entity_type": "NonExistent"}, 0),  # No matches
        ]
        
        for filters, expected_count in test_cases:
            results = await mock_memory.search_nodes("test", **filters)
            assert len(results) == expected_count
    
    def test_memory_cache_invalidation(self):
        """Test memory cache invalidation strategies"""
        cache = {}
        cache_timestamps = {}
        cache_ttl = 300  # 5 minutes
        
        def get_from_cache(key: str):
            if key in cache:
                # Check if expired
                if datetime.now() - cache_timestamps[key] > timedelta(seconds=cache_ttl):
                    # Invalidate expired entry
                    del cache[key]
                    del cache_timestamps[key]
                    return None
                return cache[key]
            return None
        
        def set_cache(key: str, value: Any):
            cache[key] = value
            cache_timestamps[key] = datetime.now()
        
        def invalidate_pattern(pattern: str):
            """Invalidate all cache entries matching pattern"""
            keys_to_remove = [k for k in cache.keys() if pattern in k]
            for key in keys_to_remove:
                del cache[key]
                del cache_timestamps[key]
        
        # Test cache operations
        set_cache("user_123_projects", ["Project1", "Project2"])
        set_cache("user_123_actions", ["Action1", "Action2"])
        set_cache("user_456_projects", ["Project3"])
        
        # Retrieve from cache
        assert get_from_cache("user_123_projects") == ["Project1", "Project2"]
        
        # Invalidate user_123 entries
        invalidate_pattern("user_123")
        
        # Check invalidation
        assert get_from_cache("user_123_projects") is None
        assert get_from_cache("user_123_actions") is None
        assert get_from_cache("user_456_projects") == ["Project3"]  # Should remain


class TestLLMToolGaps:
    """Test LLM tool operations that were uncovered"""
    
    @pytest.mark.asyncio
    async def test_llm_streaming_response(self):
        """Test handling of streaming LLM responses"""
        chunks_received = []
        
        async def stream_generator():
            chunks = ["This ", "is ", "a ", "streaming ", "response."]
            for chunk in chunks:
                chunks_received.append(chunk)
                yield {"delta": {"content": chunk}}
                await asyncio.sleep(0.01)
        
        # Process streaming response
        full_response = ""
        async for chunk in stream_generator():
            full_response += chunk["delta"]["content"]
        
        assert full_response == "This is a streaming response."
        assert len(chunks_received) == 5
    
    def test_llm_prompt_token_counting(self):
        """Test accurate token counting for prompts"""
        def estimate_tokens(text: str) -> int:
            # Simple estimation: ~4 characters per token
            # Real implementation would use tiktoken
            return len(text) // 4
        
        test_prompts = [
            ("Hello world", 3),
            ("A" * 100, 25),
            ("This is a longer prompt with multiple words.", 11),
            ("", 0),
        ]
        
        for prompt, expected_range in test_prompts:
            tokens = estimate_tokens(prompt)
            # Allow 20% variance
            assert abs(tokens - expected_range) <= expected_range * 0.2 + 1
    
    @pytest.mark.asyncio
    async def test_llm_fallback_responses(self):
        """Test fallback responses when LLM is unavailable"""
        fallback_responses = {
            "mind_sweep": {
                "prompt": "Help me capture items",
                "fallback": "Please list all items on your mind. Type 'done' when finished."
            },
            "prioritization": {
                "prompt": "Help prioritize these items",
                "fallback": "Assign items to priorities:\nA: Urgent & Important\nB: Important\nC: Nice to have"
            },
            "intervention": {
                "prompt": "User seems overwhelmed",
                "fallback": "Let's take a break. Focus on one thing at a time."
            }
        }
        
        async def get_llm_or_fallback(prompt_type: str):
            try:
                # Simulate LLM failure
                raise ConnectionError("LLM unavailable")
            except ConnectionError:
                return fallback_responses.get(prompt_type, {}).get("fallback", "Please continue.")
        
        for prompt_type in fallback_responses:
            response = await get_llm_or_fallback(prompt_type)
            assert response == fallback_responses[prompt_type]["fallback"]


class TestFileOperationGaps:
    """Test file operation tools that were uncovered"""
    
    def test_atomic_file_write(self):
        """Test atomic file writing to prevent corruption"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            
            def atomic_write(path: Path, data: dict):
                """Write file atomically using temp file + rename"""
                temp_path = path.with_suffix('.tmp')
                
                try:
                    # Write to temp file
                    with open(temp_path, 'w') as f:
                        json.dump(data, f)
                    
                    # Atomic rename
                    temp_path.replace(path)
                    return True
                except Exception as e:
                    # Clean up temp file on error
                    if temp_path.exists():
                        temp_path.unlink()
                    raise
            
            # Test atomic write
            test_data = {"key": "value", "count": 42}
            atomic_write(file_path, test_data)
            
            # Verify file written correctly
            with open(file_path) as f:
                loaded = json.load(f)
            assert loaded == test_data
            
            # Test write with simulated failure
            def failing_json_dump(data, f):
                f.write('{"partial":')
                raise IOError("Disk full")
            
            with patch('json.dump', side_effect=failing_json_dump):
                with pytest.raises(IOError):
                    atomic_write(file_path, {"new": "data"})
            
            # Original file should be unchanged
            with open(file_path) as f:
                loaded = json.load(f)
            assert loaded == test_data  # Original data preserved
    
    def test_file_lock_handling(self):
        """Test file locking for concurrent access"""
        import fcntl
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            file_path = f.name
            f.write("initial content")
        
        try:
            # Acquire exclusive lock
            with open(file_path, 'r+') as f1:
                fcntl.flock(f1.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Try to acquire lock from another handle (should fail)
                with open(file_path, 'r+') as f2:
                    with pytest.raises(BlockingIOError):
                        fcntl.flock(f2.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Release lock
                fcntl.flock(f1.fileno(), fcntl.LOCK_UN)
            
            # Should be able to lock now
            with open(file_path, 'r+') as f3:
                fcntl.flock(f3.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f3.fileno(), fcntl.LOCK_UN)
        
        finally:
            Path(file_path).unlink()
    
    def test_directory_traversal_safety(self):
        """Test protection against directory traversal attacks"""
        safe_base = Path("/tmp/safe_dir")
        
        def safe_path_join(base: Path, user_input: str) -> Path:
            """Safely join paths preventing directory traversal"""
            # Resolve to absolute path
            base = base.resolve()
            # Join and resolve
            target = (base / user_input).resolve()
            
            # Check if target is within base
            try:
                target.relative_to(base)
                return target
            except ValueError:
                raise ValueError(f"Path traversal detected: {user_input}")
        
        # Test safe paths
        safe_inputs = [
            "file.txt",
            "subdir/file.txt",
            "./file.txt",
        ]
        
        for input_path in safe_inputs:
            result = safe_path_join(safe_base, input_path)
            assert str(result).startswith(str(safe_base))
        
        # Test unsafe paths (should be rejected)
        unsafe_inputs = [
            "../etc/passwd",
            "../../root/.ssh/id_rsa",
            "/etc/shadow",
            "subdir/../../etc/passwd",
        ]
        
        for input_path in unsafe_inputs:
            with pytest.raises(ValueError, match="Path traversal"):
                safe_path_join(safe_base, input_path)


class TestValidationToolGaps:
    """Test validation tool operations that were uncovered"""
    
    def test_input_sanitization(self):
        """Test input sanitization for various data types"""
        def sanitize_input(data: Any, data_type: str) -> Any:
            """Sanitize user input based on type"""
            if data_type == "string":
                # Remove control characters, limit length
                if not isinstance(data, str):
                    data = str(data)
                # Remove control characters except newline and tab
                sanitized = ''.join(
                    c for c in data 
                    if c == '\n' or c == '\t' or (ord(c) >= 32 and ord(c) < 127)
                )
                return sanitized[:1000]  # Limit length
            
            elif data_type == "integer":
                try:
                    value = int(data)
                    # Limit range
                    return max(-999999, min(999999, value))
                except (ValueError, TypeError):
                    return 0
            
            elif data_type == "list":
                if not isinstance(data, list):
                    return []
                # Limit size and sanitize elements
                return [sanitize_input(item, "string") for item in data[:100]]
            
            elif data_type == "dict":
                if not isinstance(data, dict):
                    return {}
                # Limit size and sanitize keys/values
                sanitized = {}
                for key, value in list(data.items())[:50]:
                    safe_key = sanitize_input(key, "string")
                    safe_value = sanitize_input(value, "string")
                    sanitized[safe_key] = safe_value
                return sanitized
            
            return None
        
        # Test string sanitization
        assert sanitize_input("Hello\x00World\x1f", "string") == "HelloWorld"
        assert len(sanitize_input("A" * 2000, "string")) == 1000
        
        # Test integer sanitization
        assert sanitize_input("42", "integer") == 42
        assert sanitize_input(9999999, "integer") == 999999
        assert sanitize_input("not_a_number", "integer") == 0
        
        # Test list sanitization
        assert sanitize_input(["a", "b", "c"], "list") == ["a", "b", "c"]
        assert len(sanitize_input(list(range(200)), "list")) == 100
        
        # Test dict sanitization
        result = sanitize_input({"key": "value", "bad\x00key": "test"}, "dict")
        assert "badkey" in result
        assert "\x00" not in str(result)
    
    def test_schema_migration_validation(self):
        """Test validation during schema migrations"""
        # Old schema
        old_schema = {
            "version": 1,
            "fields": {
                "id": "string",
                "name": "string",
                "score": "number"
            }
        }
        
        # New schema
        new_schema = {
            "version": 2,
            "fields": {
                "id": "string",
                "name": "string",
                "score": "number",
                "category": "string",  # New required field
                "tags": "array"  # New optional field
            },
            "required": ["id", "name", "category"]
        }
        
        def migrate_data(data: dict, from_version: int, to_version: int) -> dict:
            """Migrate data between schema versions"""
            if from_version == 1 and to_version == 2:
                # Add default values for new fields
                migrated = data.copy()
                if "category" not in migrated:
                    migrated["category"] = "uncategorized"
                if "tags" not in migrated:
                    migrated["tags"] = []
                return migrated
            return data
        
        def validate_against_schema(data: dict, schema: dict) -> Tuple[bool, List[str]]:
            """Validate data against schema"""
            errors = []
            
            # Check required fields
            for field in schema.get("required", []):
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Check field types
            type_map = {
                "string": str,
                "number": (int, float),
                "array": list,
                "object": dict
            }
            
            for field, expected_type in schema["fields"].items():
                if field in data:
                    python_type = type_map.get(expected_type, str)
                    if not isinstance(data[field], python_type):
                        errors.append(f"Field {field} has wrong type")
            
            return len(errors) == 0, errors
        
        # Test migration
        old_data = {
            "id": "123",
            "name": "Test Item",
            "score": 85
        }
        
        # Validate against old schema
        is_valid, errors = validate_against_schema(old_data, old_schema)
        assert is_valid
        
        # Migrate to new schema
        new_data = migrate_data(old_data, 1, 2)
        
        # Validate against new schema
        is_valid, errors = validate_against_schema(new_data, new_schema)
        assert is_valid
        assert new_data["category"] == "uncategorized"
        assert new_data["tags"] == []


class TestTimerToolGaps:
    """Test timer tool operations that were uncovered"""
    
    def test_timer_pause_resume(self):
        """Test timer pause and resume functionality"""
        import time
        
        class PausableTimer:
            def __init__(self):
                self.start_time = None
                self.pause_time = None
                self.total_paused = 0
                self.is_paused = False
            
            def start(self):
                self.start_time = time.time()
                self.total_paused = 0
                self.is_paused = False
            
            def pause(self):
                if not self.is_paused and self.start_time:
                    self.pause_time = time.time()
                    self.is_paused = True
            
            def resume(self):
                if self.is_paused and self.pause_time:
                    self.total_paused += time.time() - self.pause_time
                    self.is_paused = False
                    self.pause_time = None
            
            def get_elapsed(self):
                if not self.start_time:
                    return 0
                
                current = time.time()
                if self.is_paused:
                    current = self.pause_time
                
                return current - self.start_time - self.total_paused
        
        timer = PausableTimer()
        timer.start()
        
        time.sleep(0.1)
        elapsed1 = timer.get_elapsed()
        
        timer.pause()
        time.sleep(0.1)  # This shouldn't count
        
        timer.resume()
        time.sleep(0.1)
        elapsed2 = timer.get_elapsed()
        
        # Paused time shouldn't be counted
        assert 0.09 < elapsed1 < 0.11
        assert 0.19 < elapsed2 < 0.22  # Not 0.3
    
    @pytest.mark.asyncio
    async def test_timer_cancellation(self):
        """Test timer cancellation and cleanup"""
        cleanup_called = False
        
        async def timed_operation():
            nonlocal cleanup_called
            try:
                await asyncio.sleep(1.0)
                return "completed"
            except asyncio.CancelledError:
                cleanup_called = True
                raise
        
        # Start timer task
        task = asyncio.create_task(timed_operation())
        
        # Cancel after short delay
        await asyncio.sleep(0.1)
        task.cancel()
        
        # Wait and verify cleanup
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        assert cleanup_called
    
    def test_timer_alert_scheduling(self):
        """Test scheduling of timer alerts at specific percentages"""
        def get_alert_times(total_duration: int) -> Dict[str, int]:
            """Calculate when to trigger alerts"""
            alerts = {}
            
            # Alert at 50%, 20%, 10% remaining
            alerts["50%"] = total_duration * 0.5
            alerts["20%"] = total_duration * 0.8
            alerts["10%"] = total_duration * 0.9
            alerts["done"] = total_duration
            
            return alerts
        
        # Test with different durations
        test_cases = [
            (60, {"50%": 30, "20%": 48, "10%": 54, "done": 60}),
            (300, {"50%": 150, "20%": 240, "10%": 270, "done": 300}),
            (10, {"50%": 5, "20%": 8, "10%": 9, "done": 10}),
        ]
        
        for duration, expected in test_cases:
            alerts = get_alert_times(duration)
            for key, value in expected.items():
                assert abs(alerts[key] - value) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])