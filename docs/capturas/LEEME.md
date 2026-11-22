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

### Fase 2 – PostgreSQL con CloudNativePG

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 10 | `10_cnpg_operador.png` | `helm list -n cnpg-system` y pods del operador | Operador `Running` y versión del chart | — |
| 11 | `11_cluster_postgres.png` | `kubectl get cluster,pods,pvc -n agroeco` | 2 instancias (primaria y réplica) `Running` y PVC `Bound` | — |
| 12 | `12_consulta_datos.png` | Consulta `psql` de recuento por tabla | Filas cargadas en las 6 tablas | Contraseña |
| 13 | `13_exp_C_failover.png` | Experimento C: borrar el pod primario | Cambio de primaria y la consulta sigue respondiendo | — |
| 14 | `14_backup_barman.png` | _(opcional)_ Backup con el Barman Cloud Plugin | Backup `completed` y objetos en el bucket | Claves de acceso S3 |

### Fase 3 – Helm chart propio

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 15 | `15_helm_lint_template.png` | `helm lint` y extracto de `helm template` | `0 chart(s) failed` y el CronJob generado | — |
| 16 | `16_helm_install_upgrade.png` | `helm history` tras instalar y actualizar | Revisiones 1 y 2 | — |
| 17 | `17_exp_D_entornos.png` | Experimento D: `helm diff` / `diff` de dev y prod | Diferencias de horario y recursos | — |

### Fase 4 – GitOps y CI/CD

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 18 | `18_github_actions.png` | Ejecución del workflow en GitHub | Todos los pasos en verde | Correo si aparece |
| 19 | `19_ghcr_paquete.png` | Página del paquete en ghcr.io | Imagen con su etiqueta | Correo si aparece |
| 20 | `20_argocd_app.png` | Interfaz de ArgoCD por port-forward | Aplicación `Synced` y `Healthy` | Contraseña de admin |
| 21 | `21_exp_E_drift.png` | Experimento E (1): cambio manual con `kubectl` | ArgoCD detecta `OutOfSync` y lo revierte | — |
| 22 | `22_exp_E_cambio_git.png` | Experimento E (2): commit en Git | ArgoCD aplica el cambio solo | — |

### Fase 5 – Observabilidad _(opcional)_

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 23 | `23_grafana_cnpg.png` | Dashboard de CloudNativePG en Grafana | Métricas del clúster PostgreSQL | Contraseña de Grafana |
| 24 | `24_exp_F_alerta.png` | Experimento F: Job fallido forzado | Alerta en estado `Firing` | — |

### Fase 6 – AKS _(opcional, con coste)_

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 25 | `25_aks_despliegue.png` | `kubectl get nodes` y `helm list` en AKS | Nodo `Ready` y el chart desplegado | ID de suscripción, IP pública |
| 26 | `26_aks_destroy.png` | `terraform destroy` | `Destroy complete!` | ID de suscripción |

### Cierre

| Nº | Archivo | Paso exacto | Qué debe verse | Tapar |
|----|---------|-------------|----------------|-------|
| 27 | `27_exp_G_limpieza.png` | Experimento G: `k3d cluster delete` y `k3d cluster list` | Clúster borrado y lista vacía | Usuario del prompt |
