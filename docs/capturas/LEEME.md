# Capturas del proyecto

Lista de capturas **en orden de ejecución**. Durante el trabajo se avisa en el
momento exacto de cada una con el aviso **📸 CAPTURA NN**.

## Normas para todas las capturas

- Formato PNG, guardado en esta carpeta con el nombre exacto de la tabla.
- Solo la ventana de la terminal o del navegador, sin el escritorio.
- **Tapar siempre** (rectángulo opaco, no desenfoque):
  - correo electrónico y nombre de usuario de Windows/WSL si aparecen en el prompt;
  - contraseñas y tokens (ArgoCD, Grafana, GHCR, PostgreSQL);
  - IP públicas; en Azure, también el ID de suscripción, el ID de tenant y los nombres de recursos que los incluyan.
- Las IP privadas internas de Docker y Kubernetes (10.x, 172.x) no son
  sensibles, pero se evitan cuando no aportan nada (sin `-o wide` salvo
  que se indique).

## Lista

### Fase 0 – Preparación

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 01 | `01_versiones_herramientas.png` | Tras instalar todo: `which -a docker k3d kubectl helm` y los comandos de versión | Las 4 rutas en `/usr/...` (ninguna en `/mnt/c`) y las versiones | Usuario del prompt |
| 02 | `02_nodos_k3d.png` | Tras crear el clúster: `kubectl get nodes` | 1 nodo `server` y 2 `agent`, todos `Ready` | Usuario del prompt |

### Fase 1 – Contenedor y Kubernetes básico

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 03 | `03_docker_build.png` | `docker build` y `docker image ls` | Build terminado y tamaño de la imagen | Usuario del prompt |
| 04a | `04a_docker_run_carga.png` | `docker run` del ETL contra un PostgreSQL 18.7 local (`--read-only`) | Logs de las 3 etapas, `filas insertadas` y `Carga en PostgreSQL terminada` | Contraseña si aparece en el comando |
| 04b | `04b_docker_run_consultas.png` | Consultas `psql` en el contenedor `pg-local` | Recuento de las 6 tablas (28, 17, 13529, 620, 2015, 1395) y hectáreas de España 2022-2024 desde la vista | — |
| 05 | `05_k3d_image_import.png` | `k3d image import` | Imagen importada en los 3 nodos | Usuario del prompt |
| 06 | `06_job_completado.png` | `kubectl get job,pods -n agroeco` y `kubectl logs` | Job `Complete 1/1` y final de los logs | — |
| 07 | `07_cronjob.png` | `kubectl get cronjob -n agroeco` | CronJob con horario mensual | — |
| 08a | `08a_exp_A_autocuracion.png` | Experimento A: `kubectl get pods -w` mientras se borra el pod del Job en `Running` | Pod original `Terminating` → `Completed`; pod nuevo `Pending` → `ContainerCreating` → `Running` → `Completed` | — |
| 08b | `08b_exp_A_autocuracion.png` | Experimento A: `kubectl get events` del Job | Dos `SuccessfulCreate` y `Completed` | — |
| 08c | `08c_exp_A_tiempos.png` | Experimento A (segunda ejecución): `podReplacementPolicy`, `succeeded`/`failed` y eventos con hora | `TerminatingOrFailed`, `exitosos: 1 fallidos: 1`; `Killing` 14:17:29Z → `SuccessfulCreate` 14:17:38Z (retraso de reintento de ~10 s) | — |
| 09 | `09_exp_B_job_vs_deployment.png` | Experimento B: el ETL como Deployment | `CrashLoopBackOff` / reinicios continuos frente al Job `Complete` | — |
| 10 | `10_gitleaks_fase1.png` | Cierre de la Fase 1, tras el primer commit: `gitleaks dir . --redact -v` y `gitleaks git --redact -v` | `no leaks found` en el directorio y en el historial | Usuario del prompt |

