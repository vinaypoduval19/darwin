#!/usr/bin/env python3
"""
Simple model downloader for emptyDir strategy (init container).

Downloads MLflow model directly to pod-local storage.
No caching, no race conditions (each pod has isolated storage).
"""
import os
import sys
import time
import mlflow

# Import shared utilities
from model_utils import (
    get_dir_size_mb,
    check_disk_space,
    setup_mlflow_auth,
    validate_env_vars
)


def download_model(model_uri: str, output_path: str, max_attempts: int, backoff_seconds: int):
    """Download model with retry logic."""
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Retry loop
    attempt = 1
    while attempt <= max_attempts:
        try:
            start_time = time.time()
            print(f"[download] Attempt {attempt}/{max_attempts}...")
            
            # Download directly to output path
            mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=output_path)
            
            elapsed = time.time() - start_time
            size_mb = get_dir_size_mb(output_path)
            speed = size_mb / elapsed if elapsed > 0 else 0
            
            print(f"[download] ✓ Downloaded {size_mb:.1f} MB in {elapsed:.1f}s ({speed:.1f} MB/s)")
            return
            
        except Exception as exc:
            if attempt == max_attempts:
                raise Exception(f"Download failed after {max_attempts} attempts: {exc}")
            
            # Exponential backoff with cap
            wait_time = min(backoff_seconds * (2 ** (attempt - 1)), 60)
            print(f"[retry] Attempt {attempt}/{max_attempts} failed: {exc}")
            print(f"[retry] Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            attempt += 1


def main():
    """Main entry point for emptyDir init container."""
    
    # Validate required environment variables
    env_vars = validate_env_vars("MODEL_URI", "MLFLOW_TRACKING_URI")
    model_uri = env_vars["MODEL_URI"]
    tracking_uri = env_vars["MLFLOW_TRACKING_URI"]
    
    # Optional environment variables with defaults
    output_path = os.getenv("OUTPUT_PATH", "/models")
    max_attempts = int(os.getenv("MAX_RETRIES", "5"))
    backoff_seconds = int(os.getenv("BACKOFF_SECONDS", "10"))
    
    # Set up MLflow authentication
    username = os.getenv("MLFLOW_TRACKING_USERNAME")
    password = os.getenv("MLFLOW_TRACKING_PASSWORD")
    setup_mlflow_auth(tracking_uri, username, password)
    
    try:
        print("=" * 60)
        print("EmptyDir Model Download (Init Container)")
        print("=" * 60)
        print(f"Model URI:  {model_uri}")
        print(f"Output:     {output_path}")
        print(f"MLflow URI: {tracking_uri}")
        print()
        
        # Check disk space (estimate 5GB by default for emptydir strategy)
        check_disk_space(output_path, required_mb=5120)  # 5GB default estimate
        print()
        
        # Download model
        download_model(model_uri, output_path, max_attempts, backoff_seconds)
        
        # Final summary
        final_size_mb = get_dir_size_mb(output_path)
        print()
        print("=" * 60)
        print("Download Complete")
        print("=" * 60)
        print(f"✓ Model ready at: {output_path}")
        print(f"✓ Total size:     {final_size_mb:.1f} MB ({final_size_mb/1024:.2f} GB)")
        print(f"✓ Model URI:      {model_uri}")
        print("=" * 60)
        sys.exit(0)
        
    except Exception as exc:
        print()
        print("=" * 60)
        print("Download Failed")
        print("=" * 60)
        sys.stderr.write(f"ERROR: {exc}\n")
        sys.stderr.write(f"Model URI: {model_uri}\n")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

