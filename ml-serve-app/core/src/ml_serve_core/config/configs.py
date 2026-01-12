import os
from typing import Optional

from typeguard import typechecked

from ml_serve_core.constants.constants import (
    CONFIGS_MAP,
    ISTIO_SERVICE_NAME,
    ENABLE_ISTIO,
    DEFAULT_RUNTIME
)


@typechecked
class Config:
    """
    Centralized configuration management for ML Serve.
    
    Provides environment-aware configuration with sensible defaults.
    All configurations should be accessed through this class to maintain consistency.
    """

    def __init__(self):
        env = os.getenv("ENV", "local")
        self.env = env
        if self.env not in CONFIGS_MAP:
            raise ValueError(
                f"Invalid environment: {self.env}. "
                f"Valid environments are: {', '.join(CONFIGS_MAP.keys())}. "
                f"To add a new environment, update CONFIGS_MAP in constants.py"
            )
        self._config = CONFIGS_MAP[self.env]

    # Service URLs
    @property
    def dcm_url(self):
        return self._config.get("dcm_url")

    @property
    def get_artifact_builder_url(self):
        return self._config.get("artifact_builder_url")

    @property
    def get_artifact_builder_public_url(self):
        return self._config.get("artifact_builder_public_url")

    @property
    def get_darwin_workflow_url(self):
        return self._config.get("darwin_workflow_url")

    # Istio Configuration
    @property
    def get_istio_service_name(self):
        return ISTIO_SERVICE_NAME if ENABLE_ISTIO else None

    @property
    def is_istio_enabled(self):
        return ENABLE_ISTIO

    # MLflow Configuration
    @property
    def mlflow_tracking_uri(self) -> str:
        """MLflow tracking server URI"""
        return os.getenv("MLFLOW_TRACKING_URI", "")

    @property
    def mlflow_tracking_username(self) -> str:
        """MLflow tracking username for authentication"""
        return os.getenv("MLFLOW_TRACKING_USERNAME", "")

    @property
    def mlflow_tracking_password(self) -> str:
        """MLflow tracking password for authentication"""
        return os.getenv("MLFLOW_TRACKING_PASSWORD", "")

    # Model Cache Configuration
    @property
    def model_downloader_image(self) -> str:
        """
        Docker image used for model download (init container or pre-deploy job).
        Defaults to the same runtime image used for serving.
        """
        return os.getenv("MODEL_DOWNLOADER_IMAGE", DEFAULT_RUNTIME)

    @property
    def model_cache_pvc_name(self) -> str:
        """
        Name of the PVC used for shared model caching across pods.
        When using PVC strategy, this PVC is auto-created per-namespace by the Helm chart.
        Must be a ReadWriteMany (RWX) capable PVC.
        """
        return os.getenv("MODEL_CACHE_PVC_NAME", "ml-model-cache")

    @property
    def model_cache_path(self) -> str:
        """
        Path within containers where the model cache is mounted.
        For pvc strategy: /model-cache/<cache-key>/
        For emptydir strategy: /model-cache/
        """
        return os.getenv("MODEL_CACHE_PATH", "/model-cache")
