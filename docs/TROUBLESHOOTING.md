# Registro de incidencias

Incidencias encontradas durante la construcción del proyecto, en el orden en
que ocurrieron. Cada entrada recoge el síntoma observado, la causa real, la
solución aplicada y cómo evitar que se repita.

## Índice

| Nº | Fase | Incidencia |
|----|------|------------|
| [TS-01](#ts-01--un-job-parece-haber-desaparecido-falso-positivo-de-la-terminal) | 1 | Un Job parece haber desaparecido (falso positivo de la terminal) |
| [TS-02](#ts-02--nombres-de-captura-que-no-coinciden-con-el-leeme) | 2 | Nombres de captura que no coinciden con el LEEME |
| [TS-03](#ts-03--no-hay-switchover-al-activar-el-barman-cloud-plugin-pese-a-primaryupdatemethod-switchover) | 2 | No hay switchover al activar el Barman Cloud Plugin, pese a `primaryUpdateMethod: switchover` |
| [TS-04](#ts-04--kubectl-apply-responde-configured-sin-haber-cambios) | 2 | `kubectl apply` responde `configured` sin haber cambios |
| [TS-05](#ts-05--falta-00000002history-en-el-archivo-de-wal) | 2 | Falta `00000002.history` en el archivo de WAL |
| [TS-06](#ts-06--el-nivel-debug-de-dev-no-muestra-nada-más-que-prod) | 3 | El nivel DEBUG de dev no muestra nada más que prod |
| [TS-07](#ts-07--aviso-de-last-applied-configuration-en-la-primera-sincronización-de-argocd) | 4 | Aviso de `last-applied-configuration` en la primera sincronización de ArgoCD |
| [TS-08](#ts-08--la-interfaz-de-argocd-da-request-has-been-terminated-al-iniciar-sesión) | 4 | La interfaz de ArgoCD da «Request has been terminated» al iniciar sesión |
| [TS-09](#ts-09--el-ci-falla-en-la-imagen-publicada-es-la-probada) | 4 | El CI falla en «La imagen publicada es la probada» |

---

## TS-01 · Un Job parece haber desaparecido (falso positivo de la terminal)

- **Fase:** 1 – Contenedor y Kubernetes básico (durante el Experimento B).
- **Síntoma:** `kubectl -n agroeco get jobs` mostró solo `agroeco-etl-manual`.
  El Job `etl-prueba-cron`, creado horas antes con
  `kubectl create job --from=cronjob/agroeco-etl-mensual`, no aparecía en la lista.
- **Causa:** no había ningún problema en el clúster. El Job seguía existiendo
  en `Complete 1/1`. La línea se perdió en la **visualización de la terminal
  de Ubuntu**, que ya había mezclado o dejado de mostrar líneas en otras
  ocasiones.
- **Cómo se comprobó:**
  1. Se descartaron las causas posibles en el clúster. La plantilla del
     CronJob no tiene `ttlSecondsAfterFinished`. El límite de historial
     (`successfulJobsHistoryLimit: 3`) no se alcanzaba con un solo Job. En el
     historial de la shell solo había borrados de `agroeco-etl-manual`, por
     nombre y por su etiqueta `batch.kubernetes.io/job-name`.
  2. `kubectl get jobs -A | grep -i prueba` mostró `etl-prueba-cron` en
     `Complete 1/1`, con 15 h de antigüedad, y su pod `etl-prueba-cron-2p8rh`
     seguía en `kubectl get pods`.
  3. `docker inspect -f '{{.State.StartedAt}}' k3d-agroeco-server-0` confirmó
     que el servidor no se había reiniciado.
  4. Un Job de control, `etl-prueba-cron-2`, creado de la misma forma, tenía
     como dueño `CronJob/agroeco-etl-mensual` y TTL vacío, que es lo esperado.
- **Solución:** ninguna en el clúster. Se cerró como falso positivo.
- **Prevención:** antes de concluir que un objeto ha desaparecido, se
  comprueba con una segunda consulta que no dependa de la presentación en
  tabla:
  - `kubectl get <tipo> <nombre>`: búsqueda directa, que falla con `NotFound` si no existe.
  - `kubectl get <tipo> -o name`: una línea por objeto, sin columnas.
  - `kubectl get <tipo> --no-headers | wc -l`: un recuento que se puede contrastar.

  Las salidas largas se guardan además en un archivo con
  `| tee salida.txt`, para revisarlas fuera de la terminal.
- **Frase para entrevista:** «Un Job parecía haber desaparecido del clúster.
  Antes de tocar nada descarté las causas reales: TTL, límite de historial,
  borrados en el historial de la shell y reinicio del nodo. Al final, una
  búsqueda directa por nombre mostró que el Job seguía allí y completado.
  Era la terminal, que había perdido la línea. Ahora no doy un objeto por
  desaparecido sin una segunda consulta que no dependa de la tabla, como un
  `get` por nombre o un recuento.»

---

## TS-02 · Nombres de captura que no coinciden con el LEEME

- **Fase:** 2 – PostgreSQL con CloudNativePG (al preparar el commit de cierre).
- **Síntoma:** `git status` mostró `docs/capturas/gitleaks_fase1.png`, una
  captura que ya debía llamarse `10_gitleaks_fase1.png`. Al revisar la
  carpeta aparecieron otros tres nombres distintos de los del LEEME, ya
  subidos en el commit de la Fase 1: `03b_docker_build.png`,
  `04a_docker_run_carga.png.png` y `04b_docker_run_consultas.png.png`.
- **Causa:** las capturas se guardan y renombran desde Windows. El Explorador
  oculta las extensiones conocidas, así que al escribir `….png` se añadió una
  segunda extensión. El renombrado de la captura 10 no se llegó a guardar.
- **Solución:** se renombraron con `git mv`, que conserva el historial, a
  `10_gitleaks_fase1.png`, `03_docker_build.png`,
  `04a_docker_run_carga.png` y `04b_docker_run_consultas.png`.
- **Prevención:** antes de cada commit se compara la carpeta con la lista del
  LEEME (`ls docs/capturas`). En el Explorador de Windows se activa
  *Ver → Mostrar → Extensiones de nombre de archivo*.
- **Frase para entrevista:** «Al preparar un commit vi que cuatro capturas
  no seguían la convención de nombres, y tres ya estaban subidas con doble
  extensión porque el Explorador de Windows oculta las extensiones. Las
  renombré con `git mv` para conservar el historial y añadí una comprobación
  antes de cada commit: comparar la carpeta con la lista documentada. Un
  error pequeño, pero en un proyecto que se enseña la documentación tiene
  que coincidir con lo que hay.»

---

## TS-03 · No hay switchover al activar el Barman Cloud Plugin, pese a `primaryUpdateMethod: switchover`

- **Fase:** 2 – PostgreSQL con CloudNativePG (bloque de backup, al conectar
  el Cluster con el plugin).
- **Síntoma:** se aplicaron a la vez `spec.plugins` (Barman Cloud Plugin con
  `isWALArchiver: true`) y `primaryUpdateMethod: switchover`. Las dos
  instancias se recrearon con el sidecar (`2/2 Running`), pero la primaria
  siguió siendo `agroeco-pg-2`, y `currentPrimaryTimestamp` no cambió
  (2026-11-22T19:31:17Z, el failover del Experimento C). Los únicos eventos
  del Cluster fueron `UpgradingInstance agroeco-pg-1` (20:35:21Z) y
  `UpgradingInstance agroeco-pg-2` (20:36:05Z), sin ningún evento `Switchover`.
- **Causa:** es el comportamiento previsto de CloudNativePG 1.30, no un
  fallo. En `internal/controller/cluster_upgrade.go` (rama `release-1.30`),
  antes de un switchover la función `archiverSidecarMissingOnPrimary`
  comprueba si hay un plugin archivador de WAL activo y si a la primaria le
  falta el sidecar que ese plugin inyecta. En ese caso, el switchover se
  bloquearía sin salida: para degradarse a réplica, la primaria tiene que
  archivar antes todos sus WAL pendientes (`ArchiveAllReadyWALs`), y para
  eso necesita el sidecar que todavía no tiene. El operador evita ese
  bloqueo (incidencia
  [cloudnative-pg#10981](https://github.com/cloudnative-pg/cloudnative-pg/issues/10981))
  recreando la primaria en el sitio (`recreatePrimaryInPlace`). La primaria
  vuelve como primaria y con el sidecar, sin degradación ni `pg_rewind`.
  Esto pasa solo la primera vez que se activa el plugin. A partir de ahí
  las dos instancias ya tienen el sidecar, y `switchover` se aplica con
  normalidad.
- **Cómo se comprobó:**
  1. Lectura del código de `updatePrimaryPod` en la versión 1.30: la rama
     del plugin archivador se evalúa antes de elegir la réplica a promover.
  2. Logs del operador (`kubectl logs -n cnpg-system
     deploy/cnpg-cloudnative-pg --since-time=2026-11-23T20:34:00Z`, filtrados
     con `grep`). Aparecen, en este orden:
     - `20:35:21.211Z` `"Recreating instance pod"`, pod `agroeco-pg-1` (la réplica).
     - `20:36:05.975Z` `"Primary is missing the WAL-archiver sidecar;
       recreating it in place instead of switching over"`.
     - `20:36:05.989Z` `"Recreating instance pod"`, pod `agroeco-pg-2` (la primaria).

     No hay ninguna línea `we'll trigger a switchover`.
- **Efecto secundario: 6 fallos de archivado del WAL 0011.** Después del
  primer backup, `pg_stat_archiver` en la primaria mostraba
  `failed_count = 6`, `last_failed_wal = 000000020000000000000011` y
  `last_failed_time = 20:36:10.858Z`. Los tiempos muestran que el origen
  fue la **primaria antigua**, no el pod nuevo:
  - 20:36:05.989Z: el operador borra el pod de la primaria, que todavía
    no tiene sidecar.
  - 20:36:10.858Z: último intento fallido de archivar el 0011. Ocurrió
    durante el apagado: el Cluster ya tenía el plugin como archivador,
    pero en ese pod no había sidecar que lo ejecutara.
  - 20:36:14Z, 20:36:35Z y 20:36:36Z: en el pod nuevo arrancan
    `bootstrap-controller`, el sidecar `plugin-barman-cloud` (como *native
    sidecar*) y `postgres`. El sidecar arranca **antes** que PostgreSQL, así
    que en el pod nuevo no hay carrera.
  - 20:36:38Z: el sidecar archiva el 0011 en 0,68 s, en el primer intento.
    Los logs de `postgres` y del sidecar del pod nuevo no muestran ningún
    error.

  Es la misma situación que evita el operador al no hacer switchover: una
  primaria con el plugin configurado y sin sidecar no puede archivar. Los
  logs del pod antiguo se perdieron al recrearlo. El contador sobrevive
  porque las estadísticas se guardan al apagar de forma ordenada
  (`stats_reset` es de las 13:20:57, anterior al cambio). Los fallos fueron
  **inocuos**: PostgreSQL no borra ningún segmento hasta archivarlo, así
  que el 0011 se quedó marcado como pendiente (`.ready`) en el volumen y
  el pod nuevo lo envió al arrancar. El archivo de WAL en Garage es
  continuo desde el 0011.
- **Consecuencia:** al recrearse, la primaria dejó el clúster sin escritura
  durante unos segundos, lo mismo que habría pasado con `restart`.
  Activar el archivado de WAL por primera vez supone, por tanto, un corte
  breve de escritura, que conviene planificar.
- **Solución:** ninguna. El clúster quedó sano, con
  `ContinuousArchiving=True` y el primer WAL en Garage. Se mantiene
  `primaryUpdateMethod: switchover` para las siguientes actualizaciones.
- **Prevención:** antes de prever el comportamiento de un cambio que
  reinicia instancias, se revisa en la documentación y en el código de la
  versión exacta del operador qué hace con la primaria. Activar un plugin
  archivador de WAL se programa en una ventana de mantenimiento, porque la
  primaria se reinicia sin switchover.
- **Frase para entrevista:** «Activé el archivado de WAL con el Barman Cloud
  Plugin y, aunque tenía configurado el switchover, el operador reinició la
  primaria en su sitio. Fui al código de CloudNativePG 1.30 y vi que es a
  propósito: una primaria sin el sidecar no puede archivar sus WAL
  pendientes, que es justo lo que necesita para degradarse a réplica, así
  que el switchover se quedaría bloqueado. Desde entonces compruebo en la
  versión concreta del operador qué hace con la primaria antes de aplicar
  un cambio, y programo la activación del archivado en una ventana de
  mantenimiento.»

---

## TS-04 · `kubectl apply` responde `configured` sin haber cambios

- **Fase:** 2 – PostgreSQL con CloudNativePG (bloque de backup, prueba de
  restauración).
- **Síntoma:** al repetir `kubectl apply -f k8s/08-postgres-restore.yaml`
  justo después de crear el Cluster, la respuesta fue
  `cluster.postgresql.cnpg.io/agroeco-pg-restore configured`, y no
  `unchanged`. Un `--dry-run=server` posterior dijo lo mismo.
- **Causa:** el `apply` por defecto se calcula en el cliente. Para los
  recursos personalizados (CRD) usa un *merge patch* JSON, que trata cada
  lista como un bloque. Al crear el Cluster, el servidor añadió valores por
  defecto dentro de la lista `externalClusters`: `plugin.enabled: true` y
  `plugin.isWALArchiver: false`. La lista viva ya no coincidía con la del
  archivo, así que kubectl envió la lista entera y respondió `configured`.
  El servidor volvió a añadir los mismos valores y el objeto quedó idéntico.
- **Cómo se comprobó:**
  - `metadata.generation` seguía en `1`: la especificación no había cambiado.
  - `.spec.externalClusters[0].plugin` en el objeto vivo:
    `{"enabled":true,"isWALArchiver":false,"name":"barman-cloud.cloudnative-pg.io","parameters":{…}}`,
    con dos campos que no están en el archivo.
  - `kubectl diff -f k8s/08-postgres-restore.yaml` no mostró diferencias y
    salió con código 0. `diff` compara después de que el servidor aplique
    los valores por defecto.
- **Solución:** ninguna. Fue inocuo: no hubo cambios ni reinicios. La
  recreación del pod que coincidió en el tiempo era el comportamiento
  previsto del plugin (ver README, *Backup y restauración*).
- **Prevención:** para saber si un `apply` cambia algo de verdad, se mira
  `kubectl diff` antes de aplicar, y `metadata.generation` después, en lugar
  del mensaje de `apply`. En la Fase 4 se tendrá en cuenta con ArgoCD:
  hay que comprobar que estos valores por defecto no hacen aparecer el
  recurso como `OutOfSync` y, si lo hacen, compararlo en el
  servidor (*server-side diff*).
- **Frase para entrevista:** «Al repetir un `kubectl apply` sobre un
  recurso de CloudNativePG, la respuesta fue `configured` sin que yo hubiera
  cambiado nada. Comprobé que la `generation` seguía en 1 y que
  `kubectl diff` salía vacío. La causa era que el servidor añade valores por
  defecto dentro de una lista y el `apply` en el cliente compara las listas
  enteras. Desde entonces, para saber si algo ha cambiado miro `diff` y
  `generation`, no el mensaje de `apply`.»

---

## TS-05 · Falta `00000002.history` en el archivo de WAL

- **Fase:** 2 – PostgreSQL con CloudNativePG (bloque de backup, prueba de
  restauración).
- **Síntoma:** en el clúster restaurado, `00000003.history` tenía una sola
  línea, `2  0/14000000  no recovery target specified`. Faltaba la anterior,
  que debía registrar el paso de la línea temporal 1 a la 2, el failover del
  Experimento C. En el bucket tampoco estaba `00000002.history`.
- **Causa:** el failover del Experimento C ocurrió **antes** de activar el
  plugin. Sin archivador configurado, CloudNativePG da cada archivo de WAL
  por archivado sin enviarlo a ninguna parte. Por eso la primaria tenía
  `00000002.history.done` en `archive_status`, pero el archivo nunca llegó a
  Garage. Lo mismo pasó con los segmentos hasta el 0010: el archivo de WAL
  empieza en el 0011. La copia base no incluye `pg_wal`, y al promoverse el
  clúster restaurado PostgreSQL no encontró en el archivo el historial de la
  línea 2. Escribió `00000003.history` solo con el punto de separación de la
  línea 2.
- **Consecuencias:** ninguna para lo que protege este archivo:
  - **Restaurar desde este backup y hacer PITR:** todo el WAL necesario
    (desde el 0012) y cualquier instante posterior están en la línea
    temporal 2. La recuperación no necesita saber de dónde salió esa línea.
  - **Futuras restauraciones:** la primaria original sí conserva
    `00000002.history` en su `pg_wal`. En el próximo cambio de primaria, el
    plugin archivará `00000003.history` con el historial completo, porque
    PostgreSQL lo escribe copiando el del padre. El hueco se cierra solo.
  - Se pierde solo la trazabilidad de la línea 1 dentro del archivo, que en
    cualquier caso no tiene WAL archivado al que volver.
- **Solución:** no se sube el archivo a mano. Un objeto puesto en el
  archivo de WAL sin pasar por el archivador podría no coincidir con el
  formato que espera `barman-cloud-wal-restore` (compresión y metadatos), y
  no aporta nada que se pueda recuperar.
- **Prevención:** el archivado se activa antes de cualquier cambio de línea
  temporal, al crear el clúster si es posible. En un clúster que ya
  existe, el primer backup después de activar el plugin marca el inicio real
  de lo que se puede recuperar. Así se indica al documentar la ventana de
  recuperación.
- **Frase para entrevista:** «Al restaurar el backup vi que el historial de
  líneas temporales del clúster nuevo estaba incompleto. La causa era que
  el failover anterior se produjo antes de activar el archivado de WAL, y
  sin archivador CloudNativePG da los archivos por archivados sin enviarlos.
  Analicé el impacto: ninguno para la restauración ni para PITR, porque todo
  el WAL necesario está en la línea temporal actual. Decidí no subir el
  archivo a mano para no meter en el archivo un objeto que no ha pasado por
  el archivador. La lección: el archivado se activa desde el primer día, y
  la ventana de recuperación empieza en el primer backup.»

---

## TS-06 · El nivel DEBUG de dev no muestra nada más que prod

- **Fase:** 3 – Helm chart propio (Experimento D).
- **Síntoma:** la release de dev usa `ETL_NIVEL_LOG=DEBUG` y la de prod
  `INFO`. Aun así, el log de la carga inicial de dev no tenía ninguna línea
  `DEBUG`: sus 35 líneas eran todas `INFO`, como en prod.
- **Causa:** el ETL sí lee la variable: `configurar_logs()` en
  `etl/main.py` la pasa a `logging.basicConfig(level=…)`. Pero ningún módulo
  de `etl/src/` llama a `log.debug`, y las bibliotecas que usa no escriben
  nada en ese nivel: `urllib.request` no usa `logging`, pandas no registra
  nada y en dev psycopg no llega a conectarse. El nivel se aplica, pero no
  hay mensajes DEBUG que mostrar.
- **Cómo se comprobó:**
  1. `kubectl logs … | awk '{print $2}' | sort | uniq -c` sobre el log de
     dev: `35 INFO` y ninguna otra fila.
  2. En el código, ninguna llamada `log.debug` en `etl/main.py` ni en
     `etl/src/`.
  3. Con la misma imagen y `docker run --read-only`, llamando a
     `configurar_logs()` del ETL y emitiendo una línea DEBUG de prueba. Con
     `ETL_NIVEL_LOG=DEBUG` aparece la línea
     `… DEBUG   línea DEBUG visible` y el nivel efectivo es `DEBUG`. Con
     `INFO` la línea no aparece. La variable funciona.
- **Solución:** en la Fase 3, ninguna en el código. El README indica que el
  nivel de log está configurado por entorno pero hoy no tiene efecto
  visible, y en «Tareas pendientes» se añaden mensajes DEBUG al ETL para la
  Fase 4: URL y tamaño de cada descarga, y filas antes y después de cada
  limpieza. Llegarán con la imagen que construya GitHub Actions y una nueva
  `appVersion` del chart, en lugar de con un `docker build` manual.
- **Prevención:** una diferencia entre entornos se comprueba por su efecto,
  no solo por su presencia en el diff. Antes de presentar un valor como
  diferencia útil, se comprueba en la salida real que cambia algo; si no
  cambia nada, se documenta como tal.
- **Frase para entrevista:** «En el experimento de entornos, dev tenía el log
  en DEBUG y prod en INFO, pero los dos logs eran idénticos. Comprobé
  primero que la variable llegaba y se aplicaba: con la misma imagen en
  Docker, una línea DEBUG de prueba aparecía o no según el nivel. El
  problema no estaba en el despliegue: el código no emitía ningún mensaje
  DEBUG. Lo documenté como diferencia sin efecto y lo dejé para la siguiente
  imagen, en lugar de presentarlo como una ventaja de dev. La lección: una
  diferencia de configuración solo cuenta si cambia el comportamiento
  observable.»

---

## TS-07 · Aviso de `last-applied-configuration` en la primera sincronización de ArgoCD

- **Fase:** 4 – GitOps y CI/CD (paso 4.2, adopción de la release de Helm).
- **Síntoma:** la primera sincronización de la Application `agroeco-etl`
  terminó `Succeeded`, con `configmap/agroeco-etl configured` y
  `cronjob.batch/agroeco-etl-mensual configured`, pero cada uno con el aviso
  `… missing the kubectl.kubernetes.io/last-applied-configuration annotation
  … will be patched automatically`.
- **Causa:** es el rastro previsto de la migración de Helm a ArgoCD, no un
  fallo. ArgoCD aplica por defecto con el mismo mecanismo que
  `kubectl apply` en el cliente (*client-side apply*). Ese mecanismo guarda
  en la anotación `kubectl.kubernetes.io/last-applied-configuration` lo
  último que aplicó, para saber en el siguiente apply qué campos debe
  borrar. Helm 4 creó y actualizó los dos objetos en la Fase 3 con
  *server-side apply*, que no usa esa anotación. Al no encontrarla, el apply
  de ArgoCD avisa y la añade en esa misma operación.
- **Cómo se comprobó:**
  - **Los objetos se adoptaron sin cambios.** Se comparó una foto tomada
    antes de crear la Application con el estado posterior:
    - Mismo UID y misma fecha de creación: no se recrearon.
    - Misma `metadata.generation` en el CronJob (2): no cambió su `spec`.
    - Solo se añadieron anotaciones: `argocd.argoproj.io/tracking-id`
      (`agroeco-etl:batch/CronJob:agroeco/agroeco-etl-mensual`) y
      `last-applied-configuration`.
  - **Quién ha escrito en el CronJob** (`managedFields`):

    | Gestor | Operación | Hora (UTC) | Qué fue |
    |--------|-----------|------------|---------|
    | `helm` | `Apply` | 2026-11-24 16:59:06 | `helm upgrade` a la revisión 2 (Helm 4 con *server-side apply*) |
    | `k3s` | `Update` (subrecurso `status`) | 2026-11-24 17:02:13 | Controlador de CronJobs, en la ejecución manual |
    | `argocd-controller` | `Update` | 2026-11-24 21:24:19 | Primera sincronización de ArgoCD (*client-side apply*) |

  - **La anotación ya existe.** Empieza por
    `{"apiVersion":"batch/v1","kind":"CronJob","metadata":{"annotations":{"argocd.argoproj.io/tracking-id…`:
    guarda el manifiesto deseado tal como lo aplicó ArgoCD, con su
    anotación de seguimiento.
- **Solución:** ninguna. Es un aviso de un solo uso: con la anotación ya
  puesta, las sincronizaciones siguientes no deberían repetirlo. Se
  comprobará en la primera corrección de drift (Experimento E).
- **¿Server-Side Apply?** ArgoCD admite `ServerSideApply=true` en
  `syncOptions`. Con esa opción, el servidor aplica y registra quién
  gestiona cada campo (`managedFields`), no se usa la anotación y la
  comparación también se hace en el servidor. No se activa ahora:
  - Los dos objetos se sincronizan sin diferencias con el método actual.
  - Los datos anteriores muestran el riesgo concreto. Los campos que fijó
    Helm siguen a nombre del gestor `helm` (operación `Apply`). Con
    *server-side apply*, un campo que se quitara del chart dejaría de ser
    de ArgoCD pero seguiría siendo de `helm`, y el servidor no lo borraría.
    Antes de activarlo habría que retirar las entradas de `helm` de
    `managedFields`.
  
  Queda como mejora posible en el README.
- **Prevención:** en una migración de Helm (o de `kubectl create`) a
  ArgoCD, este aviso es esperable en la primera sincronización. Para saber
  si la adopción cambió algo se miran el UID, la fecha de creación y la
  `generation`, no el mensaje de la operación (mismo criterio que en
  [TS-04](#ts-04--kubectl-apply-responde-configured-sin-haber-cambios)).
- **Frase para entrevista:** «Al pasar el ETL de Helm a ArgoCD, la primera
  sincronización avisó de que a los objetos les faltaba la anotación
  `last-applied-configuration`. Era lo esperado: ArgoCD aplica como
  `kubectl apply` y necesita esa anotación, que Helm no pone. Antes de
  crear la Application había guardado el UID, la fecha de creación y la
  `generation` de cada objeto, y después seguían iguales: ArgoCD los adoptó
  sin recrearlos ni tocar su `spec`. Valoré cambiar a Server-Side Apply,
  pero en `managedFields` vi que Helm 4 había aplicado con server-side
  apply y seguía figurando como dueño de los campos. Con ese cambio, un
  campo quitado del chart no se habría borrado. No lo hice en mitad de la
  migración: no había ningún problema que resolver.»

---

## TS-08 · La interfaz de ArgoCD da «Request has been terminated» al iniciar sesión

- **Fase:** 4 – GitOps y CI/CD (paso 4.2, acceso a la interfaz para la
  captura 20).
- **Síntoma:** al iniciar sesión en `https://localhost:8080`, la interfaz
  mostró `Request has been terminated … Origin is not allowed by
  Access-Control-Allow-Origin …`.
- **Causa:** no era un problema de CORS. Es el mensaje genérico que da la
  interfaz de ArgoCD cuando una petición no recibe respuesta: enumera
  varias «causas posibles» (red caída, CORS, página descargándose) sin
  saber cuál es. El origen era el mismo (`https://localhost:8080`, la propia
  interfaz), y con el túnel reabierto el mismo inicio de sesión funcionó sin
  cambiar nada más. Por tanto, el `kubectl port-forward` de Ubuntu 2 ya no
  transmitía. No se guardó su salida, así que no se sabe por qué se cortó.
  Las causas habituales son un error `lost connection to pod`, o que el pod
  al que estaba atado el túnel se recree (`port-forward` a un Service se
  ata a un pod concreto al arrancar y no sigue a su sustituto).
- **Solución:** cerrar y volver a abrir
  `kubectl port-forward svc/argocd-server -n argocd 8080:443`, y volver a
  iniciar sesión por `https`.
- **Prevención:**
  - Ante un error de red en la interfaz, se mira primero la terminal del
    `port-forward`.
  - Antes de iniciar sesión, se comprueba el túnel desde Ubuntu 1 con
    `curl -sk https://localhost:8080/healthz`, que debe responder `ok`.
  - El túnel se abre después de cualquier reinicio de `argocd-server`,
    nunca antes.
- **Frase para entrevista:** «Al entrar en ArgoCD, la interfaz dio un error
  que mencionaba CORS. No me fié del texto: era el mensaje genérico para
  cualquier petición sin respuesta, y el origen era el propio servidor. El
  problema estaba en el `port-forward`, que ya no transmitía. Lo reabrí y
  entró a la primera. Ahora, antes de iniciar sesión, compruebo el túnel con
  un `curl` a `/healthz` y no le doy más vueltas a la interfaz.»

---

## TS-09 · El CI falla en «La imagen publicada es la probada»

- **Fase:** 4 – GitOps y CI/CD (paso 4.4, primera ejecución del workflow
  `.github/workflows/ci.yaml`, commit `fe84e2f`).
- **Síntoma:** todos los pasos anteriores pasaron, incluidas la prueba de
  humo y la publicación en ghcr.io con las etiquetas `0.2.0` y
  `sha-<commit>`. El último control falló:

  ```
  PROBADA:   sha256:4baa09f79aa2afd14a30050eef5ad0ecf9c1afb6f86a655290d9fc839318a6b8
  PUBLICADA: sha256:6a0aad3fe6874169edbc23ebe2f6e6bab973e0fb86c0454a665a1187387083a6
  ##[error]La imagen publicada no es la misma que pasó la prueba
  ```
- **Causa:** la comparación mezclaba dos identificadores de tipo distinto:
  era como comparar el DNI de una persona con su pasaporte. La imagen se
  construía dos veces y se comparaba la salida `imageid` de cada
  construcción:
  - **Construcción para la prueba** (`load: true`): la imagen se cargaba
    en el Docker del runner, que usa containerd como almacén. Ahí el ID de
    la imagen es el digest de su manifiesto.
  - **Construcción para publicar** (con procedencia y SBOM): el registro
    guarda un índice OCI, que contiene la imagen y sus atestaciones, y el
    `imageid` de esa construcción es otro tipo de digest.

  Ninguno de los dos valores era el digest del índice publicado (la salida
  `digest`). La comparación nunca podía coincidir, aunque las capas fueran
  las mismas. El diseño tenía además un fallo de fondo: probaba una imagen
  y publicaba otra construcción, y solo podía comprobar que eran iguales
  después de haberla publicado con la etiqueta de versión.
- **Solución:** se rediseñó el job «Imagen del ETL» para probar
  exactamente lo publicado, sin comparar IDs:
  1. Se comprueba que la etiqueta de `appVersion` no existe en ghcr.io
     (inmutabilidad), como antes.
  2. Se construye una sola vez y se publica solo como `sha-<commit>`, con
     procedencia y SBOM. Se usa la salida `digest`: el digest del índice.
  3. La prueba de humo, la misma que antes (nivel DEBUG, raíz de solo
     lectura, usuario 10001), se ejecuta sobre
     `ghcr.io/samanaya11/agroeco-etl@<digest>` descargada del registro.
  4. Si pasa, la etiqueta de `appVersion` se añade a ese mismo digest sin
     reconstruir (`docker buildx imagetools create -t … <imagen>@<digest>`).
     Después, `docker buildx imagetools inspect` comprueba que la etiqueta
     apunta exactamente a ese digest. Si no coincide, el job falla.
  5. El resumen y el bloque de promoción usan ese digest.

  Además, el job de la imagen se ejecuta también cuando cambia la línea
  `appVersion` de `Chart.yaml`, no solo cuando cambia `etl/`.

  La versión sube a **0.2.1** (chart 0.2.1): el mismo código, publicado con
  el flujo verificado. La etiqueta `0.2.0` quedó publicada sin verificar.
  No se borra ni se reutiliza (reescribirla rompería la inmutabilidad) y no
  se promueve nunca.
- **Prevención:**
  - La etiqueta de versión solo se crea sobre un digest que ya ha pasado la
    prueba, y siempre por digest, sin reconstruir.
  - Antes de comparar dos identificadores, se comprueba qué es cada uno:
    ID local, digest del manifiesto o digest del índice. Para saber «qué
    hay publicado» se usa el digest del índice, que es el que guarda el
    registro y el que se fija en `values-prod.yaml`.
- **Frase para entrevista:** «Mi CI construía la imagen dos veces, una para
  probarla y otra para publicarla, y comparaba sus IDs para asegurarse de
  que eran la misma. Falló siempre. Uno era el ID local de containerd y el
  otro venía de un índice OCI con atestaciones: comparaba un DNI con un
  pasaporte. Pero el problema de fondo era el diseño: probaba una cosa y
  publicaba otra. Lo cambié para construir una sola vez, publicar solo con
  la etiqueta del commit, probar esa imagen descargada del registro por
  digest y, si pasa, añadir la etiqueta de versión al mismo digest sin
  reconstruir. La 0.2.0, publicada sin verificar, no la reutilicé:
  saqué la 0.2.1.»

---

<!--
Plantilla para cada incidencia (copiar debajo de esta línea):

## TS-NN · Título corto

- **Fase:** N – nombre
- **Síntoma:** qué se vio (mensaje de error literal, recortado si es largo).
- **Causa:** por qué ocurría.
- **Solución:** qué se hizo (comandos o cambios de archivo).
- **Prevención:** cómo evitarlo en adelante (regla, comprobación o cambio permanente).
- **Frase para entrevista:** la incidencia contada en primera persona en
  3-5 frases: qué pasó, cómo se investigó, qué se aprendió.
-->
