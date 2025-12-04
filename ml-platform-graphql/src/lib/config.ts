// Configuration module for ML Platform GraphQL
// All service URLs must be configured via environment variables
// See env.template for required configuration

export const config = {
  port: parseInt(process.env.PORT || "4000", 10),
  nodeEnv: process.env.NODE_ENV || "development",

  // Service hosts
  DEFAULT_SERVICE_HOST:
    process.env.DEFAULT_SERVICE_HOST || "http://localhost:8000",

  // ML Platform Service URLs
  // Note: All service URLs must be configured via environment variables
  // For local development with Kind/Kubernetes, services are accessible at http://<service-name>:8000
  serviceHosts: {
    // Workspace Service
    DARWIN_WORKSPACE: process.env.DARWIN_WORKSPACE_SERVICE_HOST || "",
    MLP_WORKSPACE_STAG: process.env.DARWIN_WORKSPACE_SERVICE_HOST || "",
    MLP_WORKSPACE_UAT: process.env.DARWIN_WORKSPACE_SERVICE_HOST || "",
    MLP_WORKSPACE_PROD: process.env.DARWIN_WORKSPACE_SERVICE_HOST || "",

    // Compute Service (Primary ML Platform Compute Service)
    DARWIN_COMPUTE: process.env.DARWIN_COMPUTE_SERVICE_HOST || "",
    MLP_COMPUTE_STAG: process.env.DARWIN_COMPUTE_SERVICE_HOST || "",
    MLP_COMPUTE_UAT: process.env.DARWIN_COMPUTE_SERVICE_HOST || "",
    MLP_COMPUTE_PROD: process.env.DARWIN_COMPUTE_SERVICE_HOST || "",

    // Workflows Service
    DARWIN_WORKFLOWS: process.env.DARWIN_WORKFLOWS_SERVICE_HOST || "",
    MLP_WORKFLOWS_STAG: process.env.DARWIN_WORKFLOWS_SERVICE_HOST || "",
    MLP_WORKFLOWS_UAT: process.env.DARWIN_WORKFLOWS_SERVICE_HOST || "",
    MLP_WORKFLOWS_PROD: process.env.DARWIN_WORKFLOWS_SERVICE_HOST || "",

    // Data Catalog Service
    DARWIN_DATA_CATALOG: process.env.DARWIN_DATA_CATALOG_SERVICE_HOST || "",

    // Feature Store Service
    FEATURE_STORE: process.env.FEATURE_STORE_SERVICE_HOST || "",
    FEATURE_STORE_V2: process.env.FEATURE_STORE_V2 || "",
    MLP_FEATURE_STORE: process.env.MLP_FEATURE_STORE_SERVICE_HOST || "",

    // ML Flow / Experimentation
    MLP_EXPERIMENTATION: process.env.MLP_EXPERIMENTATION_SERVICE_HOST || "",
    MLP_ML_FLOW_STAG: process.env.MLP_EXPERIMENTATION_SERVICE_HOST || "",
    MLP_ML_FLOW_UAT: process.env.MLP_EXPERIMENTATION_SERVICE_HOST || "",
    MLP_ML_FLOW_PROD: process.env.MLP_EXPERIMENTATION_SERVICE_HOST || "",

    // BYOR (Bring Your Own Runtime)
    MLP_BYOR_STAG: process.env.MLP_BYOR_SERVICE_HOST || "",
    MLP_BYOR_UAT: process.env.MLP_BYOR_SERVICE_HOST || "",
    MLP_BYOR_PROD: process.env.MLP_BYOR_SERVICE_HOST || "",

    // ML On Edge
    MLP_ON_EDGE_STAG: process.env.MLP_ON_EDGE_SERVICE_HOST || "",
    MLP_ON_EDGE_UAT: process.env.MLP_ON_EDGE_SERVICE_HOST || "",
    MLP_ON_EDGE_PROD: process.env.MLP_ON_EDGE_SERVICE_HOST || "",

    // Chronos
    MLP_CHRONOS: process.env.MLP_CHRONOS_SERVICE_HOST || "",
    MLP_CHRONOS_STAG: process.env.MLP_CHRONOS_SERVICE_HOST || "",
    MLP_CHRONOS_UAT: process.env.MLP_CHRONOS_SERVICE_HOST || "",
    MLP_CHRONOS_PROD: process.env.MLP_CHRONOS_SERVICE_HOST || "",
  },

  // Helper function to get service host by environment
  getServiceHost: (serviceName: string, environment?: string) => {
    const env = environment || process.env.NODE_ENV || "production";
    const serviceKey = `${serviceName}_${env.toUpperCase()}`;

    // Try environment-specific first
    if (config.serviceHosts[serviceKey]) {
      return config.serviceHosts[serviceKey];
    }

    // Fall back to base service name
    if (config.serviceHosts[serviceName]) {
      return config.serviceHosts[serviceName];
    }

    // Final fallback
    return config.DEFAULT_SERVICE_HOST;
  },

  // Logging
  LOG_LEVEL: process.env.LOG_LEVEL || "info",
  CURL_LOGGING: process.env.CURL_LOGGING === "true",

  // GraphQL
  ENABLE_MOCKS: process.env.ENABLE_MOCKS === "true",
  ENABLE_PLAYGROUND: process.env.ENABLE_PLAYGROUND !== "false", // enabled by default
  ENABLE_INTROSPECTION: process.env.ENABLE_INTROSPECTION !== "false", // enabled by default

  // Feature flags
  ENABLE_TRACING: process.env.ENABLE_TRACING === "true",

  // ML Flow Auth Token
  ML_FLOW_AUTH_TOKEN: process.env.ML_FLOW_AUTH_TOKEN || "",
};

export default config;

