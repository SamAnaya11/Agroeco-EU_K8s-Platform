# Reconstrucción del clúster desde el repositorio (Experimento G)

Runbook para borrar el clúster k3d `agroeco` y reconstruirlo solo con lo que
hay en este repositorio, más los valores secretos que se regeneran sin
mostrarse. El objetivo es comprobar que el proyecto se reproduce de cero y
medir cuánto tarda cada bloque.

**Resultado final esperado:**
- El ETL ha cargado las 6 tablas en PostgreSQL, con TLS `verify-full`.
- ArgoCD está `Synced`/`Healthy` en `main`.
- El WAL se archiva en Garage (S3) y hay un backup `completed`.
- La alerta `AgroecoEtlJobFallido` está cargada en Prometheus.

## Antes de empezar

- **Terminales.** **Ubuntu 1** ejecuta los bloques. **Ubuntu 2** se usa para
  los `kubectl port-forward`, que se quedan abiertos. Las dos están en
  `/mnt/c/Cloud-DevOps/Cloud-Data_Projects/Agroeco-EU_K8s-Platform`.
- **Cronometraje.** Cada bloque empieza y termina con un `echo` de la hora
  UTC. Copia esas horas a la tabla final.
- **Reglas de los secretos:**
  - Ningún valor secreto aparece en pantalla ni se guarda en un archivo.
  - Los valores aleatorios se generan con `openssl` y pasan a
    `kubectl create secret` en variables de shell. Las variables se borran
    con `unset` al final del bloque.
  - Las contraseñas que tiene que conocer una persona (admin de ArgoCD,
    admin de Grafana) van al portapapeles con `clip.exe`.
  - Los comandos de los secretos no contienen ningún valor, así que el
    historial de bash tampoco los guarda.
- **Lo que se pierde al borrar el clúster.** El bucket de Garage está dentro
  del clúster (limitación aceptada, ver la decisión sobre Garage en el
  README): **los backups y el WAL archivado desaparecen con él**. Los datos
  se vuelven a cargar desde Eurostat, que es la fuente. Si Eurostat hubiera
  publicado datos nuevos desde la última carga, los recuentos podrían
  cambiar, y eso no sería un error de la reconstrucción.
- **Nueva CA de PostgreSQL.** CloudNativePG genera una CA nueva en el Secret
  `agroeco-pg-ca`. Todo lo que verifica el servidor (el ETL y el Pod de
  `k8s/experimentos/verify-full-negativa.yaml`) monta ese Secret. No se
  reutiliza ninguna copia de la CA antigua que pudiera haber en WSL.
- **Herramientas en WSL.** Comprueba con `which -a` que las rutas están en
  `/usr/...`:
  - Docker Engine, k3d 5.9.0, kubectl v1.37.2 y Helm v4.3.2.
  - El plugin `kubectl cnpg` 1.30.2.
  - `openssl`, `python3` y `curl`.

---

## Bloque 0 · Foto del estado antes de borrar (solo lectura)

**Terminal: Ubuntu 1** (más Ubuntu 2 para el port-forward de Prometheus).

```bash
echo "BLOQUE 0 $(date -u +%H:%M:%S)"
mkdir -p ~/exp-g && cd /mnt/c/Cloud-DevOps/Cloud-Data_Projects/Agroeco-EU_K8s-Platform

# Consultas comunes a la foto y a la comparación
SQL="SELECT 'dim_pais', count(*) FROM dim_pais
UNION ALL SELECT 'dim_cultivo', count(*) FROM dim_cultivo
UNION ALL SELECT 'fact_superficie', count(*) FROM fact_superficie
UNION ALL SELECT 'fact_pct_sau', count(*) FROM fact_pct_sau
UNION ALL SELECT 'fact_operadores', count(*) FROM fact_operadores
UNION ALL SELECT 'fact_ganaderia', count(*) FROM fact_ganaderia"

foto() {   # uso: foto antes | foto despues
  local f=~/exp-g/$1
  # 1. Filas por tabla, en la primaria (psql dentro del pod, sin contraseña)
  local P; P=$(kubectl get cluster agroeco-pg -n agroeco -o jsonpath='{.status.currentPrimary}')
  kubectl exec -n agroeco "$P" -c postgres -- psql -d agroeco -AtF ' ' -c "$SQL" > "$f-filas.txt"
  # 2. Application de ArgoCD
  kubectl get application agroeco-etl -n argocd \
    -o jsonpath='{.status.sync.revision} {.status.sync.status} {.status.health.status}{"\n"}' > "$f-argocd.txt"
  # 3. Pods por namespace y estado
  kubectl get pods -A --no-headers | awk '{print $1, $4}' | sort | uniq -c > "$f-pods.txt"
  # 4. Releases de Helm
  helm list -A -o table > "$f-helm.txt"
  # 5. Objetivos de Prometheus (requiere el port-forward 9090 de Ubuntu 2)
  curl -s 'http://localhost:9090/api/v1/targets?state=active' | python3 -c '
import json, sys, collections
t = json.load(sys.stdin)["data"]["activeTargets"]
print(len(t), "objetivos;", sum(x["health"] != "up" for x in t), "caídos")
for job, n in sorted(collections.Counter(x["labels"]["job"] for x in t).items()):
    print(f"  {n:2} {job}")' > "$f-prometheus.txt"
  # 6. Backups y ventana de recuperación del ObjectStore
  { kubectl get backup -n agroeco \
      -o custom-columns=NOMBRE:.metadata.name,FASE:.status.phase,ID:.status.backupId,FIN:.status.stoppedAt
    kubectl get objectstore agroeco-backup-store -n agroeco \
      -o jsonpath='{"Ventana de recuperación: "}{.status.serverRecoveryWindow}{"\n"}'; } > "$f-backups.txt"
  for x in filas argocd pods helm prometheus backups; do echo "== $x"; cat "$f-$x.txt"; done
}
```

