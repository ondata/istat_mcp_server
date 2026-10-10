{{- define "istat-mcp-server.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "istat-mcp-server.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "istat-mcp-server.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "istat-mcp-server.namespace" -}}
{{- default .Release.Namespace .Values.namespace }}
{{- end }}

{{- define "istat-mcp-server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "istat-mcp-server.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "istat-mcp-server.labels" -}}
helm.sh/chart: {{ include "istat-mcp-server.chart" . }}
{{ include "istat-mcp-server.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: server
{{- end }}

{{- define "istat-mcp-server.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "istat-mcp-server.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "istat-mcp-server.gateway.name" -}}
{{- .Values.gateway.name | default (printf "%s-gateway" (include "istat-mcp-server.fullname" .)) }}
{{- end }}

{{/* Istio pod labels: ambient dataplane mode (+ optional waypoint) or sidecar injection. */}}
{{- define "istat-mcp-server.meshLabels" -}}
{{- if .Values.mesh.enabled -}}
{{- if eq .Values.mesh.mode "ambient" -}}
istio.io/dataplane-mode: {{ .Values.mesh.ambient.dataplaneMode | default "ambient" | quote }}
{{- with .Values.mesh.ambient.waypoint }}
istio.io/use-waypoint: {{ . | quote }}
{{- end }}
{{- else -}}
{{- with .Values.mesh.podLabels }}
{{- toYaml . }}
{{- end }}
{{- end }}
{{- end -}}
{{- end }}
