#!/usr/bin/env python3
"""
Disk space monitoring utilities for GTD Coach
Provides functions to check disk space and handle low disk situations
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class DiskSpaceError(Exception):
    """Raised when disk space is critically low"""
    pass


def get_disk_usage(path: str = "/") -> Tuple[int, int, int]:
    """
    Get disk usage statistics for a given path
    
    Args:
        path: Path to check disk usage for (default: root)
        
    Returns:
        Tuple of (total, used, free) space in bytes
    """
    stat = shutil.disk_usage(path)
    return stat.total, stat.used, stat.free


def get_disk_usage_percent(path: str = "/") -> float:
    """
    Get disk usage as a percentage
    
    Args:
        path: Path to check disk usage for (default: root)
        
    Returns:
        Disk usage percentage (0-100)
    """
    total, used, _ = get_disk_usage(path)
    if total == 0:
        return 0.0
    return (used / total) * 100


def check_disk_space(
    path: str = "/",
    warning_threshold: float = 80.0,
    critical_threshold: float = 90.0,
    min_free_gb: float = 1.0
) -> Tuple[bool, Optional[str]]:
    """
    Check if disk space is sufficient
    
    Args:
        path: Path to check
        warning_threshold: Percentage threshold for warning (default: 80%)
        critical_threshold: Percentage threshold for critical (default: 90%)
        min_free_gb: Minimum free space in GB (default: 1GB)
        
    Returns:
        Tuple of (is_ok, warning_message)
        - is_ok: True if disk space is sufficient
        - warning_message: Warning/error message if any
    """
    try:
        total, used, free = get_disk_usage(path)
        usage_percent = get_disk_usage_percent(path)
        free_gb = free / (1024 ** 3)  # Convert to GB
        
        # Check critical threshold
        if usage_percent >= critical_threshold:
            msg = (f"CRITICAL: Disk usage at {usage_percent:.1f}% "
                   f"(only {free_gb:.2f}GB free)")
            logger.critical(msg)
            return False, msg
        
        # Check minimum free space
        if free_gb < min_free_gb:
            msg = (f"CRITICAL: Only {free_gb:.2f}GB free disk space "
                   f"(minimum {min_free_gb}GB required)")
            logger.critical(msg)
            return False, msg
        
        # Check warning threshold
        if usage_percent >= warning_threshold:
            msg = (f"WARNING: Disk usage at {usage_percent:.1f}% "
                   f"({free_gb:.2f}GB free)")
            logger.warning(msg)
            return True, msg
        
        # All good
        logger.debug(f"Disk usage: {usage_percent:.1f}% ({free_gb:.2f}GB free)")
        return True, None
        
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return False, f"Error checking disk space: {e}"


def cleanup_old_logs(log_dir: Path, days_to_keep: int = 7) -> int:
    """
    Clean up old log files
    
    Args:
        log_dir: Directory containing log files
        days_to_keep: Number of days to keep logs (default: 7)
        
    Returns:
        Number of files deleted
    """
    import time
    
    if not log_dir.exists():
        return 0
    
    deleted = 0
    current_time = time.time()
    max_age_seconds = days_to_keep * 24 * 60 * 60
    
    for log_file in log_dir.glob("*.log*"):
        try:
            file_age = current_time - log_file.stat().st_mtime
            if file_age > max_age_seconds:
                log_file.unlink()
                deleted += 1
                logger.info(f"Deleted old log file: {log_file}")
        except Exception as e:
            logger.error(f"Error deleting {log_file}: {e}")
    
    return deleted


def cleanup_docker_logs() -> bool:
    """
    Attempt to clean up Docker container logs
    
    Returns:
        True if cleanup was successful
    """
    import subprocess
    
    try:
        # Truncate all Docker container logs
        cmd = "sudo sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Successfully truncated Docker container logs")
            return True
        else:
            logger.warning(f"Failed to truncate Docker logs: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error cleaning Docker logs: {e}")
        return False


def emergency_cleanup(
    log_dir: Optional[Path] = None,
    clean_docker: bool = True
) -> Tuple[bool, str]:
    """
    Perform emergency cleanup when disk space is critical
    
    Args:
        log_dir: Directory to clean logs from
        clean_docker: Whether to clean Docker logs
        
    Returns:
        Tuple of (success, message)
    """
    messages = []
    success = False
    
    # Clean old logs
    if log_dir and log_dir.exists():
        deleted = cleanup_old_logs(log_dir, days_to_keep=3)
        messages.append(f"Deleted {deleted} old log files")
        if deleted > 0:
            success = True
    
    # Clean Docker logs
    if clean_docker:
        if cleanup_docker_logs():
            messages.append("Cleaned Docker container logs")
            success = True
        else:
            messages.append("Failed to clean Docker logs (may need sudo)")
    
    # Check disk space after cleanup
    is_ok, status = check_disk_space()
    messages.append(status or "Disk space check passed")
    
    return success and is_ok, " | ".join(messages)


class DiskSpaceMonitor:
    """Context manager for monitoring disk space during operations"""
    
    def __init__(
        self,
        path: str = "/",
        warning_threshold: float = 80.0,
        critical_threshold: float = 90.0,
        auto_cleanup: bool = False,
        log_dir: Optional[Path] = None
    ):
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.auto_cleanup = auto_cleanup
        self.log_dir = log_dir
    
    def __enter__(self):
        """Check disk space on entry"""
        is_ok, msg = check_disk_space(
            self.path, 
            self.warning_threshold,
            self.critical_threshold
        )
        
        if not is_ok:
            if self.auto_cleanup:
                logger.warning("Disk space critical, attempting cleanup...")
                cleanup_ok, cleanup_msg = emergency_cleanup(self.log_dir)
                if not cleanup_ok:
                    raise DiskSpaceError(f"{msg} | Cleanup failed: {cleanup_msg}")
            else:
                raise DiskSpaceError(msg)
        elif msg:
            logger.warning(msg)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Check disk space on exit"""
        if exc_type is None:
            # No exception, check disk space again
            is_ok, msg = check_disk_space(
                self.path,
                self.warning_threshold,
                self.critical_threshold
            )
            if msg:
                logger.info(f"Post-operation: {msg}")
        return False  # Don't suppress exceptions