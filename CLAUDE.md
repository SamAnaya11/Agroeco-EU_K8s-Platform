# CLAUDE.md — Reglas del proyecto Agroeco-EU K8s Platform

Proyecto demostrativo: el ETL serverless original (Azure Function + Azure SQL,
repositorio público `SamAnaya11/Agroeco-EU_Cloud-Pipeline`) llevado a
Kubernetes con k3d, PostgreSQL gestionado por CloudNativePG, Helm, GitOps con
ArgoCD y CI/CD con GitHub Actions. Todo en local y gratis, salvo la Fase 6
(AKS, opcional).

## Entorno

- Claude Code edita los archivos desde VS Code en **Windows**.
- El usuario ejecuta **todos** los comandos (docker, k3d, kubectl, helm, git,
  az, terraform, ansible) en **Ubuntu sobre WSL 2** y pega la salida.
- La carpeta del proyecto está en el disco de Windows; desde WSL se accede por
  `/mnt/c/Cloud-DevOps/Cloud-Data_Projects/Agroeco-EU_K8s-Platform`.
- Herramientas de Windows y de Linux son instalaciones distintas: antes de
  usar una herramienta en WSL se comprueba con `which -a <herramienta>` que la
  ruta es de Linux (`/usr/...`), nunca de `/mnt/c/...`.
- Docker Engine nativo en WSL (repositorio oficial de Docker). **Sin Docker Desktop.**

## Forma de trabajar

1. Se avanza **una fase cada vez**. No se pasa a la siguiente sin la
   confirmación explícita del usuario.
2. Antes de escribir cada archivo se explica en lenguaje sencillo qué hace y por qué.
3. Los comandos se dan de uno en uno o en bloques cortos, indicando qué debe salir.
4. Se avisa en el momento exacto de cada captura (ver `docs/capturas/LEEME.md`).
5. Cada incidencia se registra en `docs/TROUBLESHOOTING.md` en cuanto ocurre
   (síntoma, causa, solución, prevención).
6. El README se mantiene al día en cada fase, no solo al final.

## Estilo

- Todo en **español**: código comentado, documentación y mensajes de commit.
- Código claro, con comentarios que explican el porqué, no solo el qué.
- README con tono profesional de proyecto demostrativo, nunca de tutorial
  ni de aprendizaje.
- Finales de línea LF (lo impone `.gitattributes`).

## Versiones y componentes

- Antes de usar una herramienta, chart o imagen se verifica su última versión
  estable, y después se **fija** (sin `latest` en imágenes ni charts sin versión).
- Prohibido usar componentes obsoletos o retirados. En concreto:
  - Ingress NGINX (retirado) → acceso por `kubectl port-forward` o Gateway API.
  - `barmanObjectStore` de CloudNativePG (obsoleto) → Barman Cloud Plugin.
  - MinIO (archivado) → Garage o SeaweedFS.
  - Docker Desktop → Docker Engine en WSL.

## Secretos (regla estricta)

- Ninguna contraseña, token, IP pública, ID de suscripción/tenant ni correo
  real en Git ni en capturas.
- Los Secret de Kubernetes se crean con `kubectl create secret`; en el repo solo
  existen archivos `*.example.yaml` o `.env.example` con valores ficticios.
- Antes del primer commit (y antes de cada push relevante) se ejecuta una
  comprobación de secretos.
- El estado de Terraform y los `*.tfvars` reales no se suben nunca.

## Repositorio original

- Se clona en una carpeta temporal **fuera** de este proyecto y nunca se modifica.
- Solo se copia lo necesario (`src/`, `sql/`) y se adapta lo mínimo: arranque
  como script normal y carga en PostgreSQL. La lógica de extracción, limpieza
  y carga se mantiene.

## Limpieza y costes

- Fase 6 (AKS): `terraform destroy` es obligatorio al terminar cada sesión.
- Al final del proyecto: `k3d cluster delete`.