**Ubuntu 2:**

```bash
kubectl port-forward -n monitoring svc/kps-prometheus 9090:9090
```

**Ubuntu 1:**

```bash
foto antes
# Contenido del bucket (Pod de un solo uso; no muestra credenciales)
kubectl apply -f k8s/utilidades/s3-listado.yaml
kubectl wait -n agroeco --for=jsonpath='{.status.phase}'=Succeeded pod/s3-listado --timeout=120s
kubectl logs -n agroeco s3-listado | tail -3 | tee ~/exp-g/antes-bucket.txt
kubectl delete -f k8s/utilidades/s3-listado.yaml
echo "FIN BLOQUE 0 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- **Filas:** `dim_pais 28`, `dim_cultivo 17`, `fact_superficie 13529`,
  `fact_pct_sau 620`, `fact_operadores 2015` y `fact_ganaderia 1395`.
- **ArgoCD:** el SHA de `main`, `Synced Healthy`.
- **Prometheus:** `23 objetivos; 0 caídos`.
- **Backups:** `agroeco-pg-backup-manual` `completed`, con el total de
  objetos y bytes del bucket.

Cierra el port-forward de Ubuntu 2 (Ctrl+C).

---

## Bloque 1 · Borrar el clúster

**Terminal: Ubuntu 1.** Captura `29_exp_G_limpieza.png` justo después del
`k3d cluster list`.

```bash
echo "BLOQUE 1 $(date -u +%H:%M:%S)"
k3d cluster delete agroeco
k3d cluster list
docker ps --filter name=k3d-agroeco --format '{{.Names}}'
echo "FIN BLOQUE 1 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `Successfully deleted cluster agroeco!`.
- `k3d cluster list` solo muestra la cabecera.
- `docker ps` no devuelve ningún contenedor `k3d-agroeco-*`.

---

## Bloque 2 · Crear el clúster

**Terminal: Ubuntu 1.** Usa la configuración del repositorio,
[`k3d/cluster.yaml`](../k3d/cluster.yaml): 1 server, 2 agents, k3s
`v1.37.2-k3s1`, la API en `127.0.0.1:6550` y Traefik desactivado.

```bash
echo "BLOQUE 2 $(date -u +%H:%M:%S)"
k3d cluster create --config k3d/cluster.yaml
kubectl config current-context
kubectl wait --for=condition=Ready nodes --all --timeout=180s
kubectl get nodes -o wide
echo "FIN BLOQUE 2 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- El contexto es `k3d-agroeco`.
- Hay 3 nodos `Ready` (`k3d-agroeco-server-0`, `-agent-0` y `-agent-1`),
  todos en `v1.37.2+k3s1`.
- `kubectl get pods -n kube-system` no muestra ningún pod de Traefik.

---

## Bloque 3 · cert-manager

**Terminal: Ubuntu 1.** Lo necesita el Barman Cloud Plugin para el TLS
mutuo con el operador.

```bash
echo "BLOQUE 3 $(date -u +%H:%M:%S)"
helm install cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.21.3 \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true \
  --wait --timeout 5m
kubectl wait --for=condition=Available deployment --all -n cert-manager --timeout=180s
kubectl get pods -n cert-manager
echo "FIN BLOQUE 3 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `STATUS: deployed`.
- 3 pods `1/1 Running`: `cert-manager`, `cert-manager-cainjector` y
  `cert-manager-webhook`.
