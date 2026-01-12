#!/usr/bin/env python3
"""
Model downloader for pre-deployment job.

Downloads MLflow models to shared PVC cache.
Runs once before deployment (no race conditions).
"""
import os
import sys
import shutil
import time
import mlflow

# Import shared utilities
from model_utils import (
    cache_key,
    get_dir_size_mb,
    check_disk_space,
    setup_mlflow_auth,
    validate_env_vars
)


def is_model_cached(cache_dir: str, model_uri: str) -> bool:
    """Check if model is already cached and valid."""
    marker = os.path.join(cache_dir, ".download_complete")
    uri_file = os.path.join(cache_dir, ".model_uri")
    mlmodel_file = os.path.join(cache_dir, "MLmodel")
    
    # Check all required files exist
    if not (os.path.exists(marker) and os.path.exists(uri_file) and os.path.exists(mlmodel_file)):
        return False
    
    # Verify URI matches
    with open(uri_file, "r") as f:
        cached_uri = f.read().strip()
    
    return cached_uri == model_uri


def write_metadata(cache_dir: str, model_uri: str):
    """Write cache metadata files."""
    timestamp = str(time.time())
    
    with open(os.path.join(cache_dir, ".model_uri"), "w") as f:
        f.write(model_uri)
    
    with open(os.path.join(cache_dir, ".download_complete"), "w") as f:
        f.write(timestamp)
    
    with open(os.path.join(cache_dir, ".last_accessed"), "w") as f:
        f.write(timestamp)
    
    with open(os.path.join(cache_dir, ".created_at"), "w") as f:
        f.write(timestamp)


def update_access_time(cache_dir: str):
    """Update last access timestamp for cleanup tracking."""
    try:
        with open(os.path.join(cache_dir, ".last_accessed"), "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"[warn] Could not update access time: {e}")


def download_model_to_cache(model_uri: str, cache_dir: str, max_attempts: int, backoff_seconds: int):
    """
    Download model to cache with atomic write pattern.
    
    Uses staging directory and atomic rename to ensure cache consistency.
    """
    staging_dir = f"{cache_dir}.staging"
    
    try:
        # Clean staging directory
        if os.path.exists(staging_dir):
            print(f"[cleanup] Removing stale staging directory...")
            shutil.rmtree(staging_dir)
        
        os.makedirs(staging_dir, exist_ok=True)
        print(f"[download] Downloading to staging: {staging_dir}")
        
        # Retry loop
        attempt = 1
        while attempt <= max_attempts:
            try:
                start_time = time.time()
                print(f"[download] Attempt {attempt}/{max_attempts}...")
                
                # Download directly to staging
                mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=staging_dir)
                
                elapsed = time.time() - start_time
                size_mb = get_dir_size_mb(staging_dir, skip_hidden=True)
                speed = size_mb / elapsed if elapsed > 0 else 0
                
                print(f"[download] ✓ Downloaded {size_mb:.1f} MB in {elapsed:.1f}s ({speed:.1f} MB/s)")
                break
                
            except Exception as exc:
                if attempt == max_attempts:
                    raise Exception(f"Download failed after {max_attempts} attempts: {exc}")
                
                # Clean partial download before retry
                print(f"[cleanup] Removing partial download from staging...")
                if os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir)
                os.makedirs(staging_dir, exist_ok=True)
                
                wait_time = min(backoff_seconds * (2 ** (attempt - 1)), 60)
                print(f"[retry] Attempt {attempt}/{max_attempts} failed: {exc}")
                print(f"[retry] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                attempt += 1
        
        # Write metadata to staging
        write_metadata(staging_dir, model_uri)
        
        # Atomic move to final cache location
        print(f"[atomic-move] Moving to final cache location: {cache_dir}")
        if os.path.exists(cache_dir):
            # Remove old cache atomically
            old_cache = f"{cache_dir}.old"
            if os.path.exists(old_cache):
                shutil.rmtree(old_cache)
            os.rename(cache_dir, old_cache)
            os.rename(staging_dir, cache_dir)
            shutil.rmtree(old_cache)
        else:
            os.rename(staging_dir, cache_dir)
        
        print(f"[cache] ✓ Model cached successfully at {cache_dir}")
        
    except Exception as e:
        # Clean up staging on failure
        print(f"[error] Download failed, cleaning up staging directory...")
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def main():
    """Main entry point for pre-deployment model download job."""
    
    # Validate required environment variables
    env_vars = validate_env_vars("MODEL_URI", "MLFLOW_TRACKING_URI")
    model_uri = env_vars["MODEL_URI"]
    tracking_uri = env_vars["MLFLOW_TRACKING_URI"]
    
    # Optional environment variables with defaults
    cache_root = os.getenv("CACHE_PATH", "/model-cache")
    deployment_name = os.getenv("DEPLOYMENT_NAME", "unknown")
    max_attempts = int(os.getenv("MAX_RETRIES", "5"))
    backoff_seconds = int(os.getenv("BACKOFF_SECONDS", "10"))
    
    # Set up MLflow authentication
    username = os.getenv("MLFLOW_TRACKING_USERNAME")
    password = os.getenv("MLFLOW_TRACKING_PASSWORD")
    setup_mlflow_auth(tracking_uri, username, password)

    try:
        print("=" * 60)
        print("Model Pre-Download Job")
        print("=" * 60)
        print(f"Deployment: {deployment_name}")
        print(f"Model URI:  {model_uri}")
        print(f"Cache Root: {cache_root}")
        print(f"MLflow URI: {tracking_uri}")
        print()
        
        # Generate cache key (unique per deployment + model)
        ck = cache_key(deployment_name, model_uri)
        cache_dir = os.path.join(cache_root, ck)
        
        print(f"[cache-key] {ck}")
        print(f"[cache-dir] {cache_dir}")
        print()
        
        # Check if already cached
        if is_model_cached(cache_dir, model_uri):
            print("[cache-hit] ✓ Model already cached and valid")
            print(f"            URI: {model_uri}")
            
            # Update access time for cleanup tracking
            update_access_time(cache_dir)
            
            size_mb = get_dir_size_mb(cache_dir, skip_hidden=True)
            print(f"            Size: {size_mb:.1f} MB ({size_mb/1024:.2f} GB)")
            print()
            print("=" * 60)
            print("Job Complete - Model Ready")
            print("=" * 60)
            sys.exit(0)
        
        # Cache miss - need to download
        print("[cache-miss] Model not in cache, downloading...")
        print()
        
        # Estimate space needed (assume 5GB if unknown)
        # In production, you might query MLflow API for actual size
        estimated_size_mb = 5 * 1024
        check_disk_space(cache_root, estimated_size_mb)
        print()
        
        # Download to cache
        download_model_to_cache(model_uri, cache_dir, max_attempts, backoff_seconds)

        # Final summary
        final_size_mb = get_dir_size_mb(cache_dir, skip_hidden=True)
        print()
        print("=" * 60)
        print("Job Complete - Model Downloaded")
        print("=" * 60)
        print(f"✓ Model cached at: {cache_dir}")
        print(f"✓ Cache key:       {ck}")
        print(f"✓ Total size:      {final_size_mb:.1f} MB ({final_size_mb/1024:.2f} GB)")
        print(f"✓ Model URI:       {model_uri}")
        print("=" * 60)
        sys.exit(0)

    except Exception as exc:
        print()
        print("=" * 60)
        print("Job Failed")
        print("=" * 60)
        sys.stderr.write(f"ERROR: {exc}\n")
        sys.stderr.write(f"Deployment: {deployment_name}\n")
        sys.stderr.write(f"Model URI: {model_uri}\n")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

