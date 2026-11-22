# Registro de incidencias

Incidencias encontradas durante la construcción del proyecto, en el orden en
que ocurrieron. Cada entrada recoge el síntoma observado, la causa real, la
solución aplicada y cómo evitar que se repita.

## Índice

| Nº | Fase | Incidencia |
|----|------|------------|
| [TS-01](#ts-01--un-job-parece-haber-desaparecido-falso-positivo-de-la-terminal) | 1 | Un Job parece haber desaparecido (falso positivo de la terminal) |

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

---

<!--
Plantilla para cada incidencia (copiar debajo de esta línea):

## TS-NN · Título corto

- **Fase:** N – nombre
- **Síntoma:** qué se vio (mensaje de error literal, recortado si es largo).
- **Causa:** por qué ocurría.
- **Solución:** qué se hizo (comandos o cambios de archivo).
- **Prevención:** cómo evitarlo en adelante (regla, comprobación o cambio permanente).
-->