- `kubectl get crd | grep -c cert-manager.io` devuelve `6`.

---

## Bloque 4 · Operador CloudNativePG

**Terminal: Ubuntu 1.**

```bash
echo "BLOQUE 4 $(date -u +%H:%M:%S)"
helm repo add cnpg https://cloudnative-pg.github.io/charts --force-update
helm repo update cnpg
helm install cnpg cnpg/cloudnative-pg \
  --version 0.29.2 \
  --namespace cnpg-system --create-namespace \
  --wait --timeout 5m
kubectl rollout status deployment/cnpg-cloudnative-pg -n cnpg-system --timeout=180s
helm list -n cnpg-system
echo "FIN BLOQUE 4 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- La release `cnpg` en `deployed`, con `cloudnative-pg-0.29.2` y APP VERSION
  `1.30.2`.
- `deployment "cnpg-cloudnative-pg" successfully rolled out`.

---

## Bloque 5 · Barman Cloud Plugin

**Terminal: Ubuntu 1.** Necesita cert-manager (bloque 3) y el operador
(bloque 4).

```bash
echo "BLOQUE 5 $(date -u +%H:%M:%S)"
helm install plugin-barman-cloud cnpg/plugin-barman-cloud \
  --version 0.9.0 \
  --namespace cnpg-system \
  --wait --timeout 5m
kubectl rollout status deployment/plugin-barman-cloud -n cnpg-system --timeout=180s
kubectl wait --for=condition=Ready certificate --all -n cnpg-system --timeout=180s
kubectl get certificate -n cnpg-system
echo "FIN BLOQUE 5 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `STATUS: deployed` (chart 0.9.0, app v0.16.0).
- `deployment "plugin-barman-cloud" successfully rolled out`.
- Los certificados `barman-cloud-client` y `barman-cloud-server` en
  `READY True`.

---

## Bloque 6 · Namespaces del proyecto

**Terminal: Ubuntu 1.** Se crean con sus etiquetas de Pod Security antes de
que entre ningún pod:
- `agroeco` y `argocd`: `restricted`.
- `monitoring`: `privileged` solo por node-exporter, con `warn` y `audit`
  en `restricted`.
- `garage`: se aplica solo el Namespace de `k8s/05-garage.yaml`. El
  selector `!app.kubernetes.io/name` deja fuera los demás objetos del
  archivo, que sí llevan esa etiqueta. Así el Secret de Garage existe antes
  que su StatefulSet.

```bash
echo "BLOQUE 6 $(date -u +%H:%M:%S)"
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f argocd/00-namespace.yaml
kubectl apply -f monitoring/00-namespace.yaml
kubectl apply -f k8s/05-garage.yaml -l '!app.kubernetes.io/name'
kubectl get namespaces agroeco argocd monitoring garage \
  -L pod-security.kubernetes.io/enforce,pod-security.kubernetes.io/warn
echo "FIN BLOQUE 6 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- 4 `namespace/... created`.
- En la tabla, `agroeco` y `argocd` con `restricted restricted`,
  `monitoring` con `privileged restricted` y `garage` sin etiquetas de
  Pod Security.

---

## Bloque 7 · Garage: Secret, despliegue, layout, bucket y clave

**Terminal: Ubuntu 1.**

```bash
echo "BLOQUE 7 $(date -u +%H:%M:%S)"
# 7.1 Secret RPC: 32 bytes aleatorios en hexadecimal, sin mostrarse
RPC_SECRET=$(openssl rand -hex 32)
kubectl create secret generic garage-rpc -n garage \
  --from-literal=rpc-secret="$RPC_SECRET"
unset RPC_SECRET

# 7.2 Despliegue (ConfigMap, Service y StatefulSet)
kubectl apply -f k8s/05-garage.yaml
kubectl rollout status statefulset/garage -n garage --timeout=300s

# 7.3 Layout de un solo nodo: zona dc1, capacidad 1G, versión 1 (clúster nuevo).
# "node id -q" lee el ID de metadata_dir e imprime "<id>@<rpc_public_addr>"
# sin las instrucciones de uso; cut se queda con el ID (64 hex).
NODO=$(kubectl exec -n garage garage-0 -- /garage node id -q | cut -d@ -f1)
if [[ "$NODO" =~ ^[0-9a-f]{64}$ ]]; then
  echo "ID del nodo: ${NODO:0:16}… (64 caracteres)"
  kubectl exec -n garage garage-0 -- /garage layout assign -z dc1 -c 1G "$NODO"
  kubectl exec -n garage garage-0 -- /garage layout apply --version 1
