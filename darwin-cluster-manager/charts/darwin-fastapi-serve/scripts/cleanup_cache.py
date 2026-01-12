#!/usr/bin/env python3
"""
Cache cleanup script for PVC strategy.

Scans the model cache directory and removes entries that haven't been
accessed within the configured TTL.
"""
import os
import shutil
import time
import sys

# Import shared utilities
from model_utils import get_dir_size_mb, validate_env_vars

def cleanup_cache(cache_root: str, ttl_hours: float, min_free_gb: float):
    """
    Remove old cache entries to free up space.
    
    Args:
        cache_root: Root directory of model cache
        ttl_hours: Age in hours to consider an entry "old"
        min_free_gb: Minimum free space target (aggressive cleanup if below this)
    """
    if not os.path.exists(cache_root):
        print(f"[cleanup] Cache root not found: {cache_root}")
        return

    print(f"[cleanup] Scanning {cache_root}...")
    print(f"[cleanup] Policy: TTL={ttl_hours}h, Target Free={min_free_gb}GB")
    
    entries = []
    now = time.time()
    ttl_seconds = ttl_hours * 3600
    
    # 1. Scan all cache entries
    for entry_name in os.listdir(cache_root):
        entry_path = os.path.join(cache_root, entry_name)
        if not os.path.isdir(entry_path) or entry_name.startswith('.'):
            continue
            
        # Check last access time
        last_access_file = os.path.join(entry_path, ".last_accessed")
        if os.path.exists(last_access_file):
            try:
                with open(last_access_file, "r") as f:
                    last_access = float(f.read().strip())
            except:
                last_access = os.path.getmtime(entry_path)
        else:
            # Fallback to filesystem mtime
            last_access = os.path.getmtime(entry_path)
            
        age_hours = (now - last_access) / 3600
        size_mb = get_dir_size_mb(entry_path)
        
        entries.append({
            "path": entry_path,
            "name": entry_name,
            "age_hours": age_hours,
            "last_access": last_access,
            "size_mb": size_mb
        })

    # 2. Sort by age (oldest first)
    entries.sort(key=lambda x: x["last_access"])
    
    deleted_count = 0
    freed_mb = 0.0
    
    # 3. Check disk space
    total, used, free = shutil.disk_usage(cache_root)
    free_gb = free / (1024**3)
    
    print(f"[cleanup] Current disk status: {free_gb:.2f} GB free")
    
    # 4. Cleanup Logic
    for entry in entries:
        should_delete = False
        reason = ""
        
        # Condition A: Expired TTL
        if entry["age_hours"] > ttl_hours:
            should_delete = True
            reason = f"Expired (Age: {entry['age_hours']:.1f}h > {ttl_hours}h)"
            
        # Condition B: Disk pressure (aggressive cleanup)
        elif free_gb < min_free_gb:
            should_delete = True
            reason = f"Disk Pressure ({free_gb:.2f}GB < {min_free_gb}GB)"
        
        if should_delete:
            print(f"[delete] Removing {entry['name']} ({entry['size_mb']:.1f} MB) - {reason}")
            try:
                shutil.rmtree(entry["path"])
                deleted_count += 1
                freed_mb += entry["size_mb"]
                
                # Update free space tracking if we deleted for disk pressure
                if free_gb < min_free_gb:
                    # Roughly estimate new free space
                    free_gb += (entry["size_mb"] / 1024)
            except Exception as e:
                print(f"[error] Failed to remove {entry['name']}: {e}")
                
    print("=" * 60)
    print(f"Cleanup Complete")
    print(f"Removed: {deleted_count} entries")
    print(f"Freed:   {freed_mb:.1f} MB")
    print("=" * 60)

def main():
    env_vars = validate_env_vars("CACHE_PATH")
    cache_path = env_vars["CACHE_PATH"]
    
    ttl_hours = float(os.getenv("CLEANUP_TTL_HOURS", "24"))
    min_free_gb = float(os.getenv("MIN_FREE_GB", "10"))
    
    cleanup_cache(cache_path, ttl_hours, min_free_gb)

if __name__ == "__main__":
    main()