### Fase 2 – PostgreSQL con CloudNativePG

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 11 | `11_cnpg_operador.png` | `helm list -n cnpg-system` y pods del operador | Operador `Running` y versión del chart | — |
| 12a | `12a_cluster_postgres.png` | Fase 2, tras crear el Cluster: `kubectl get cluster`, pods con rol y nodo, `get pvc` y `get svc` | `Cluster in healthy state`, 2/2 instancias; primaria y réplica en **nodos distintos**; 2 PVC `Bound`; Services `-rw`, `-ro`, `-r` | Usuario del prompt |
| 12b | `12b_cnpg_status.png` | Fase 2, a continuación: `kubectl cnpg status agroeco-pg -n agroeco` | Primaria, réplica en *streaming* y estado sano del clúster | Usuario del prompt |
| 13a | `13a_consulta_datos.png` | Fase 2, tras relanzar el Job con carga: `kubectl cnpg psql` con el recuento por tabla en la primaria (y en la réplica) | Filas en las 6 tablas (28, 17, 13529, 620, 2015, 1395) y hectáreas de España desde la vista | Usuario del prompt |
| 13b | `13b_conexion_tls.png` | Fase 2, a continuación: log de `agroeco-pg-1` filtrado por `connection authorized` del ETL | `application_name=agroeco-etl SSL enabled (protocol=TLSv1.3…)` | Usuario del prompt |
| 14a | `14a_exp_C_log_cliente.png` | Experimento C, terminal Ubuntu 2: `kubectl logs -f exp-c-cliente` mientras en la terminal Ubuntu 1 se borra `agroeco-pg-1` | Líneas `primaria 13529` con la IP de `agroeco-pg-1`, los `ERROR` del corte y de nuevo `primaria 13529` con la IP de `agroeco-pg-2` | Usuario del prompt |
| 14b | `14b_exp_C_cnpg_status.png` | Experimento C, terminal Ubuntu 1, tras el failover: `kubectl cnpg status agroeco-pg -n agroeco` | Primaria `agroeco-pg-2`, réplica `agroeco-pg-1` en *streaming* y `Cluster in healthy state` | Usuario del prompt |
| 14c | `14c_exp_C_job_nueva_primaria.png` | Experimento C, terminal Ubuntu 1: Job del ETL relanzado tras el failover | Log con `Conectando a PostgreSQL (agroeco@agroeco-pg-rw…)`, las 6 tablas insertadas y `Complete 1/1` | Usuario del prompt |
| 15 | `15_gitleaks_fase2.png` | Cierre de la Fase 2, antes del commit: `gitleaks dir . --redact -v` y `gitleaks git --redact -v` | `no leaks found` en el directorio y en el historial | Usuario del prompt |
| 16a | `16a_backup_completado.png` | Fase 2, bloque de backup, terminal Ubuntu 1, tras el backup bajo demanda: `kubectl get backup -n agroeco` y `kubectl logs` del Pod `s3-listado` (listado del bucket en Garage) | Backup `completed` y objetos de la copia base y del WAL en el bucket | Claves de acceso S3 |
| 16b | `16b_restauracion.png` | Fase 2, bloque de backup, terminal Ubuntu 1, tras crear `agroeco-pg-restore` desde el backup: `kubectl get cluster -n agroeco`, recuento por tabla con `kubectl cnpg psql agroeco-pg-restore` y línea temporal | Clúster restaurado `healthy` y los mismos recuentos (28, 17, 13529, 620, 2015, 1395) | Usuario del prompt |