else
  echo "ERROR: ID de nodo inesperado; revisa 'garage status'"
fi
kubectl exec -n garage garage-0 -- /garage status
unset NODO

# 7.4 Bucket
kubectl exec -n garage garage-0 -- /garage bucket create agroeco-backups
echo "FIN BLOQUE 7 $(date -u +%H:%M:%S)"
```

El ID del nodo no es secreto, pero tampoco hace falta verlo entero.

**Salida esperada:**
- `secret/garage-rpc created`.
- `statefulset rolling update complete` o `partitioned roll out complete`,
  según la versión de kubectl.
- `ID del nodo: …… (64 caracteres)`.
- `layout assign`: `Role changes are staged but not yet committed.`
- `layout apply`: `New cluster layout with updated role assignment has been applied in cluster.`
- `garage status`: en `==== HEALTHY NODES ====`, el nodo `garage-0` en la
  zona `dc1` con 1 GB de capacidad.
- `bucket create` imprime `==== BUCKET INFORMATION ====`, con
  `Global alias: agroeco-backups`.

La clave S3 se crea en el bloque 8, en la misma terminal en la que se crea
su Secret.

---

## Bloque 8 · Clave S3, Secret `agroeco-s3-creds` y ObjectStore

**Terminal: Ubuntu 1.**

**Cómo se extrae la clave sin mostrarla:**
- La salida de `garage key create` va entera a la variable `SALIDA` y no
  llega a la pantalla. En Garage v2.5.0, la orden imprime una tabla
  `==== ACCESS KEY INFORMATION ====` con las filas `Key ID:` y
  `Secret key:`, con el valor en la última columna.
- El ID se extrae con su forma exacta (`GK` + 24 hex) y el secreto con la
  última palabra de su fila.
- Antes de crear el Secret, los dos se validan contra su formato exacto:
  24 hex en el ID y 64 hex en el secreto, que es como los genera Garage
  (`src/model/key_table.rs`). Si cambiara la salida, el bloque no crea nada
  y no imprime los valores.
- En pantalla solo se escriben sus longitudes.
- `kubectl create secret --from-literal` recibe las variables, y `unset`
  las borra.

```bash
echo "BLOQUE 8 $(date -u +%H:%M:%S)"
SALIDA=$(kubectl exec -n garage garage-0 -- /garage key create agroeco-pg-backup)
KEY_ID=$(printf '%s\n' "$SALIDA" | grep -m1 -oE '\bGK[0-9a-f]{24}\b')
KEY_SECRET=$(printf '%s\n' "$SALIDA" | awk '/Secret key:/ {print $NF}')
echo "Longitudes: ID=${#KEY_ID} secreto=${#KEY_SECRET}"     # esperado: ID=26 secreto=64

# Solo si los dos tienen el formato exacto; si no, no se crea nada
if [[ "$KEY_ID" =~ ^GK[0-9a-f]{24}$ && "$KEY_SECRET" =~ ^[0-9a-f]{64}$ ]]; then
  kubectl create secret generic agroeco-s3-creds -n agroeco \
    --from-literal=ACCESS_KEY_ID="$KEY_ID" \
    --from-literal=ACCESS_SECRET_KEY="$KEY_SECRET"
else
  echo "ERROR: formato de la clave inesperado; revisa 'garage key list'"
fi
unset SALIDA KEY_ID KEY_SECRET

# Permisos de lectura y escritura en el bucket, sin permiso de propietario
kubectl exec -n garage garage-0 -- /garage bucket allow --read --write agroeco-backups --key agroeco-pg-backup

# Comprobación sin ver los valores: describe muestra solo los bytes de cada clave
kubectl describe secret agroeco-s3-creds -n agroeco | sed -n '/^Data/,$p'
# Permisos de la clave en el bucket: solo las banderas y el nombre, sin el ID
kubectl exec -n garage garage-0 -- /garage bucket info agroeco-backups \
  | sed -n '/KEYS FOR THIS BUCKET/,$p' | grep agroeco-pg-backup | awk '{print $1, $NF}'

# ObjectStore del plugin
kubectl apply -f k8s/06-objectstore.yaml
kubectl get objectstore -n agroeco
echo "FIN BLOQUE 8 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `Longitudes: ID=26 secreto=64` y `secret/agroeco-s3-creds created`.
- En `Data`: `ACCESS_KEY_ID: 26 bytes` y `ACCESS_SECRET_KEY: 64 bytes`.
- `RW agroeco-pg-backup`: lectura y escritura, sin la `O` de propietario.
- `objectstore.barmancloud.cnpg.io/agroeco-backup-store created`.

---

