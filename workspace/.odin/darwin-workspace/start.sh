#!/usr/bin/env bash
set -e
echo "APP_DIR: ${APP_DIR}"
echo "ENV: ${ENV}"
echo "VPC_SUFFIX: ${VPC_SUFFIX}"
echo "TEAM_SUFFIX: ${TEAM_SUFFIX}"
echo "SERVICE_NAME: ${SERVICE_NAME}"
echo "PLATFORM: ${PLATFORM}"
echo "DEPLOYMENT_TYPE: ${DEPLOYMENT_TYPE}"
echo "NAMESPACE: ${NAMESPACE}"

echo "----- Setup log file path -----"
mkdir -p /var/log/darwin-workspace
mkdir -p /var/www/fsx/workspace/init_logs
export LOG_DIR=/var/log/darwin-workspace/


echo "Cding into app layer"
cd app-layer/src/workspace_app_layer
echo "Starting app layer"
CORES=$(nproc)
echo "CORES: $CORES"
LOG_FILE=$LOG_DIR/workspace.log opentelemetry-instrument uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
