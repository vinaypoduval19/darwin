{{/*
Expand the name of the chart.
*/}}
{{- define "service-deployment.name" -}}
{{- default .Values.name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "service-deployment.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Values.name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "service-deployment.serviceName" -}}
{{- if .Values.serviceName }}
{{- .Values.serviceName }}
{{- else }}
{{- include "service-deployment.fullname" . }}
{{- end }}
{{- end }}

{{- define "service-deployment.ingressServiceName" -}}
{{- if .Values.serviceName }}
{{- .Values.serviceName }}
{{- else }}
{{- include "service-deployment.fullname" . }}
{{- end }}
{{- end }}


{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "service-deployment.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "service-deployment.labels" -}}
helm.sh/chart: {{ include "service-deployment.chart" . }}
{{ include "service-deployment.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
darwin.dream11.com/resource-instance-id: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
tags.datadoghq.com/env: k8s-{{ .Values.envs.ENV }}{{ .Values.envs.TEAM_SUFFIX }}{{ .Values.envs.VPC_SUFFIX }}
tags.datadoghq.com/service: {{ .Values.name | quote }}
tags.datadoghq.com/version: {{ .Values.image.tag | quote  }}
com.dreamsports.{{ .Values.org  }}/service: {{ .Values.name | quote }}
{{- range $key, $value := .Values.labels }}
com.dreamsports.{{ $.Values.org  }}/{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "service-deployment.selectorLabels" -}}
app.kubernetes.io/name: {{ include "service-deployment.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "service-deployment.serviceAccountName" -}}
{{- if .Values.serviceAccount.enabled }}
{{- default (include "service-deployment.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the tls secret for secure port
*/}}
{{- define "service-deployment.tlsSecretName" -}}
{{- $fullname := include "service-deployment.fullname" . -}}
{{- default (printf "%s-tls" $fullname) .Values.tls.secretName }}
{{- end }}

{{- define "service-deployment.podAnnotations" -}}
{{- end }}


{{- define "service-deployment.ingressInt.alb-annotations" -}}
alb.ingress.kubernetes.io/healthcheck-path: {{ .Values.ingressInt.healthcheckPath }}
alb.ingress.kubernetes.io/scheme: "internal"
alb.ingress.kubernetes.io/target-type: "ip"
kubernetes.io/ingress.class: "alb"
{{ if .Values.ingressInt.tags }}
alb.ingress.kubernetes.io/tags: {{ .Values.ingressInt.tags }}
{{- end }}
{{ if .Values.ingressInt.inboundCIDRs }}
alb.ingress.kubernetes.io/inbound-cidrs: {{ .Values.ingressInt.inboundCIDRs }}
{{- end }}
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=120
{{- if $.Values.ingressInt.albLogs.enabled -}}
{{- $fullName := include "service-deployment-lib-chart.fullname" $ -}}
alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket={{ $.Values.ingressInt.albLogs.bucket }},access_logs.s3.prefix={{ $fullName }}-{{ .Release.Namespace }}-internal
{{- end }}
{{- end }}

{{- define "service-deployment.ingressInt.nginx-annotations" -}}
nginx.ingress.kubernetes.io/rewrite-target: /$2
nginx.ingress.kubernetes.io/ssl-redirect: "false"
kubernetes.io/ingress.class: {{ .Values.ingressInt.ingressClass }}
{{- end }}

{{- define "service-deployment.ingressExt.alb-annotations" -}}
alb.ingress.kubernetes.io/healthcheck-path: {{ .Values.ingressInt.healthcheckPath }}
alb.ingress.kubernetes.io/scheme: "internet-facing"
alb.ingress.kubernetes.io/target-type: "ip"
kubernetes.io/ingress.class: "alb"
{{ if .Values.ingressExt.tags }}
alb.ingress.kubernetes.io/tags: {{ .Values.ingressExt.tags }}
{{- end }}
{{ if .Values.ingressExt.inboundCIDRs }}
alb.ingress.kubernetes.io/inbound-cidrs: {{ .Values.ingressExt.inboundCIDRs }}
{{- end }}
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=120
{{- if $.Values.ingressInt.albLogs.enabled -}}
{{- $fullName := include "service-deployment-lib-chart.fullname" $ -}}
alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket={{ $.Values.ingressInt.albLogs.bucket }},access_logs.s3.prefix={{ $fullName }}-{{ .Release.Namespace }}-internal
{{- end }}
{{- end }}

{{- define "service-deployment.ingressExt.nginx-annotations" -}}
nginx.ingress.kubernetes.io/rewrite-target: /
nginx.ingress.kubernetes.io/ssl-redirect: "false"
kubernetes.io/ingress.class: {{ .Values.ingressExt.ingressClass }}
{{- end }}

{{/*
Generate model cache key (hash of deployment name + model URI)

Used for PVC strategy to create unique subdirectories for each deployment's model.
Multiple deployments can share the same PVC without conflicts.

Example: /model-cache/<cache-key>/MLmodel

Cache key format: SHA256(deploymentName:modelUri)
This ensures:
  - Same deployment + same model = same cache (reuse)
  - Different deployment or model = different cache (isolation)
*/}}
{{- define "service-deployment.modelCacheKey" -}}
{{- $deploymentName := (include "service-deployment.fullname" .) -}}
{{- $modelUri := .Values.modelCache.modelUri -}}
{{- $combined := (printf "%s:%s" $deploymentName $modelUri) -}}
{{- sha256sum $combined -}}
{{- end }}