## Bloque 9 · Secret `agroeco-db-app` y Cluster de PostgreSQL

**Terminal: Ubuntu 1.** La contraseña del usuario `agroeco` es nueva y
aleatoria. Ninguna persona necesita conocerla: el ETL la lee del Secret, y
la administración se hace con `kubectl cnpg psql` dentro del pod.

```bash
echo "BLOQUE 9 $(date -u +%H:%M:%S)"
DB_PASS=$(openssl rand -hex 24)
kubectl create secret generic agroeco-db-app -n agroeco \
  --type=kubernetes.io/basic-auth \
  --from-literal=username=agroeco \
  --from-literal=password="$DB_PASS"
unset DB_PASS
kubectl describe secret agroeco-db-app -n agroeco | sed -n '/^Data/,$p'

kubectl apply -f k8s/04-postgres-cluster.yaml
# Espera a las 2 instancias y al archivado continuo de WAL
kubectl wait --for=condition=Ready cluster/agroeco-pg -n agroeco --timeout=15m
kubectl wait --for=jsonpath='{.status.readyInstances}'=2 cluster/agroeco-pg -n agroeco --timeout=5m
kubectl wait --for=condition=ContinuousArchiving cluster/agroeco-pg -n agroeco --timeout=5m

kubectl get cluster agroeco-pg -n agroeco
kubectl get pods -n agroeco -o wide
kubectl get secret -n agroeco agroeco-pg-ca agroeco-pg-server agroeco-pg-replication
echo "FIN BLOQUE 9 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- En `Data`: `password: 48 bytes` y `username: 7 bytes`.
- `cluster.postgresql.cnpg.io/agroeco-pg condition met`, tres veces.
- `Cluster in healthy state`, con `INSTANCES 2` y `READY 2`.
- `agroeco-pg-1` y `agroeco-pg-2` en `2/2 Running` (postgres y el sidecar
  del plugin) y en **nodos distintos**.
- Los 3 Secrets generados por el operador: la CA nueva y los dos
  certificados.

---

## Bloque 10 · kube-prometheus-stack, PodMonitor y dashboard

**Terminal: Ubuntu 1.** Va **antes** que ArgoCD: la Application genera una
`PrometheusRule`, y sin el CRD (que instala este chart) la sincronización
entera fallaría.

```bash
echo "BLOQUE 10 $(date -u +%H:%M:%S)"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
helm repo update prometheus-community
helm upgrade --install kps prometheus-community/kube-prometheus-stack \
  --version 93.11.1 -n monitoring -f monitoring/values-kps.yaml --wait --timeout 10m
kubectl get crd | grep -c monitoring.coreos.com
kubectl wait --for=condition=Ready pod --all -n monitoring --timeout=300s
kubectl get pods -n monitoring
kubectl get pvc -n monitoring

kubectl apply -f k8s/09-podmonitor-cnpg.yaml
kubectl apply --server-side -f monitoring/dashboard-cnpg.yaml
echo "FIN BLOQUE 10 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `STATUS: deployed`, con el aviso `warn` de PodSecurity solo para
  node-exporter.
- `10` CRD de `monitoring.coreos.com`.
- 8 pods `Running`: `alertmanager` 2/2, `grafana` 3/3,
  `kube-state-metrics`, `operator`, 3 `node-exporter` y `prometheus` 2/2.
- PVC de 2Gi, `Bound`.
- `podmonitor.monitoring.coreos.com/agroeco-pg created` y
  `configmap/dashboard-cnpg serverside-applied`.

---

## Bloque 11 · ArgoCD: instalación, AppProject, Application y contraseña de admin

**Terminal: Ubuntu 1**, y Ubuntu 2 para el port-forward.

```bash
echo "BLOQUE 11 $(date -u +%H:%M:%S)"
helm repo add argo https://argoproj.github.io/argo-helm --force-update
helm repo update argo
helm install argocd argo/argo-cd --version 10.19.1 -n argocd \
  -f argocd/values-argocd.yaml --wait --timeout 10m
kubectl get pods -n argocd

kubectl apply -f argocd/01-proyecto-agroeco.yaml
kubectl apply -f argocd/02-app-agroeco-etl.yaml
kubectl wait --for=jsonpath='{.status.sync.status}'=Synced application/agroeco-etl -n argocd --timeout=300s
kubectl wait --for=jsonpath='{.status.health.status}'=Healthy application/agroeco-etl -n argocd --timeout=300s
kubectl get application agroeco-etl -n argocd \
  -o jsonpath='{.status.sync.revision} {.status.sync.status} {.status.health.status}{"\n"}'
kubectl get configmap,cronjob,prometheusrule -n agroeco -l app.kubernetes.io/instance=agroeco-etl
```

