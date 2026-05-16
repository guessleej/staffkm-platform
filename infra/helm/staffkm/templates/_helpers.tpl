{{/* Reusable helpers — 後續加 deployment 模板時用 */}}

{{- define "staffkm.fullname" -}}
{{ .Release.Name }}-{{ .Values.componentName | default "app" }}
{{- end -}}

{{- define "staffkm.labels" -}}
app.kubernetes.io/name: {{ .Values.componentName | default "app" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: staffkm
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
