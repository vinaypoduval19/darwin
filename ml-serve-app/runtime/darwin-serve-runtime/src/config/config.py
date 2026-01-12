import os
from typing import Optional

from typeguard import typechecked


@typechecked
class Config:
    """
    Config class to get the configuration from environment variables
    """

    def __init__(self, env: Optional[str] = None):
        if not env:
            env = os.getenv("ENV", "local")

        self.env = env
        self.feature_store_url = os.getenv("FEATURE_STORE_URL")
        self.ofs_admin_url = os.getenv("OFS_ADMIN_URL")
        self.model_uri = os.getenv("MLFLOW_MODEL_URI")
        self.model_local_path = os.getenv("MODEL_LOCAL_PATH")
        self.mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        self.mlflow_tracking_username = os.getenv("MLFLOW_TRACKING_USERNAME")
        self.mlflow_tracking_password = os.getenv("MLFLOW_TRACKING_PASSWORD")

        # Validate required configuration
        self._validate_config()

    def _validate_config(self):
        """Validate that required configuration values are set.

        If a local path is provided (MODEL_LOCAL_PATH), we can skip MLflow tracking
        configuration. Otherwise, require the MLflow tracking settings to be present.
        """
        if self.model_local_path:
            # Local path mode: require at least one source (path or uri)
            return

        required_configs = {
            "MLFLOW_MODEL_URI": self.model_uri,
            "MLFLOW_TRACKING_URI": self.mlflow_tracking_uri,
            "MLFLOW_TRACKING_USERNAME": self.mlflow_tracking_username,
            "MLFLOW_TRACKING_PASSWORD": self.mlflow_tracking_password,
        }
        
        missing_configs = [key for key, value in required_configs.items() if not value]
        
        if missing_configs:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_configs)}"
            )

    @property
    def get_env(self):
        return self.env

    @property
    def get_feature_store_url(self):
        return self.feature_store_url

    @property
    def get_ofs_admin_url(self):
        return self.ofs_admin_url

    @property
    def get_model_uri(self):
        return self.model_uri

    @property
    def get_model_local_path(self):
        return self.model_local_path

    @property
    def get_mlflow_tracking_uri(self):
        return self.mlflow_tracking_uri

    @property
    def get_mlflow_tracking_username(self):
        return self.mlflow_tracking_username

    @property
    def get_mlflow_tracking_password(self):
        return self.mlflow_tracking_password