**Salida esperada:**
- `STATUS: deployed`, sin avisos de PodSecurity.
- Los pods de ArgoCD en `Running`: `application-controller`,
  `repo-server`, `server` y `redis`, sin Dex ni ApplicationSet.
- `<SHA de main> Synced Healthy`.
- `configmap/agroeco-etl`, `cronjob/agroeco-etl-mensual` y
  `prometheusrule/agroeco-etl`.
- No aparece ningún Job, porque la carga inicial está desactivada en la
  Application.

**Contraseña de admin.**

**Ubuntu 2:**

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

**Ubuntu 1:**

```bash
curl -sk https://localhost:8080/healthz; echo     # esperado: ok
# 1. Contraseña inicial al portapapeles: entra en https://localhost:8080 como admin
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d | clip.exe
#    En User Info > Update Password, pega la inicial en "Current password".
# 2. Contraseña nueva, aleatoria, al portapapeles: guárdala primero en el
#    gestor de contraseñas y después pégala en "New password" y "Confirm".
openssl rand -base64 24 | tr -d '\n' | clip.exe
# 3. Comprobación del cambio y borrado del Secret inicial
kubectl get secret argocd-secret -n argocd -o jsonpath='{.data.admin\.passwordMtime}' | base64 -d; echo
kubectl delete secret argocd-initial-admin-secret -n argocd
kubectl get secret argocd-initial-admin-secret -n argocd
# 4. Vacía el portapapeles
printf '' | clip.exe
echo "FIN BLOQUE 11 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `admin.passwordMtime` con la hora del cambio (UTC).
- `secret "argocd-initial-admin-secret" deleted`, seguido de
  `Error from server (NotFound)`.
- Vuelve a iniciar sesión con la contraseña nueva, desde el gestor, para
  confirmarla.

Cierra el port-forward de Ubuntu 2.

---

## Bloque 12 · Carga inicial de datos

**Terminal: Ubuntu 1.** La Application tiene `cargaInicial.enabled: false`.
La primera carga es una acción puntual: un Job creado a partir del CronJob
que gestiona ArgoCD, con la misma plantilla que las ejecuciones mensuales.
Ese Job lo crea Kubernetes y no ArgoCD, así que el AppProject no lo bloquea
y la Application no lo borra.

```bash
echo "BLOQUE 12 $(date -u +%H:%M:%S)"
kubectl create job --from=cronjob/agroeco-etl-mensual etl-carga-inicial -n agroeco
kubectl wait --for=condition=complete job/etl-carga-inicial -n agroeco --timeout=15m
kubectl get job etl-carga-inicial -n agroeco
kubectl logs -n agroeco job/etl-carga-inicial | head -1
kubectl logs -n agroeco job/etl-carga-inicial | grep -E 'Carga en PostgreSQL|Pipeline terminado|Resumen'
kubectl get pod -n agroeco -l job-name=etl-carga-inicial -o jsonpath='{.items[0].status.containerStatuses[0].imageID}{"\n"}'
echo "FIN BLOQUE 12 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `job.batch/etl-carga-inicial condition met`, `Complete` y `1/1`.
- La primera línea del log es `agroeco-etl 0.2.1`, y después aparecen
  `>>> 3. Carga en PostgreSQL` y `>>> Pipeline terminado correctamente`.
- El resumen da las 6 tablas con 28, 17, 13529, 620, 2015 y 1395 filas.
- El `imageID` es `ghcr.io/samanaya11/agroeco-etl@sha256:5c06ff2e…55338`.
  Es el digest de `values-prod.yaml`, descargado de nuevo de ghcr.io: la
  duración del Job incluye esa primera descarga.

**La base de datos vacía no es un problema.**
- **Es el mismo Job que la carga inicial.** El Job creado desde el CronJob
  y la carga inicial del chart usan la plantilla única
  `agroeco-etl.jobSpec` de `_helpers.tpl`: la misma imagen, el mismo
  ConfigMap, las mismas credenciales y ningún argumento. El hook `job.yaml`
  solo añade el TTL y las anotaciones de Helm.
- **El esquema lo crea el propio ETL en cada carga.** `carga_sql.cargar()`
  ejecuta `sql/01_esquema.sql` (`DROP … IF EXISTS` y
  `CREATE TABLE`/`CREATE VIEW`) en la misma transacción que los `INSERT`.
- **Tiene permiso para hacerlo.** El usuario `agroeco` es el propietario de
  la base de datos (`bootstrap.initdb.owner`).

**TLS `verify-full` con la CA nueva.**
- El pod del ETL monta `ca.crt` del Secret `agroeco-pg-ca` que acaba de
  generar CloudNativePG.
