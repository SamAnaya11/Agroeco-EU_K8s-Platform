{{/*
Fragmentos reutilizables del chart. Este archivo no genera ningún objeto.
*/}}

{{/* Nombre del chart (máx. 40 caracteres: el CronJob añade "-mensual" y
     Kubernetes limita su nombre a 52) */}}
{{- define "agroeco-etl.name" -}}
{{- .Chart.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{/* Nombre base de los objetos. Con la release "agroeco-etl" queda
     "agroeco-etl" (no "agroeco-etl-agroeco-etl") */}}
{{- define "agroeco-etl.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Etiquetas que identifican los pods de esta release */}}
{{- define "agroeco-etl.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agroeco-etl.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Etiquetas estándar de todos los objetos */}}
{{- define "agroeco-etl.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{ include "agroeco-etl.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: agroeco-eu
{{- end -}}

{{/* Imagen con etiqueta fijada: image.tag o, si está vacía, appVersion */}}
{{- define "agroeco-etl.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{/* "true" si la conexión verifica la CA del servidor (verify-ca o
     verify-full). Solo entonces se monta la CA y se define PGSSLROOTCERT:
     en libpq, con una CA configurada, sslmode=require se comporta como
     verify-ca, así que "require" debe ir sin CA para significar lo que dice. */}}
{{- define "agroeco-etl.verificaCA" -}}
{{- if and .Values.postgres.enabled (has .Values.postgres.tls.sslmode (list "verify-ca" "verify-full")) -}}
true
{{- end -}}
{{- end -}}

{{/* Carpeta donde se monta la CA de PostgreSQL dentro del pod */}}
{{- define "agroeco-etl.rutaCA" -}}
/etc/agroeco/pg-ca
{{- end -}}

{{/*
PLANTILLA ÚNICA DEL JOB: la usan templates/job.yaml (carga inicial) y
templates/cronjob.yaml (jobTemplate). Antes estaba repetida en
k8s/02-job.yaml y k8s/03-cronjob.yaml.
*/}}
{{- define "agroeco-etl.jobSpec" -}}
backoffLimit: {{ .Values.ejecucion.backoffLimit }}
activeDeadlineSeconds: {{ .Values.ejecucion.activeDeadlineSeconds }}
template:
  metadata:
    labels:
      {{- include "agroeco-etl.labels" . | nindent 6 }}
  spec:
    {{- /* Cada reintento es un pod nuevo, con sus propios logs */}}
    restartPolicy: Never
    {{- /* El ETL no llama a la API de Kubernetes: su pod no recibe token */}}
    automountServiceAccountToken: false
    securityContext:
      runAsNonRoot: true
      runAsUser: 10001
      runAsGroup: 10001
      {{- /* Los volúmenes montados pertenecen al grupo 10001 */}}
      fsGroup: 10001
      seccompProfile:
        type: RuntimeDefault
    containers:
      - name: etl
        image: {{ include "agroeco-etl.image" . }}
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        envFrom:
          - configMapRef:
              name: {{ include "agroeco-etl.fullname" . }}
        {{- if .Values.postgres.enabled }}
        {{- /* Credenciales desde el Secret creado con kubectl */}}
        env:
          - name: PGUSER
            valueFrom:
              secretKeyRef:
                name: {{ .Values.postgres.credentialsSecret }}
                key: username
          - name: PGPASSWORD
            valueFrom:
              secretKeyRef:
                name: {{ .Values.postgres.credentialsSecret }}
                key: password
        {{- end }}
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
        volumeMounts:
          - name: datos
            mountPath: /datos
          - name: tmp
            mountPath: /tmp
          {{- if include "agroeco-etl.verificaCA" . }}
          {{- /* Carpeta completa, sin subPath: así la renovación de la CA
                 que hace CloudNativePG llega al pod */}}
          - name: pg-ca
            mountPath: {{ include "agroeco-etl.rutaCA" . }}
            readOnly: true
          {{- end }}
    volumes:
      - name: datos
        emptyDir:
          sizeLimit: {{ .Values.volumenes.datos }}
      - name: tmp
        emptyDir:
          sizeLimit: {{ .Values.volumenes.tmp }}
      {{- if include "agroeco-etl.verificaCA" . }}
      - name: pg-ca
        secret:
          secretName: {{ .Values.postgres.tls.caSecret }}
          {{- /* Solo el certificado público: ca.key no se monta */}}
          items:
            - key: ca.crt
              path: ca.crt
      {{- end }}
{{- end -}}
