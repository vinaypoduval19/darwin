import os

CONFIGS_MAP = {
    "darwin-local": {
        "mysql_db": {
            "host": f"{os.getenv('DARWIN_MYSQL_HOST')}",
            "username": f"{os.getenv('DARWIN_MYSQL_USERNAME')}",
            "password": f"{os.getenv('DARWIN_MYSQL_PASSWORD')}",
            "database": f"{os.getenv('DARWIN_MYSQL_DATABASE')}",
            "port": "3306",
        },
        "ray_job_location": "s3://local",
        "app_layer_url": "http://darwin-compute:8000",
        "s3_bucket": "s3://local/",
        "darwin_host_internal": "internal-local/",
        "fsx_root": "fsx/workspace/",
        "darwin_chronos_url": f"http://localhost:8003",
    },
}

SUCCESS = "SUCCESS"
ERROR = "ERROR"
HTTP = "http://"

RAY_JOB_SUBMIT_URL = "api/jobs/"
CODESPACE_URL = "/lab/tree/"

PROJECT_EXISTS_MESSAGE = "Project already exists"
CODESPACE_EXISTS_MESSAGE = "Codespace already exists"
GENERIC_ERROR_MESSAGE = "Something went wrong"
CREATE_PROJECT_ERROR = "Error in creating Project"
CREATE_CODESPACE_ERROR = "Error in creating Codespace"
PROJECT_VALIDATION_ERROR = "Error in validating Project"
CODESPACE_VALIDATION_ERROR = "Error in validating codespace"

CWD = "/app/core/src/workspace_core"
BASE_EFS_PATH = "/var/www/fsx/workspace"

VALID_FILE_TYPES_FOR_UPLOAD = ["json", "xlsx", "csv", "py", "txt", "zip", "tar", "tar.gz", "tgz", "whl", "jar"]
VALID_FILE_SIZE_IN_MB_FOR_UPLOAD = 1024

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

DATADOG_API_URL = "https://api.datadoghq.com/api/v1/query"

DATADOG_API_KEY = os.getenv("VAULT_SERVICE_DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("VAULT_SERVICE_DATADOG_APP_KEY")