- Con `PGSSLMODE=verify-full`, libpq aborta la conexión si el certificado
  del servidor no lo firma esa CA o si su nombre no es `agroeco-pg-rw`.
  Por eso un Job `Complete` ya prueba la verificación.
- El Cluster tiene `log_connections: "on"`
  ([`k8s/04-postgres-cluster.yaml`](../k8s/04-postgres-cluster.yaml)), así
  que la primaria registra cada conexión aceptada con su cifrado. Para
  confirmarlo:

```bash
P=$(kubectl get cluster agroeco-pg -n agroeco -o jsonpath='{.status.currentPrimary}')
kubectl logs -n agroeco "$P" -c postgres | grep 'connection authorized: user=agroeco' | tail -1 | grep -o 'SSL enabled[^"]*'
kubectl get configmap agroeco-etl -n agroeco -o jsonpath='{.data.PGSSLMODE}{"\n"}'
```

**Salida esperada:** `SSL enabled (protocol=TLSv1.3, …)` y `verify-full`.

---

## Bloque 13 · Backup bajo demanda y archivado de WAL

**Terminal: Ubuntu 1.**

```bash
echo "BLOQUE 13 $(date -u +%H:%M:%S)"
P=$(kubectl get cluster agroeco-pg -n agroeco -o jsonpath='{.status.currentPrimary}')
# Fuerza el cierre del segmento de WAL actual (la carga acaba de escribir)
# y espera, hasta 2 min, a que el archivador lo suba a Garage
SEG=$(kubectl exec -n agroeco "$P" -c postgres -- psql -d agroeco -Atc "SELECT pg_walfile_name(pg_switch_wal())")
echo "Segmento cerrado: $SEG"
for i in $(seq 1 24); do
  ULT=$(kubectl exec -n agroeco "$P" -c postgres -- psql -d agroeco -Atc "SELECT last_archived_wal FROM pg_stat_archiver")
  if [[ "$ULT" == "$SEG" || "$ULT" > "$SEG" ]]; then echo "Archivado: $ULT"; break; fi
  sleep 5
done
kubectl exec -n agroeco "$P" -c postgres -- psql -d agroeco -AtF ' ' \
  -c "SELECT 'archivados', archived_count, 'fallidos', failed_count, 'último', last_archived_wal FROM pg_stat_archiver"
kubectl get cluster agroeco-pg -n agroeco \
  -o jsonpath='{range .status.conditions[?(@.type=="ContinuousArchiving")]}{.type}={.status}{"\n"}{end}'
unset SEG ULT

kubectl apply -f k8s/07-backup.yaml
kubectl wait --for=jsonpath='{.status.phase}'=completed backup/agroeco-pg-backup-manual -n agroeco --timeout=10m
kubectl get backup agroeco-pg-backup-manual -n agroeco \
  -o jsonpath='{"Instancia: "}{.status.instanceID.podName}{"\nID: "}{.status.backupId}{"\nInicio: "}{.status.startedAt}{"\nFin: "}{.status.stoppedAt}{"\n"}'

kubectl apply -f k8s/utilidades/s3-listado.yaml
kubectl wait -n agroeco --for=jsonpath='{.status.phase}'=Succeeded pod/s3-listado --timeout=120s
kubectl logs -n agroeco s3-listado | grep -E 'base/|wals/|Total' | tail -8
kubectl delete -f k8s/utilidades/s3-listado.yaml
echo "FIN BLOQUE 13 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `Segmento cerrado: 0000000100000000000000XX` y, en unos segundos,
  `Archivado:` con ese mismo segmento o uno posterior.
- `archivados` mayor que 0, `fallidos 0`, y `ContinuousArchiving=True`.
- `backup.postgresql.cnpg.io/agroeco-pg-backup-manual condition met`.
- La instancia es la réplica (`prefer-standby`), con un ID nuevo.
- En el bucket, `agroeco-pg/base/<ID>/` (`data.tar.gz` y `backup.info`) y
  WAL `.gz` en `agroeco-pg/wals/`.

---

## Bloque 14 · Verificación final

**Terminal: Ubuntu 1**, y Ubuntu 2 para los port-forward.

**Ubuntu 2** (dos port-forward en la misma terminal; Ctrl+C cierra los dos):

```bash
kubectl port-forward -n monitoring svc/kps-prometheus 9090:9090 &
kubectl port-forward -n monitoring svc/kps-alertmanager 9093:9093
```

**Ubuntu 1:**

```bash
echo "BLOQUE 14 $(date -u +%H:%M:%S)"
# Objetivos de Prometheus
curl -s 'http://localhost:9090/api/v1/targets?state=active' | python3 -c '
import json, sys
t = json.load(sys.stdin)["data"]["activeTargets"]
print(len(t), "objetivos;", sum(x["health"] != "up" for x in t), "caídos")'
# Métricas de PostgreSQL (PodMonitor)
curl -s 'http://localhost:9090/api/v1/query' --data-urlencode 'query=cnpg_collector_up' | python3 -c '
import json, sys
for r in json.load(sys.stdin)["data"]["result"]:
    print(r["metric"]["pod"], r["value"][1])'