### Fase 3 – Helm chart propio

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 17a | `17a_helm_lint.png` | Fase 3, terminal Ubuntu 1: `helm lint --strict` con los valores por defecto, dev y prod, y `helm template … -f values-prod.yaml --show-only templates/cronjob.yaml` (primera parte) | `1 chart(s) linted, 0 chart(s) failed` en los tres; comienzo del CronJob generado: nombre `agroeco-etl-mensual`, `schedule`, `jobTemplate` y `automountServiceAccountToken: false` hasta el `securityContext` del pod | Usuario del prompt |
| 17b | `17b_helm_template_cronjob.png` | Fase 3, terminal Ubuntu 1, a continuación: resto de la misma salida de `helm template` | Contenedor, credenciales desde `agroeco-db-app`, recursos, seguridad del contenedor y volumen `pg-ca` del Secret `agroeco-pg-ca` con solo `ca.crt`, montado en `/etc/agroeco/pg-ca` en solo lectura | Usuario del prompt |
| 18 | `18_helm_install_upgrade.png` | Fase 3, terminal Ubuntu 1, tras el `helm upgrade` a `verify-full` y la ejecución manual: `helm history agroeco-etl -n agroeco` | Revisión 1 (instalación con `require`) `superseded` y revisión 2 (`verify-full`) `deployed` | Usuario del prompt |
| 18b | `18b_verify_full_negativa.png` | Fase 3, terminal Ubuntu 1, paso 5.5: `kubectl logs -n agroeco prueba-verify-full` | Caso A (`verify-full`, `agroeco-pg-rw`) y C (`require`, IP del Service) con `fe_sendauth: no password supplied`; caso B (`verify-full`, IP) rechazado con `server certificate … does not match host name` | Usuario del prompt |
| 19a1 | `19a1_exp_D_diff_configmap.png` | Experimento D (1), terminal Ubuntu 1: `diff -u` entre `helm template` (ConfigMap y CronJob) con `values-dev.yaml` (`-`) y con `values-prod.yaml` (`+`), primera parte | Los comandos; en el ConfigMap, `ETL_NIVEL_LOG` DEBUG/INFO, `ETL_CARGAR_BD` false/true y las variables `PG*` y `PGSSLROOTCERT` solo en prod; cabecera del CronJob: `schedule`, `suspend` e historial hasta `jobTemplate` | Usuario del prompt |
| 19a2 | `19a2_exp_D_diff_cronjob.png` | Experimento D (1), terminal Ubuntu 1, a continuación: resto de la misma salida | Pod del CronJob: credenciales solo en prod, requests 100m/256Mi frente a 250m/512Mi, montaje y volumen `pg-ca` solo en prod; `código diff: 1` y TTL del Job de carga inicial (3600 frente a 86400) | Usuario del prompt |
| 19b | `19b_exp_D_release_dev.png` | Experimento D (2), terminal Ubuntu 1: release dev en `agroeco-dev` con `helm list -A`, `kubectl get job,cronjob -n agroeco-dev` y final del log | Dos releases del mismo chart (`agroeco` y `agroeco-dev`); Job de dev `Complete` con `Carga en PostgreSQL omitida`; CronJob de dev suspendido | Usuario del prompt |

### Fase 4 – GitOps y CI/CD

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 20 | `20_github_actions.png` | Ejecución del workflow en GitHub | Todos los pasos en verde | Correo si aparece |
| 21 | `21_ghcr_paquete.png` | Página del paquete en ghcr.io | Imagen con su etiqueta | Correo si aparece |
| 22 | `22_argocd_app.png` | Interfaz de ArgoCD por port-forward | Aplicación `Synced` y `Healthy` | Contraseña de admin |
| 23 | `23_exp_E_drift.png` | Experimento E (1): cambio manual con `kubectl` | ArgoCD detecta `OutOfSync` y lo revierte | — |
| 24 | `24_exp_E_cambio_git.png` | Experimento E (2): commit en Git | ArgoCD aplica el cambio solo | — |

### Fase 5 – Observabilidad _(opcional)_

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 25 | `25_grafana_cnpg.png` | Dashboard de CloudNativePG en Grafana | Métricas del clúster PostgreSQL | Contraseña de Grafana |
| 26 | `26_exp_F_alerta.png` | Experimento F: Job fallido forzado | Alerta en estado `Firing` | — |

### Fase 6 – AKS _(opcional, con coste)_

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 27 | `27_aks_despliegue.png` | `kubectl get nodes` y `helm list` en AKS | Nodo `Ready` y el chart desplegado | ID de suscripción, IP pública |
| 28 | `28_aks_destroy.png` | `terraform destroy` | `Destroy complete!` | ID de suscripción |

### Cierre

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 29 | `29_exp_G_limpieza.png` | Experimento G: `k3d cluster delete` y `k3d cluster list` | Clúster borrado y lista vacía | Usuario del prompt |
