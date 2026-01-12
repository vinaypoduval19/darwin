#!/usr/bin/env python3
"""
Shared utility functions for model downloading and caching.

This module contains common functionality used by:
- download_model.py (PVC strategy pre-deploy job)
- download_model_emptydir.py (EmptyDir strategy init container)
- cleanup_cache.py (Cache cleanup CronJob)
"""
import os
import hashlib
import shutil
import time
from typing import Optional


def cache_key(deployment_name: str, model_uri: str) -> str:
    """
    Generate unique cache key for deployment + model URI.
    
    Uses SHA256 to match Helm's sha256sum function.
    Includes deployment name to allow multiple deployments to share same PVC.
    
    Args:
        deployment_name: Full deployment name
        model_uri: MLflow model URI
        
    Returns:
        64-character SHA256 hex digest
    """
    combined = f"{deployment_name}:{model_uri}"
    return hashlib.sha256(combined.encode()).hexdigest()


def get_dir_size_mb(path, skip_hidden: bool = False) -> float:
    """
    Calculate directory size in MB.
    
    Args:
        path: Directory path to measure (str or Path)
        skip_hidden: If True, skip files starting with '.' (metadata files)
        
    Returns:
        Size in megabytes
    """
    from pathlib import Path
    
    path = Path(path) if not isinstance(path, Path) else path
    
    if not path.exists():
        return 0.0
    
    total = 0
    for item in path.rglob('*'):
        if item.is_file():
            # Skip metadata files if requested
            if skip_hidden and item.name.startswith('.'):
                continue
            total += item.stat().st_size
    
    return total / (1024 * 1024)


def check_disk_space(path: str, required_mb: float, safety_factor: float = 1.5) -> None:
    """
    Check if sufficient disk space is available.
    
    Args:
        path: Directory path to check
        required_mb: Required space in MB
        safety_factor: Multiplier for safety buffer (default 1.5x)
        
    Raises:
        Exception: If insufficient disk space available
    """
    # Get parent directory if path doesn't exist yet
    check_path = path if os.path.exists(path) else os.path.dirname(path)
    if not check_path or not os.path.exists(check_path):
        check_path = "/"
    
    stat = shutil.disk_usage(check_path)
    available_mb = stat.free / (1024 * 1024)
    required_with_buffer_mb = required_mb * safety_factor
    
    if available_mb < required_with_buffer_mb:
        raise Exception(
            f"Insufficient disk space: {available_mb:.1f} MB available, "
            f"{required_with_buffer_mb:.1f} MB required (including {safety_factor}x safety buffer)"
        )
    
    print(f"[disk-check] {available_mb:.1f} MB available, {required_with_buffer_mb:.1f} MB required (OK)")


def retry_with_backoff(func, max_attempts: int, backoff_seconds: int, operation_name: str = "Operation"):
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: Callable to execute
        max_attempts: Maximum number of retry attempts
        backoff_seconds: Initial backoff time in seconds (doubles each retry)
        operation_name: Name of operation for logging
        
    Returns:
        Return value of func if successful
        
    Raises:
        Exception: If all retry attempts fail
    """
    attempt = 1
    while attempt <= max_attempts:
        try:
            print(f"[{operation_name.lower()}] Attempt {attempt}/{max_attempts}...")
            return func()
        except Exception as exc:
            if attempt == max_attempts:
                raise Exception(f"{operation_name} failed after {max_attempts} attempts: {exc}")
            
            # Exponential backoff with cap at 60 seconds
            wait_time = min(backoff_seconds * (2 ** (attempt - 1)), 60)
            print(f"[retry] Attempt {attempt}/{max_attempts} failed: {exc}")
            print(f"[retry] Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            attempt += 1


def format_size(size_bytes: Optional[int]) -> str:
    """
    Format byte size in human-readable format.
    
    Args:
        size_bytes: Size in bytes, or None
        
    Returns:
        Formatted string (e.g., "1.50 MB", "2.00 GB")
    """
    if not size_bytes:
        return "unknown"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_idx = 0
    
    while size >= 1024 and unit_idx < len(units) - 1:
        size /= 1024
        unit_idx += 1
    
    return f"{size:.2f} {units[unit_idx]}"


def setup_mlflow_auth(tracking_uri: str, username: Optional[str] = None, password: Optional[str] = None):
    """
    Configure MLflow tracking URI and authentication.
    
    Args:
        tracking_uri: MLflow tracking server URL
        username: Optional MLflow username
        password: Optional MLflow password
    """
    import mlflow
    
    mlflow.set_tracking_uri(tracking_uri)
    
    if username:
        os.environ["MLFLOW_TRACKING_USERNAME"] = username
    if password:
        os.environ["MLFLOW_TRACKING_PASSWORD"] = password


def validate_env_vars(*required_vars: str) -> dict:
    """
    Validate that required environment variables are set.
    
    Args:
        *required_vars: Names of required environment variables
        
    Returns:
        Dictionary of var_name -> value
        
    Raises:
        SystemExit: If any required variable is missing
    """
    import sys
    
    values = {}
    missing = []
    
    for var_name in required_vars:
        value = os.getenv(var_name)
        if not value:
            missing.append(var_name)
        else:
            values[var_name] = value
    
    if missing:
        for var in missing:
            print(f"[ERROR] Required environment variable not set: {var}", file=sys.stderr)
        sys.exit(1)
    
    return values