# Regla del ETL cargada desde el chart (la despliega ArgoCD)
curl -s 'http://localhost:9090/api/v1/rules' | python3 -c '
import json, sys
for g in json.load(sys.stdin)["data"]["groups"]:
    for r in g["rules"]:
        if r["name"] == "AgroecoEtlJobFallido":
            print(r["name"], r["state"], r["health"], r["lastEvaluation"])'
# Ninguna alerta del ETL activa en Alertmanager
curl -s -G 'http://localhost:9093/api/v2/alerts' \
  --data-urlencode 'filter=alertname="AgroecoEtlJobFallido"' | python3 -c 'import json, sys; print(len(json.load(sys.stdin)), "alertas del ETL")'
# Ningún pod fuera de Running o Completed
kubectl get pods -A --no-headers | awk '$4 != "Running" && $4 != "Completed"'
echo "FIN BLOQUE 14 $(date -u +%H:%M:%S)"
```

**Salida esperada:**
- `23 objetivos; 0 caídos`.
- `agroeco-pg-1 1` y `agroeco-pg-2 1`.
- `AgroecoEtlJobFallido inactive ok <hora>` y `0 alertas del ETL`.
- El último comando no devuelve ninguna línea.

**Grafana** (opcional): `kubectl port-forward -n monitoring svc/kps-grafana 3000:80`
en Ubuntu 2. La contraseña de `admin` va al portapapeles con
`kubectl get secret -n monitoring kps-grafana -o jsonpath='{.data.admin-password}' | base64 -d | clip.exe`.
El dashboard CloudNativePG debe mostrar `agroeco` / `agroeco-pg` con datos.

---

## Bloque 15 · Comparación

**Terminal: Ubuntu 1**, con el port-forward 9090 de Ubuntu 2 abierto.
Define otra vez `SQL` y `foto` (bloque 0) si es una terminal nueva.

```bash
echo "BLOQUE 15 $(date -u +%H:%M:%S)"
foto despues
for x in filas argocd pods helm prometheus backups; do
  echo "===== $x"; diff ~/exp-g/antes-$x.txt ~/exp-g/despues-$x.txt && echo "(igual)"
done
echo "FIN BLOQUE 15 $(date -u +%H:%M:%S)"
```

**Resultado esperado:**

| Dato | Esperado |
|------|----------|
| Filas | `(igual)`, salvo que Eurostat haya publicado datos nuevos |
| ArgoCD | `Synced Healthy`. El SHA solo cambia si hubo commits en `main` entre la foto y la reconstrucción |
| Pods | Las mismas cuentas por namespace. En `agroeco` cambian los pods `Completed`: antes los de `agroeco-etl-manual-tls` y `etl-promocion-021`, ahora el de `etl-carga-inicial` |
| Helm | Las mismas releases, con las mismas versiones de chart y de aplicación; cambian las fechas de despliegue |
| Prometheus | `23 objetivos; 0 caídos`, con las mismas cuentas por job |
| Backups | Un backup `completed` con un **ID nuevo**: el anterior se perdió con el bucket, que estaba dentro del clúster |

---

## Tiempos por bloque

| Bloque | Inicio (UTC) | Fin (UTC) | Duración | Incidencias |
|--------|--------------|-----------|----------|-------------|
| 0 · Foto del estado | | | | |
| 1 · Borrar el clúster | | | | |
| 2 · Crear el clúster | | | | |
| 3 · cert-manager | | | | |
| 4 · CloudNativePG | | | | |
| 5 · Barman Cloud Plugin | | | | |
| 6 · Namespaces | | | | |
| 7 · Garage | | | | |
| 8 · Clave S3 y ObjectStore | | | | |
| 9 · Cluster de PostgreSQL | | | | |
| 10 · kube-prometheus-stack | | | | |
| 11 · ArgoCD | | | | |
| 12 · Carga inicial | | | | |
| 13 · Backup y WAL | | | | |
| 14 · Verificación final | | | | |
| 15 · Comparación | | | | |
| **Total (bloques 2-14)** | | | | |
